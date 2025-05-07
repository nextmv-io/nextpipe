import json
import os

import nextmv

from nextpipe import FlowSpec, app, needs, step


# >>> Workflow definition
class Flow(FlowSpec):
    @step
    def prepare(input: dict):
        """Prepares the data."""
        input["prepared"] = True
        return input

    @app(app_id="echo")
    @needs(predecessors=[prepare])
    @step
    def solve():
        """Runs the model."""
        pass

    @needs(predecessors=[solve])
    @step
    def enhance(result: dict):
        """Enhances the result."""
        output = result["solution"]  # Unwrap the solution
        output["echo"]["data"]["enhanced"] = True
        return output


def main():
    # Read API key from file (until secrets management support)
    with open("key.json") as f:
        os.environ["NEXTMV_API_KEY"] = json.load(f)["nextmv_api_key"]

    # Load input data
    input = nextmv.load()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()

    # Write out the result
    print(json.dumps(flow.get_result(flow.enhance)))


if __name__ == "__main__":
    main()
