import json

import nextmv

from nextpipe import FlowSpec, app, log, needs, repeat, step


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

        # Define value extractor for both output formats of the solvers.
        def get_value(sol: dict):
            return sol["metrics"]["result"]["value"] if "metrics" in sol else sol["statistics"]["result"]["value"]

        best_solution_idx = min(
            range(len(results)),
            key=lambda i: get_value(results[i]),
        )

        values = [get_value(result) for result in results]
        values.sort()
        log(f"Values: {values}")

        # For test stability reasons, we always return the or-tools result
        _ = results.pop(best_solution_idx)
        return result_ortools


def main():
    # Load input data
    input = nextmv.load()

    # Run workflow
    flow = Flow("DecisionFlow", input.data)
    flow.run()
    result = flow.get_result(flow.pick_best)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
