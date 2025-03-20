import copy
import json
import os

import nextmv
import nextmv.cloud

from nextpipe import AppOption, AppRunConfig, FlowSpec, app, foreach, join, needs, optional, step


class Flow(FlowSpec):
    @foreach()
    @step
    def prepare(data: dict):
        """Prepares the data."""
        inputs = [copy.deepcopy(data) for _ in range(3)]
        run_configs = [AppRunConfig(input, [AppOption("param", i)]) for i, input in enumerate(inputs)]
        return run_configs

    @app(app_id="echo")
    @needs(predecessors=[prepare])
    @optional(condition=lambda _: True)
    @step
    def solve():
        """Runs the model."""
        pass

    @needs(predecessors=[solve])
    @join()  # This collects the results from the 'foreach' previous step and combines them into a list passed as the arg
    @step
    def enhance(results: list[dict]):
        """Enhances the result."""
        return results


def main():
    # Read API key from file (until secrets management support)
    with open("key.json") as f:
        os.environ["NEXTMV_API_KEY"] = json.load(f)["nextmv_api_key"]

    # Load input data
    input = nextmv.load_local()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()

    # Write out the result
    print(json.dumps(flow.get_result(flow.enhance)))


if __name__ == "__main__":
    main()
