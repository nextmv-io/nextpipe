import json
import os

import nextmv

from nextpipe import FlowSpec, app, needs, repeat, step


# >>> Workflow definition
class Flow(FlowSpec):
    @step
    def prepare(input: dict):
        """Prepares the data."""
        return input

    @repeat(repetitions=2)
    @app(app_id="routing-nextroute")
    @needs(predecessors=[prepare])
    @step
    def run_nextroute():
        """Runs the model."""
        pass

    @app(app_id="routing-ortools")
    @needs(predecessors=[prepare])
    @step
    def run_ortools():
        """Runs the model."""
        pass

    @app(app_id="routing-pyvroom")
    @needs(predecessors=[prepare])
    @step
    def run_pyvroom():
        """Runs the model."""
        pass

    @needs(predecessors=[run_nextroute, run_ortools, run_pyvroom])
    @step
    def pick_best(
        results_nextroute: list[dict],
        result_ortools: dict,
        result_pyvroom: dict,
    ):
        """Aggregates the results."""
        results = results_nextroute + [result_ortools, result_pyvroom]
        best_solution_idx = min(
            range(len(results)),
            key=lambda i: results[i]["statistics"]["result"]["value"],
        )

        values = [result["statistics"]["result"]["value"] for result in results]
        values.sort()
        nextmv.log(f"Values: {values}")

        # For test stability reasons, we always return the or-tools result
        _ = results.pop(best_solution_idx)
        return result_ortools


def main():
    # Read API key from file (until secrets management support)
    with open("key.json") as f:
        os.environ["NEXTMV_API_KEY"] = json.load(f)["nextmv_api_key"]

    # Load input data
    input = nextmv.load_local()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()
    result = flow.get_result(flow.pick_best)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
