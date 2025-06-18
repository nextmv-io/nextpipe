import copy
import json

import nextmv
import nextmv.cloud

from nextpipe import AppOption, AppRunConfig, FlowSpec, app, foreach, join, needs, step


class Flow(FlowSpec):
    @foreach()  # Run the successor step for each item in the result list of this step
    @step
    def prepare(data: dict):
        """
        Creates 3 copies of the input and configures them for 3 different app options.
        """
        inputs = [copy.deepcopy(data) for _ in range(3)]
        run_configs = [AppRunConfig(input, [AppOption("param", i)]) for i, input in enumerate(inputs)]
        return run_configs

    @app(app_id="echo")
    @needs(predecessors=[prepare])
    @step
    def solve():
        """
        Runs the model.
        """
        pass

    @needs(predecessors=[solve])
    @join()  # Collect the results from the previous 'foreach' step and combine them into a list passed as the arg
    @step
    def merge(results: list[dict]):
        """Merges the results."""
        return results


def main():
    # Load input data
    input = nextmv.load()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()

    # Write out the result
    print(json.dumps(flow.get_result(flow.merge)))


if __name__ == "__main__":
    main()
