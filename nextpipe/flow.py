import ast
import base64
import inspect
import io
import threading
import time
from importlib.metadata import version
from itertools import product
from typing import Any, Optional, Union

from nextmv.cloud import Application, Client, StatusV2

from . import config, decorators, graph, schema, threads, uplink, utils


class FlowStep:
    def __init__(
        self,
        step_function: callable,
        step_definition: decorators.Step,
        docstring: str,
    ):
        self.step_function = step_function
        self.definition = step_definition
        self.docstring = docstring
        self.lock = threading.Lock()
        self.done = False
        self.successors: list[FlowStep] = []
        self.predecessors: list[FlowStep] = []
        self.nodes: list[FlowNode] = []

    def __repr__(self):
        return f"FlowStep({self.step_function.name})"


class FlowNode:
    def __init__(self, parent: FlowStep, index: int):
        self.parent = parent
        self.index = index
        self.id = f"{parent.definition.get_id()}_{index}"
        self.status: str = "pending"
        self.error: str = None
        self.successors: list[FlowNode] = []
        self.run_id: str = None
        self.result: any = None
        self.done: bool = False

    def __repr__(self):
        return f"FlowNode({self.id})"


class FlowSpec:
    def __init__(
        self,
        name: str,
        input: dict,
        conf: Optional[config.Configuration] = None,
        client: Optional[Client] = None,
        uplink_config: Optional[uplink.UplinkConfig] = None,
    ):
        self.name = name
        self.config = config.Configuration() if conf is None else conf
        self.client = Client() if client is None else client
        self.uplink = uplink.UplinkClient(self.client, uplink_config)
        # Create the graph
        self.graph = FlowGraph(self.__class__)
        # Inform platform about the graph
        self.uplink.post_graph(self.graph._to_uplink_dag())
        # Prepare for running the flow
        self.input = input
        self.runner = Runner(
            self,
            self.graph,
            self.config,
            self.uplink,
        )

    def run(self):
        self.runner.run()

    def __repr__(self):
        return f"Flow({self.name})"

    def get_result(self, step: callable) -> Union[object, None]:
        if not hasattr(step, "step"):
            raise Exception(f"Step {step} does not have a step decorator.")
        s = self.graph.get_step(step.step)
        if not s.done:
            return None
        return [n.result for n in s.nodes] if len(s.nodes) > 1 else s.nodes[0].result

    def _get_inputs(self, step: FlowStep) -> list[object]:
        return (
            [self.get_result(predecessor) for predecessor in step.definition.needs.predecessors]
            if step.definition.is_needs()
            else [self.input]
        )


class FlowGraph:
    def __init__(self, flow_spec_type: type):
        self.flow_spec_type = flow_spec_type
        self.__create_graph(flow_spec_type)
        self.__debug_print()
        # Create a Mermaid diagram of the graph and log it
        mermaid = self._to_mermaid()
        utils.log("Mermaid diagram:")
        utils.log(mermaid)
        mermaid_url = f"https://mermaid.ink/svg/{base64.b64encode(mermaid.encode('utf8')).decode('ascii')}?theme=dark"
        utils.log(f"Mermaid URL: {mermaid_url}")

    def get_step(self, definition: decorators.Step) -> FlowStep:
        return self.steps_by_definition[definition]

    def __create_graph(self, flow_spec):
        module = __import__(flow_spec.__module__)
        class_name = flow_spec.__name__
        tree = ast.parse(inspect.getsource(module)).body
        root = [n for n in tree if isinstance(n, ast.ClassDef) and n.name == class_name][0]

        # Build the graph
        self.steps: list[FlowStep] = []
        visitor = StepVisitor(self.steps, flow_spec)
        visitor.visit(root)

        # Init steps for all step definitions
        self.steps_by_definition = {step.definition: step for step in self.steps}
        for step in self.steps:
            step.predecessors = []
            step.successors = []

        for step in self.steps:
            if not step.definition.is_needs():
                continue
            for predecessor in step.definition.needs.predecessors:
                predecessor_node = self.steps_by_definition[predecessor.step]
                step.predecessors.append(predecessor_node)
                predecessor_node.successors.append(step)

        self.start_steps = [step for step in self.steps if not step.predecessors]

        # Make sure that all app steps have at most one predecessor.
        # TODO: This may change in the future. See other comment about it in this file.
        for step in self.steps:
            if step.definition.is_app() and len(step.predecessors) > 1:
                raise Exception(
                    "App steps cannot have more than one predecessor, "
                    + f"but {step.definition.get_id()} has {len(step.predecessors)}"
                )

        # Check for cycles
        steps_as_dict = {}
        for step in self.steps:
            steps_as_dict[step.definition.get_id()] = [successor.definition.get_id() for successor in step.successors]
        cycle, cycle_steps = graph.check_cycle(steps_as_dict)
        if cycle:
            raise Exception(f"Cycle detected in the flow graph, cycle steps: {cycle_steps}")

    def __get_arrow(self, step: FlowStep, successor: FlowStep) -> str:
        if step.definition.is_foreach() and not successor.definition.is_join():
            return "-- foreach -->"
        if not step.definition.is_foreach() and successor.definition.is_join():
            return "-- join -->"
        return "-->"

    def _to_mermaid(self):
        """Convert the graph to a Mermaid diagram."""
        out = io.StringIO()
        out.write("graph LR\n")
        for step in self.steps:
            id = step.definition.get_id()
            if step.definition.is_foreach():
                out.write(f"  {id}{{ }}\n")
            if step.definition.is_repeat():
                out.write(f"  {id}{{ }}\n")
                out.write(f"  {id}_join{{ }}\n")
                repetitions = step.definition.repeat.repetitions
                for i in range(repetitions):
                    out.write(f"  {id}_{i}({id}_{i})\n")
                    out.write(f"  {id} --> {id}_{i}\n")
                    out.write(f"  {id}_{i} --> {id}_join\n")
                for successor in step.successors:
                    out.write(f"  {id}_join {self.__get_arrow(step, successor)} {successor.definition.get_id()}\n")
            else:
                out.write(f"  {id}({id})\n")
                for successor in step.successors:
                    out.write(f"  {id} {self.__get_arrow(step, successor)} {successor.definition.get_id()}\n")
        return out.getvalue()

    def _to_uplink_dag(self) -> uplink.FlowDTO:
        return uplink.FlowDTO(
            steps=[
                uplink.StepDTO(
                    id=step.definition.get_id(),
                    app_id=step.definition.get_app_id(),
                    docs=step.docstring,
                    predecessors=[s.definition.get_id() for s in step.successors],
                )
                for step in self.steps
            ]
        )

    def _to_uplink_node(self, node: FlowNode) -> uplink.NodeStateDTO:
        return uplink.NodeStateDTO(
            parent_id=node.parent.definition.get_id(),
            predecessor_ids=[p.id for p in node.successors],
            status=node.status,
            run_id=node.run_id,
        )

    def __debug_print(self):
        utils.log(f"Flow: {self.flow_spec_type.__name__}")
        utils.log(f"nextpipe: {version('nextpipe')}")
        utils.log(f"nextmv: {version('nextmv')}")
        utils.log("Flow graph steps:")
        for step in self.steps:
            utils.log("Step:")
            utils.log(f"  Definition: {step.definition}")
            utils.log(f"  Docstring: {step.docstring}")


class StepVisitor(ast.NodeVisitor):
    def __init__(self, steps: list[FlowStep], flow: FlowSpec):
        self.steps = steps
        self.flow = flow
        super().__init__()

    def visit_FunctionDef(self, step_function):
        func = getattr(self.flow, step_function.name)
        if hasattr(func, "is_step"):
            self.steps.append(FlowStep(step_function, func.step, func.__doc__))


## EXECUTION


class Runner:
    def __init__(
        self,
        spec: FlowSpec,
        graph: FlowGraph,
        config: config.Configuration,
        uplink: uplink.UplinkClient,
    ):
        self.spec = spec
        self.graph = graph
        self.uplink = uplink
        self.pool = threads.Pool(config.thread_count)
        self.jobs = []
        self.node_idxs = {}
        self.fail = False
        self.fail_reason = None
        self.lock_fail = threading.Lock()
        self.lock_running = threading.Lock()

    def __prepare_inputs(self, step: FlowStep) -> list[list[any]]:
        """
        Prepares the inputs for a step. The inputs are either collected from predecessors
        or the flow input is used (if the step has no predecessors).
        If the step is a 'foreach' step, the input is repeated for each item in the result
        of the predecessor. If multiple predecessors are defined as 'foreach', the inputs
        are combined in a cartesian product. If the step itself is defined as 'repeat',
        the resulting inputs are repeated for each repetition. The result of the step is
        a list of results, one for each final input (after combining predecessors,
        'foreach', 'repeat' and potential further modifiers).
        """
        # If the step has no predecessors, the input is the flow input.
        if not step.predecessors:
            return [self.spec.input]
        # Collect all inputs from predecessors.
        predecessor_inputs = {}
        for predecessor in step.predecessors:
            predecessor_results = [res.result for res in predecessor.nodes]
            if predecessor.definition.is_foreach():
                # Make sure the result is in fact a list.
                if len(predecessor_results) != 1 or not isinstance(predecessor_results[0], list):
                    raise Exception(
                        f"Predecessor step {predecessor.definition.get_id()} declared as 'foreach' "
                        + f"must return a list, but returned {predecessor_results}"
                    )
                # If the predecessor is a 'foreach' step, we need to create a result for each item.
                predecessor_results = predecessor_results[0]
            if predecessor.definition.is_repeat():
                # If the predecessor is a 'repeat' step, we need to collect the results in a list.
                predecessor_results = [predecessor_results]
            predecessor_inputs[predecessor] = predecessor_results
        # Combine inputs from predecessors (cartesian product).
        inputs = [list(item) for item in product(*predecessor_inputs.values())]
        # If the steps is a 'join' step, we need to combine the inputs from all predecessors.
        if step.definition.is_join():
            # Unwrap the inputs from the list of lists.
            inputs = [item[0] for item in inputs]
        # If the step is a 'repeat' step, repeat the inputs for each repetition.
        if step.definition.is_repeat():
            inputs = inputs * step.definition.get_repetitions()
        if len(inputs) > self.spec.config.max_step_inputs:
            raise Exception(
                f"Step {step.definition.get_id()} has too many inputs ({len(inputs)}). "
                + f"Maximum allowed is {self.graph.flow_spec_type.config.max_step_inputs}."
            )
        return inputs

    def __node_callback(self, job: threads.Job):
        """
        Callback function for a job. This function is called by the pool manager when a job is done.
        """
        reference: FlowNode = job.reference
        reference.status = "succeeded" if job.error is None else "failed"
        reference.result = job.result
        reference.error = job.error
        # Check if the job failed and mark the flow as failed if it did
        with self.lock_fail:
            if job.error is not None and not self.fail:
                self.fail = True
                self.fail_reason = f"Step {reference.parent.definition.get_id()} failed: {job.error}"
        # Mark the node as done (and its parent if all nodes are done)
        reference.done = True
        with reference.parent.lock:
            if all(n.done for n in reference.parent.nodes):
                reference.parent.done = True
        # Inform the platform about the node update
        self.uplink.enqueue_node_update(reference.id, self.graph._to_uplink_node(reference))

    @staticmethod
    def __run_step(node: FlowNode, inputs: list[object], client: Client) -> Union[list[object], object, None]:
        utils.log(f"Running node {node.id}")

        # Run the step
        if node.parent.definition.is_app():
            app_step = node.parent.definition.app
            # Prepare the input for the app
            # TODO: We only support one predecessor for app steps for now. This may
            # change in the future. We may want to support multiple predecessors for
            # app steps. However, we need to think about how to handle the input and
            # how to expose control over the input to the user.
            if len(inputs) > 1:
                raise Exception(f"App steps cannot have more than one predecessor, but {node.id} has {len(inputs)}")
            if isinstance(inputs[0], schema.AppRunConfig):
                # If the input is AppRunConfig, unwrap it.
                app_run_config: schema.AppRunConfig = inputs[0]
                input = app_run_config.input
                options = {option.name: option.value for option in app_run_config.options}
            else:
                # If the input is not AppRunConfig, we use it directly.
                input = inputs[0]
                options = app_step.parameters
            run_args = (
                [],  # No nameless arguments
                {  # We use the named arguments to pass the user arguments to the run function
                    "input": input,
                    "options": options,
                },
            )
            # Prepare the application itself.
            app = Application(
                client=client,
                id=app_step.app_id,
                default_instance_id=app_step.instance_id,
            )
            # Run the application
            run_id = app.new_run(*run_args[0], **run_args[1])
            node.run_id = run_id
            output = utils.wait_for_runs(app=app, run_ids=[run_id])[0]
            # Check if all runs were successful
            if output.metadata.status_v2 != StatusV2.succeeded:
                raise Exception(f"Node {node.id} failed with status {output.metadata.status_v2}: {output.error_log}")
            # Unwrap the result and return it
            return output.output
        else:
            spec = inspect.getfullargspec(node.parent.definition.function)
            if len(spec.args) == 0:
                output = node.parent.definition.function()
            else:
                output = node.parent.definition.function(*inputs)
            return output

    def __create_job(self, node: FlowNode, inputs: Union[list[Any], Any]) -> threads.Job:
        # Convert input to list, if it is not already a list
        inputs = inputs if isinstance(inputs, list) else [inputs]
        # Create the job
        return threads.Job(
            target=self.__run_step,
            callback=self.__node_callback,
            args=(node, inputs, self.spec.client),
            reference=node,
        )

    def run(self):
        # Start communicating updates to the platform
        try:
            self.uplink.post_graph(self.graph)
            self.uplink.run_async()
        except Exception as e:
            self.uplink.terminate()
            utils.log(f"Failed to update graph with platform: {e}")

        # Start running the flow
        open_steps: set[FlowStep] = set(self.graph.start_steps)
        running_steps: set[FlowStep] = set()
        closed_steps: set[FlowStep] = set()

        # Run the steps in parallel
        while open_steps or running_steps:
            # If there was a failure, stop running the flow
            with self.lock_fail:
                if self.fail:
                    utils.log(f"Flow failed: {self.fail_reason}")
                    break
            while True:
                # Get the first step from the open steps which has all its predecessors done
                step = next(iter(filter(lambda n: all(p in closed_steps for p in n.predecessors), open_steps)), None)
                if step is None:
                    # No more steps to run at this point. Wait for the remaining tasks to finish.
                    break
                open_steps.remove(step)
                # Skip the step if it is optional and the condition is not met
                if step.definition.skip():
                    utils.log(f"Skipping step {step.definition.get_id()}")
                    step.definition.set_state("skipped")
                    # Create dummy node
                    node = FlowNode(step, 0)
                    node.status = "skipped"
                    node.result = None
                    step.nodes.append(node)
                    closed_steps.add(step)
                    open_steps.update(step.successors)
                    self.uplink.enqueue_node_update(node.id, self.graph._to_uplink_node(node))
                    continue
                # Run the node asynchronously
                step.definition.set_state("running")
                with self.lock_running:
                    running_steps.add(step)
                inputs = self.__prepare_inputs(step)
                for i, input in enumerate(inputs):
                    node = FlowNode(step, i)
                    job = self.__create_job(node, input)
                    self.pool.run(job)
                    step.nodes.append(node)
                    self.uplink.enqueue_node_update(node.id, self.graph._to_uplink_node(node))

            # Wait until at least one task is done
            task_done = False
            while not task_done:
                time.sleep(0.1)
                # Check if any steps are done, if not, keep waiting
                done_steps = []
                with self.lock_running:
                    done_steps = [step for step in running_steps if step.done]
                    task_done = True
                for step in done_steps:
                    # Remove step and mark successors as ready by adding them to the open list.
                    with self.lock_running:
                        running_steps.remove(step)
                    closed_steps.add(step)
                    open_steps.update(step.successors)
