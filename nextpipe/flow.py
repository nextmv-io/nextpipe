"""
Flow module for defining and executing decision pipelines.

This module provides classes and functions for creating, configuring, and
executing decision pipelines.

Classes
-------
FlowStep
    Represents a step in a workflow pipeline.
FlowNode
    Represents a specific instance of a step in execution.
FlowSpec
    Defines a complete workflow specification.
FlowGraph
    Represents the directed acyclic graph (DAG) of steps in a flow.
StepVisitor
    AST visitor for finding step functions in a flow class.
Runner
    Handles the execution of a flow graph.

The module also defines status constants used throughout pipeline execution.
"""

import ast
import base64
import copy
import inspect
import io
import random
import threading
import time
from importlib.metadata import version
from itertools import product
from typing import Any, Optional, Union

from nextmv.cloud import Application, Client

from . import config, decorators, graph, schema, threads, uplink, utils
from .__about__ import __version__

STATUS_PENDING = "pending"
"""Status constant indicating a pending step or node."""

STATUS_RUNNING = "running"
"""Status constant indicating a running step or node."""

STATUS_SUCCEEDED = "succeeded"
"""Status constant indicating a successfully completed step or node."""

STATUS_FAILED = "failed"
"""Status constant indicating a failed step or node."""


class FlowStep:
    """
    Represents a step in a workflow pipeline.

    A FlowStep is created from a function decorated with `@step` and maintains
    information about its position in the flow graph, including predecessors,
    successors, and execution nodes.

    Parameters
    ----------
    step_function : callable
        The AST function node representing the step function.
    step_definition : decorators.Step
        The step decorator instance that contains the step's configuration.
    docstring : str
        The docstring of the step function.

    Attributes
    ----------
    step_function : callable
        The AST function node representing the step function.
    definition : decorators.Step
        The step decorator instance.
    docstring : str
        The docstring of the step function.
    lock : threading.Lock
        Thread lock for this step.
    done : bool
        Whether this step has completed execution.
    successors : list[FlowStep]
        Steps that depend on this step.
    predecessors : list[FlowStep]
        Steps that this step depends on.
    nodes : list[FlowNode]
        Execution nodes for this step.
    """

    def __init__(
        self,
        step_function: callable,
        step_definition: decorators.Step,
        docstring: str,
    ):
        """
        Initialize a FlowStep.

        Parameters
        ----------
        step_function : callable
            The AST function node representing the step function.
        step_definition : decorators.Step
            The step decorator instance that contains the step's configuration.
        docstring : str
            The docstring of the step function.
        """

        self.step_function = step_function
        self.definition = step_definition
        self.docstring = docstring
        self.lock = threading.Lock()
        self.done = False
        self.successors: list[FlowStep] = []
        self.predecessors: list[FlowStep] = []
        self.nodes: list[FlowNode] = []

    def __repr__(self):
        """
        Return a string representation of the FlowStep.

        Returns
        -------
        str
            String representation showing the step function name.
        """

        return f"FlowStep({self.step_function.name})"


class FlowNode:
    """
    Represents a specific instance of a step in execution.

    A FlowNode is created for each execution instance of a FlowStep. For example,
    when using foreach or repeat decorators, multiple nodes will be created for a
    single step.

    Parameters
    ----------
    parent : FlowStep
        The parent step this node belongs to.
    index : int
        The index of this node within the parent step.

    Attributes
    ----------
    parent : FlowStep
        The parent step this node belongs to.
    index : int
        The index of this node within the parent step.
    id : str
        Unique identifier for this node.
    status : str
        Current execution status (pending, running, succeeded, failed).
    error : str or None
        Error message if the node execution failed.
    predecessors : list[FlowNode]
        Nodes that this node depends on.
    run_id : str or None
        ID of the application run if this is an app step.
    result : Any
        Result data from this node's execution.
    done : bool
        Whether this node has completed execution.
    cancel : bool
        Flag to indicate if this node's execution should be cancelled.
    """

    def __init__(self, parent: FlowStep, index: int):
        """
        Initialize a FlowNode.

        Parameters
        ----------
        parent : FlowStep
            The parent step this node belongs to.
        index : int
            The index of this node within the parent step.
        """

        self.parent = parent
        self.index = index
        self.id = f"{parent.definition.get_id()}_{index}"
        self.status: str = STATUS_PENDING
        self.error: str = None
        self.predecessors: list[FlowNode] = []
        self.run_id: str = None
        self.result: Any = None
        self.done: bool = False
        self.cancel: bool = False

    def __repr__(self):
        """
        Return a string representation of the FlowNode.

        Returns
        -------
        str
            String representation showing the node's id.
        """

        return f"FlowNode({self.id})"


class FlowSpec:
    """
    Defines a complete workflow specification.

    You can import the `FlowSpec` class directly from `nextpipe`:

    ```python
    from nextpipe import FlowSpec
    ```

    FlowSpec is the main class to define a workflow. Users typically inherit from this class
    and decorate methods with @step to define the workflow steps.

    Parameters
    ----------
    name : str
        Name of the flow specification.
    input : dict
        Input data for the flow.
    conf : Optional[config.Configuration], optional
        Configuration for the flow, by default None.
    client : Optional[Client], optional
        Nextmv client for API access, by default None.
    uplink_config : Optional[uplink.UplinkConfig], optional
        Configuration for uplink, by default None.

    Attributes
    ----------
    name : str
        Name of the flow specification.
    config : config.Configuration
        Configuration for the flow.
    client : Client
        Nextmv client for API access.
    uplink : uplink.UplinkClient
        Client for communicating with the Nextmv platform.
    graph : FlowGraph
        Graph representing the workflow.
    input : dict
        Input data for the flow.
    runner : Runner
        Runner responsible for executing the flow.

    Examples
    --------
    ```python
    from nextpipe import FlowSpec, step

    class MyFlow(FlowSpec):
        @step
        def step1(self, input_data):
            # Process input data
            return {"processed": input_data}

        @step
        def step2(self, input_data):
            # Further processing
            return {"result": input_data["processed"] * 2}

    # Create and run the flow
    flow = MyFlow("my-flow", {"value": 5})
    flow.run()
    ```
    """

    def __init__(
        self,
        name: str,
        input: dict,
        conf: Optional[config.Configuration] = None,
        client: Optional[Client] = None,
        uplink_config: Optional[uplink.UplinkConfig] = None,
    ):
        """
        Initialize a FlowSpec.

        Parameters
        ----------
        name : str
            Name of the flow specification.
        input : dict
            Input data for the flow.
        conf : Optional[config.Configuration], optional
            Configuration for the flow, by default None.
        client : Optional[Client], optional
            Nextmv client for API access, by default None.
        uplink_config : Optional[uplink.UplinkConfig], optional
            Configuration for uplink, by default None.
        """

        self.name = name
        self.config = config.Configuration() if conf is None else conf
        self.client = Client() if client is None else client
        self.uplink = uplink.UplinkClient(self.client, uplink_config)
        # Create the graph
        self.graph = FlowGraph(self)
        # Inform platform about the graph
        self.uplink.submit_update(self.graph._to_uplink_dto())
        # Prepare for running the flow
        self.input = input
        self.runner = Runner(
            self,
            self.graph,
            self.config,
            self.uplink,
        )

    def run(self):
        """
        Run the flow.

        This method starts the flow execution and blocks until it completes
        or fails with an exception.
        """

        self.runner.run()

    def __repr__(self):
        """
        Return a string representation of the FlowSpec.

        Returns
        -------
        str
            String representation showing the flow name.
        """

        return f"Flow({self.name})"

    def get_result(self, step: callable) -> Union[object, None]:
        """
        Get the result of a step.

        Parameters
        ----------
        step : callable
            The step function to get the result for.

        Returns
        -------
        Union[object, None]
            The result of the step, or None if the step is not done.
            If the step has multiple nodes, a list of results is returned.

        Raises
        ------
        Exception
            If the provided function does not have a step decorator.

        Examples
        --------
        ```python
        # Assuming a flow with a step called 'process_data'
        result = flow.get_result(flow.process_data)
        ```
        """
        if not hasattr(step, "step"):
            raise Exception(f"Step {step} does not have a step decorator.")
        s = self.graph.get_step(step.step)
        if not s.done:
            return None
        return [n.result for n in s.nodes] if len(s.nodes) > 1 else s.nodes[0].result

    def _get_inputs(self, step: FlowStep) -> list[object]:
        """
        Get the inputs for a step.

        Parameters
        ----------
        step : FlowStep
            The step to get inputs for.

        Returns
        -------
        list[object]
            List of input objects for the step.
        """

        return (
            [self.get_result(predecessor) for predecessor in step.definition.needs.predecessors]
            if step.definition.is_needs()
            else [self.input]
        )


class FlowGraph:
    """
    Represents the directed acyclic graph (DAG) of steps in a flow.

    You can import the `FlowGraph` class directly from `nextpipe`:

    ```python
    from nextpipe import FlowGraph
    ```

    A FlowGraph contains all steps of a flow and their connections, forming a DAG.
    It provides methods for converting the graph to different representations.

    Parameters
    ----------
    flow_spec : FlowSpec
        The flow specification this graph belongs to.

    Attributes
    ----------
    flow_spec : FlowSpec
        The flow specification this graph belongs to.
    steps : list[FlowStep]
        List of all steps in the graph.
    steps_by_definition : dict
        Dictionary mapping step definitions to FlowStep objects.
    start_steps : list[FlowStep]
        List of steps with no predecessors (starting points).
    """

    def __init__(self, flow_spec: FlowSpec):
        """
        Initialize a FlowGraph.

        Parameters
        ----------
        flow_spec : FlowSpec
            The flow specification this graph belongs to.
        """
        self.flow_spec = flow_spec
        self.__create_graph(flow_spec)
        self.__debug_print()
        # Create a Mermaid diagram of the graph and log it
        mermaid = self._to_mermaid()
        utils.log_internal("Mermaid diagram:")
        utils.log_internal(mermaid)
        mermaid_url = f"https://mermaid.ink/svg/{base64.b64encode(mermaid.encode('utf8')).decode('ascii')}?theme=dark"
        utils.log_internal(f"Mermaid URL: {mermaid_url}")

    def get_step(self, definition: decorators.Step) -> FlowStep:
        """
        Get a FlowStep by its definition.

        Parameters
        ----------
        definition : decorators.Step
            Step definition to look up.

        Returns
        -------
        FlowStep
            The FlowStep matching the given definition.
        """

        return self.steps_by_definition[definition]

    def __create_graph(self, flow_spec: FlowSpec):
        """
        Create the flow graph by analyzing the flow specification.

        This method visits all step methods in the flow specification class,
        builds the graph of steps and their connections, and validates the graph
        (checks for cycles and other constraints).

        Parameters
        ----------
        flow_spec : FlowSpec
            The flow specification to create a graph for.

        Raises
        ------
        Exception
            If constraints are violated (e.g., app steps with multiple predecessors)
            or if a cycle is detected in the graph.
        """

        root = utils.get_ast_root(flow_spec)

        # Build the graph
        self.steps: list[FlowStep] = []
        visitor = StepVisitor(self.steps, flow_spec.__class__)
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
                predecessor_step = self.steps_by_definition[predecessor.step]
                step.predecessors.append(predecessor_step)
                predecessor_step.successors.append(step)

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
        """
        Get the arrow style for Mermaid diagram connections.

        Parameters
        ----------
        step : FlowStep
            The source step.
        successor : FlowStep
            The target step.

        Returns
        -------
        str
            The arrow style string for the Mermaid diagram.
        """

        if step.definition.is_foreach() and not successor.definition.is_join():
            return "-- foreach -->"
        if not step.definition.is_foreach() and successor.definition.is_join():
            return "-- join -->"
        return "-->"

    def _to_mermaid(self):
        """
        Convert the graph to a Mermaid diagram.

        Returns
        -------
        str
            The Mermaid diagram as a string.
        """

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

    def _to_uplink_dto(self) -> uplink.FlowUpdateDTO:
        """
        Convert the graph to an uplink DTO for communication with the platform.

        Returns
        -------
        uplink.FlowUpdateDTO
            Data transfer object for the flow graph.
        """

        return uplink.FlowUpdateDTO(
            pipeline_graph=uplink.FlowDTO(
                steps=[
                    uplink.StepDTO(
                        id=step.definition.get_id(),
                        app_id=step.definition.get_app_id(),
                        docs=step.docstring,
                        predecessors=[s.definition.get_id() for s in step.predecessors],
                    )
                    for step in self.steps
                ],
                nodes=[
                    uplink.NodeDTO(
                        id=node.id,
                        parent_id=node.parent.definition.get_id(),
                        predecessor_ids=[p.id for p in node.predecessors],
                        status=node.status,
                        run_id=node.run_id,
                    )
                    for step in self.steps
                    for node in step.nodes
                ],
            ),
        )

    def __debug_print(self):
        """
        Print debug information about the flow graph.

        This method logs internal information about the flow graph,
        including flow name, version information, and step details.
        """

        utils.log_internal(f"Flow: {self.flow_spec.__class__.__name__}")
        utils.log_internal(f"nextpipe: {__version__}")
        utils.log_internal(f"nextmv: {version('nextmv')}")
        utils.log_internal("Flow graph steps:")
        for step in self.steps:
            utils.log_internal("Step:")
            utils.log_internal(f"  Definition: {step.definition}")
            utils.log_internal(f"  Docstring: {step.docstring}")


class StepVisitor(ast.NodeVisitor):
    """
    AST visitor for finding step functions in a flow class.

    This visitor traverses the abstract syntax tree of a flow class
    and identifies all methods decorated with @step.

    Parameters
    ----------
    steps : list[FlowStep]
        List to collect found steps.
    flow_class : type
        The flow class to visit.

    Attributes
    ----------
    steps : list[FlowStep]
        List to collect found steps.
    flow_class : type
        The flow class being visited.
    """

    def __init__(self, steps: list[FlowStep], flow_class: type):
        """
        Initialize a StepVisitor.

        Parameters
        ----------
        steps : list[FlowStep]
            List to collect found steps.
        flow_class : type
            The flow class to visit.
        """

        self.steps = steps
        self.flow_class = flow_class
        super().__init__()

    def visit_FunctionDef(self, step_function):
        """
        Visit a function definition node in the AST.

        If the function has a step decorator, it will be added to the steps list.

        Parameters
        ----------
        step_function : ast.FunctionDef
            The function definition node.
        """

        func = getattr(self.flow_class, step_function.name)
        if hasattr(func, "is_step"):
            self.steps.append(FlowStep(step_function, func.step, func.__doc__))


## EXECUTION


class Runner:
    """
    Handles the execution of a flow graph.

    This class is responsible for preparing inputs for steps, creating execution nodes,
    dispatching jobs to the thread pool, and monitoring execution progress.

    Parameters
    ----------
    spec : FlowSpec
        The flow specification being executed.
    graph : FlowGraph
        The flow graph to execute.
    config : config.Configuration
        Configuration for the runner.
    uplink : uplink.UplinkClient
        Client for communicating with the Nextmv platform.

    Attributes
    ----------
    spec : FlowSpec
        The flow specification being executed.
    graph : FlowGraph
        The flow graph to execute.
    uplink : uplink.UplinkClient
        Client for communicating with the Nextmv platform.
    pool : threads.Pool
        Thread pool for executing steps.
    jobs : list
        List of jobs.
    node_idxs : dict
        Dictionary of node indices.
    fail : bool
        Whether the flow has failed.
    fail_reason : str or None
        Reason for the flow failure, if any.
    lock_fail : threading.Lock
        Lock for updating fail state.
    lock_running : threading.Lock
        Lock for updating running steps.
    """

    def __init__(
        self,
        spec: FlowSpec,
        graph: FlowGraph,
        config: config.Configuration,
        uplink: uplink.UplinkClient,
    ):
        """
        Initialize a Runner.

        Parameters
        ----------
        spec : FlowSpec
            The flow specification being executed.
        graph : FlowGraph
            The flow graph to execute.
        config : config.Configuration
            Configuration for the runner.
        uplink : uplink.UplinkClient
            Client for communicating with the Nextmv platform.
        """

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
        Prepare the inputs for a step.

        The inputs are either collected from predecessors or the flow input is used
        (if the step has no predecessors). If the step is a 'foreach' step, the input
        is repeated for each item in the result of the predecessor. If multiple
        predecessors are defined as 'foreach', the inputs are combined in a cartesian
        product. If the step itself is defined as 'repeat', the resulting inputs are
        repeated for each repetition. The result of the step is a list of results,
        one for each final input (after combining predecessors, 'foreach', 'repeat'
        and potential further modifiers).

        Parameters
        ----------
        step : FlowStep
            The step to prepare inputs for.

        Returns
        -------
        list[list[any]]
            List of input lists for the step.

        Raises
        ------
        Exception
            If there are too many inputs for the step.
        """

        # If the step has no predecessors, the input is the flow input.
        if not step.predecessors:
            inputs = [self.spec.input]
            if step.definition.is_repeat():
                inputs = inputs * step.definition.get_repetitions()
            return inputs
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
            # Make sure that we only pass one list as the input.
            inputs = [[inputs]]
        # If the step is a 'repeat' step, repeat the inputs for each repetition.
        if step.definition.is_repeat():
            inputs = inputs * step.definition.get_repetitions()
        if len(inputs) > self.spec.config.max_step_inputs:
            raise Exception(
                f"Step {step.definition.get_id()} has too many inputs ({len(inputs)}). "
                + f"Maximum allowed is {self.graph.flow_spec.config.max_step_inputs}."
            )
        return inputs

    def __node_start_callback(self, job: threads.Job):
        """
        Callback function called when a job is started.

        This function updates the node status to running and informs the platform
        about the node update.

        Parameters
        ----------
        job : threads.Job
            The job that was started.
        """

        reference: FlowNode = job.reference
        reference.status = STATUS_RUNNING
        # Inform the platform about the node update
        self.uplink.submit_update(self.graph._to_uplink_dto())

    def __node_done_callback(self, job: threads.Job):
        """
        Callback function called when a job is completed.

        This function updates the node status to succeeded or failed,
        stores the result or error, and informs the platform about the
        node update. If the job failed, the flow is marked as failed.

        Parameters
        ----------
        job : threads.Job
            The job that was completed.
        """

        reference: FlowNode = job.reference
        reference.status = STATUS_SUCCEEDED if job.error is None else STATUS_FAILED
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
        self.uplink.submit_update(self.graph._to_uplink_dto())

    @staticmethod
    def __run_step(node: FlowNode, inputs: list[object], client: Client) -> Union[list[object], object, None]:
        """
        Execute a step with the given inputs.

        This method handles the execution of different types of steps
        (app steps and regular function steps).

        Parameters
        ----------
        node : FlowNode
            The node to run.
        inputs : list[object]
            Input data for the step.
        client : Client
            Nextmv client for API access.

        Returns
        -------
        Union[list[object], object, None]
            The result of the step execution.

        Raises
        ------
        Exception
            If an app step has more than one predecessor.
        """

        utils.log_internal(f"Running node {node.id}")

        # Run the step
        if node.parent.definition.is_app():
            app_step: decorators.App = node.parent.definition.app
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
                name = app_run_config.name if app_run_config.name else node.id
                app_run_options = app_run_config.get_options()
                # Merge the options from the app decorator with the options from the
                # AppRunConfig. AppRunConfig options take precedence.
                options = app_step.options | app_run_options
            else:
                # If the input is not AppRunConfig, we use it directly.
                input = inputs[0]
                options = app_step.options
                name = node.id

            # Modify the polling options set for the step (by default or by the
            # user) so that the initial delay is randomized and the stopping
            # callback is configured as the node being cancelled if the user
            # doesn't want to override it.
            polling_options = copy.deepcopy(app_step.polling_options)
            delay = random.uniform(0, 5)  # For lack of a better idea...
            polling_options.initial_delay = delay
            if polling_options.stop is None:
                polling_options.stop = lambda: node.cancel

            run_args = (
                [],  # No nameless arguments
                {  # We use the named arguments to pass the user arguments to the run function
                    "input": input,
                    "run_options": options,
                    "polling_options": polling_options,
                    "name": name,
                },
            )

            # Prepare the application itself.
            app = Application(
                client=client,
                id=app_step.app_id,
                default_instance_id=app_step.instance_id,
            )

            # Run the application
            result = app.new_run_with_result(
                *run_args[0],
                **run_args[1],
            )
            run_id = result.id
            node.run_id = run_id

            # Return result (do not unwrap if full result is requested)
            if app_step.full_result:
                return result
            return result.output

        else:
            spec = inspect.getfullargspec(node.parent.definition.function)
            if len(spec.args) == 0:
                output = node.parent.definition.function()
            else:
                output = node.parent.definition.function(*inputs)
            return output

    def __create_job(self, node: FlowNode, inputs: Union[list[Any], Any]) -> threads.Job:
        """
        Create a job for executing a step.

        Parameters
        ----------
        node : FlowNode
            The node to create a job for.
        inputs : Union[list[Any], Any]
            Input data for the step.

        Returns
        -------
        threads.Job
            Job for executing the step.
        """

        # Convert input to list, if it is not already a list
        inputs = inputs if isinstance(inputs, list) else [inputs]
        # Create the job
        return threads.Job(
            target=self.__run_step,
            start_callback=self.__node_start_callback,
            done_callback=self.__node_done_callback,
            args=(node, inputs, self.spec.client),
            name=utils.THREAD_NAME_PREFIX + node.id,
            reference=node,
        )

    def run(self):
        """
        Run the flow.

        This method starts the uplink communication, executes the flow steps
        in the correct order based on dependencies, and handles failures.

        Raises
        ------
        RuntimeError
            If the flow execution fails.
        """

        # Start communicating updates to the platform
        try:
            self.uplink.submit_update(self.graph._to_uplink_dto())
            self.uplink.run_async()
        except Exception as e:
            self.uplink.terminate()
            utils.log_internal(f"Failed to update graph with platform: {e}")

        # Start running the flow
        open_steps: set[FlowStep] = set(self.graph.start_steps)
        running_steps: set[FlowStep] = set()
        closed_steps: set[FlowStep] = set()

        # Run the steps in parallel
        while open_steps or running_steps:
            while True:
                # Get the first step from the open steps which has all its predecessors done
                step = next(iter(filter(lambda n: all(p in closed_steps for p in n.predecessors), open_steps)), None)
                if step is None:
                    # No more steps to run at this point. Wait for the remaining tasks to finish.
                    break
                open_steps.remove(step)
                # Skip the step if it is optional and the condition is not met
                if step.definition.skip():
                    utils.log_internal(f"Skipping step {step.definition.get_id()}")
                    # Create dummy node
                    node = FlowNode(step, 0)
                    node.status = STATUS_SUCCEEDED
                    node.result = None
                    step.nodes.append(node)
                    closed_steps.add(step)
                    open_steps.update(step.successors)
                    self.uplink.submit_update(self.graph._to_uplink_dto())
                    continue
                # Run the node asynchronously
                with self.lock_running:
                    running_steps.add(step)
                inputs = self.__prepare_inputs(step)
                for i, input in enumerate(inputs):
                    node = FlowNode(step, i)
                    job = self.__create_job(node, input)
                    self.pool.run(job)
                    step.nodes.append(node)
                    self.uplink.submit_update(self.graph._to_uplink_dto())

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
                # Raise an exception if the flow failed
                with self.lock_fail:
                    if self.fail:
                        # Issue cancel to all nodes
                        for step in running_steps:
                            for node in step.nodes:
                                node.cancel = True
                                node.status = STATUS_FAILED
                        # Submitting the final state and terminating uplink causes the last
                        # update to be send to the platform (reflecting the final state).
                        self.uplink.submit_update(self.graph._to_uplink_dto())
                        self.uplink.terminate()  # This will issue the final update.
                        raise RuntimeError(f"Flow failed: {self.fail_reason}")

        # Terminate uplink
        self.uplink.terminate()
