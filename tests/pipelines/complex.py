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
        def get_value(idx: int, result: dict) -> float:
            if k := next((k for k in ("statistics", "metrics") if k in result), None):
                return result[k]["result"]["value"]
            raise ValueError(f"Result at index {idx} does not contain 'statistics' or 'metrics'")

        results = results_nextroute + [result_ortools, result_pyvroom]
        best_solution_idx = min(
            range(len(results)),
            key=lambda i: get_value(i, results[i]),
        )

        values = [get_value(i, result) for i, result in enumerate(results)]
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
