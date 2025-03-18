import ast
import base64
import inspect
import io
import time
from importlib.metadata import version
from typing import Optional, Union

from nextmv.cloud import Application, Client, StatusV2

from . import decorators, graph, threads, uplink, utils


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
        self.successors: list[FlowStep] = []
        self.predecessors: list[FlowStep] = []

    def __repr__(self):
        return f"DAGNode({self.step_function.name})"


class FlowNode:
    def __init__(self, parent: FlowStep, index: int):
        self.parent = parent
        self.index = index
        self.id = f"{parent.definition.get_id()}_{index}"
        self.status: str = "pending"
        self.successors: list[FlowNode] = []
        self.run_id: str = None

    def __repr__(self):
        return f"FlowNode({self.id})"


class FlowSpec:
    def __init__(
        self,
        name: str,
        input: dict,
        client: Optional[Client] = None,
        uplink_config: Optional[uplink.UplinkConfig] = None,
    ):
        self.name = name
        self.client = Client() if client is None else client
        self.uplink = uplink.UplinkClient(self.client, uplink_config)
        # Create the graph
        self.graph = FlowGraph(self.__class__)
        # Inform platform about the graph
        self.uplink.post_graph(self.graph._to_uplink_dag())
        # Prepare for running the flow
        self.input = input
        self.results = {}

    def __repr__(self):
        return f"Flow({self.name})"

    def run_pool(self):
        pool = threads.Pool(8)
        # TODO: implement new runner

    def run(self):
        open_steps = set(self.graph.start_steps)
        closed_steps = set()

        # Run the steps in parallel
        tasks = {}
        pool = threads.Pool(8)
        while open_steps:
            while True:
                # Get the first step from the open steps which has all its predecessors done
                step = next(
                    iter(
                        filter(
                            lambda n: all(p in closed_steps for p in n.predecessors),
                            open_steps,
                        )
                    ),
                    None,
                )
                if step is None:
                    # No more steps to run at this point. Wait for the remaining tasks to finish.
                    break
                open_steps.remove(step)
                # Skip the step if it is optional and the condition is not met
                if step.definition.skip():
                    utils.log(f"Skipping step {step.definition.get_id()}")
                    step.definition.set_state("skipped")
                    self.uplink.enqueue_node_update(self.graph._to_uplink_node(step))
                    continue
                # Run the node asynchronously
                job = threads.Job(self.__run_step, None, (step, self._get_inputs(step), self.client))
                pool.run(job)
                tasks[step] = job
                step.definition.set_state("running")
                self.uplink.enqueue_node_update(self.graph._to_uplink_node(step))

            # Wait until at least one task is done
            task_done = False
            while not task_done:
                time.sleep(0.1)
                # Check if any tasks are done, if not, keep waiting
                for step, job in list(tasks.items()):
                    if job.done:
                        # Remove task and mark successors as ready by adding them to the open list.
                        self.set_result(step, job.result)
                        step.step.set_state("succeeded")
                        self.uplink.enqueue_node_update(self.graph._to_uplink_node(step))
                        del tasks[step]
                        task_done = True
                        closed_steps.add(step)
                        open_steps.update(step.successors)

    def set_result(self, step: callable, result: object):
        self.results[step.step] = result

    def get_result(self, step: callable) -> Union[object, None]:
        return self.results.get(step.step)

    def _get_inputs(self, step: FlowStep) -> list[object]:
        return (
            [self.get_result(predecessor) for predecessor in step.definition.needs.predecessors]
            if step.definition.is_needs()
            else [self.input]
        )

    @staticmethod
    def __run_step(step: FlowStep, inputs: list[object], client: Client) -> Union[list[object], object, None]:
        utils.log(f"Running step {step.definition.get_id()}")

        # Run the step
        if step.definition.is_app():
            app_step = step.definition.app
            repetitions = step.definition.repeat.repetitions if step.definition.is_repeat() else 1
            # Prepare the input for the app
            # TODO: We only support one predecessor for app steps for now. This may
            # change in the future. We may want to support multiple predecessors for
            # app steps. However, we need to think about how to handle the input and
            # how to expose control over the input to the user.
            if len(inputs) > 1:
                raise Exception(
                    f"App steps cannot have more than one predecessor, but {step.definition.get_id()} has {len(inputs)}"
                )
            inputs = [
                (
                    [],  # No nameless arguments
                    {  # We use the named arguments to pass the user arguments to the run function
                        "input": inputs[0],
                        "options": app_step.parameters,
                    },
                )
            ] * repetitions
            app = Application(client=client, id=app_step.app_id, default_instance_id=app_step.instance_id)
            # Run the app (or multiple runs if it is a repeat step)
            run_ids = [app.new_run(*i[0], **i[1]) for i in inputs]
            step.definition.set_run_ids(run_ids)
            outputs = utils.wait_for_runs(app=app, run_ids=run_ids)
            # Check if all runs were successful
            for output in outputs:
                if output.metadata.status_v2 != StatusV2.succeeded:
                    raise Exception(
                        f"Step {step.definition.get_id()} failed with status {output.metadata.status_v2}: "
                        + f"{output.error_log}"
                    )
            # Unwrap the result and store it
            # TODO: We may want to store the full RunResult object in certain cases.
            # Maybe this can become a parameter of the step decorator.
            outputs = [output.output for output in outputs]
            return outputs if step.definition.is_repeat() else outputs[0]
        else:
            spec = inspect.getfullargspec(step.definition.function)
            if len(spec.args) == 0:
                output = step.definition.function()
            else:
                output = step.definition.function(*inputs)
            return output


class FlowGraph:
    def __init__(self, flow_spec: FlowSpec):
        self.flow_spec = flow_spec
        self.__create_graph(flow_spec)
        self.__debug_print()
        # Create a Mermaid diagram of the graph and log it
        mermaid = self._to_mermaid()
        utils.log(mermaid)
        mermaid_url = f"https://mermaid.ink/svg/{base64.b64encode(mermaid.encode('utf8')).decode('ascii')}?theme=dark"
        utils.log(f"Mermaid URL: {mermaid_url}")

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
        steps_by_definition = {step.definition: step for step in self.steps}
        for step in self.steps:
            step.predecessors = []
            step.successors = []

        for step in self.steps:
            if not step.definition.is_needs():
                continue
            for predecessor in step.definition.needs.predecessors:
                predecessor_node = steps_by_definition[predecessor.step]
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

    def _to_mermaid(self):
        """Convert the graph to a Mermaid diagram."""
        out = io.StringIO()
        out.write("graph TD\n")
        for step in self.steps:
            id = step.definition.get_id()
            if step.definition.is_repeat():
                out.write(f"  {id}{{ }}\n")
                out.write(f"  {id}_join{{ }}\n")
                repetitions = step.definition.repeat.repetitions
                for i in range(repetitions):
                    out.write(f"  {id}_{i}({id}_{i})\n")
                    out.write(f"  {id} --> {id}_{i}\n")
                    out.write(f"  {id}_{i} --> {id}_join\n")
                for successor in step.successors:
                    out.write(f"  {id}_join --> {successor.definition.get_id()}\n")
            else:
                out.write(f"  {id}({id})\n")
                for successor in step.successors:
                    out.write(f"  {id} --> {successor.definition.get_id()}\n")
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

    def _to_uplink_node(self, node: FlowNode) -> uplink.NodeDTO:
        return uplink.NodeDTO(
            id=node.id,
            parent_id=node.parent.definition.get_id(),
            predecessor_ids=[p.id for p in node.successors],
            status=node.status,
            run_id=node.run_id,
        )

    def __debug_print(self):
        utils.log(f"Flow: {self.flow_spec.__name__}")
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
