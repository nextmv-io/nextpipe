import json

import nextmv

from nextpipe import FlowSpec, needs, step


# >>> Workflow definition
class Flow(FlowSpec):
    @step
    def prepare(input: dict):
        """Prepares the data."""
        input["prepared"] = True
        return input

    @needs(predecessors=[prepare])
    @step
    def fail(result: dict):
        """A step that fails."""
        raise ValueError("Something went wrong")


def main():
    # Load input data
    input = nextmv.load()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()

    # Write out the result
    print(json.dumps(flow.get_result(flow.fail)))


if __name__ == "__main__":
    main()
