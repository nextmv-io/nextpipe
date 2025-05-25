import csv
import json
from typing import Any

import nextmv.cloud
import requests

from nextpipe import FlowSpec, app, log, needs, repeat, step


class Workflow(FlowSpec):
    @step
    def fetch(_: dict[str, Any]) -> str:
        """Fetch CSV data from external source."""

        file_url = "https://gist.githubusercontent.com/merschformann/5dc2d06b246f924f8c65e93dd3c646e2/raw/fca52de5b7b9a1396e8d9525f8006488ac3467c9/muenster-stops.csv"
        response = requests.get(file_url)

        return response.text

    @needs(predecessors=[fetch])
    @step
    def convert(input_csv: str) -> dict[str, Any]:
        """Convert CSV data to JSON."""

        reader = csv.reader(input_csv.splitlines())
        next(reader)  # skip header

        return {
            "vehicles": [
                {
                    "id": f"vehicle-{i}",
                    "start_location": {"lon": 7.62558, "lat": 51.96223},
                    "end_location": {"lon": 7.62558, "lat": 51.96223},
                    "start_time": "2024-09-04T11:00:00+00:00",
                    "speed": 10,
                    "capacity": 27,
                }
                for i in range(20)
            ],
            "stops": [
                {
                    "id": row[0],
                    "location": {"lon": float(row[1]), "lat": float(row[2])},
                    "quantity": -1,
                    "unplanned_penalty": 2000000000,
                }
                for row in reader
            ],
        }

    @needs(predecessors=[convert])
    @step
    def align(input: dict[str, Any]) -> dict[str, Any]:
        """Align the input data for the solver."""

        clone = json.loads(json.dumps(input))
        for stop in [s for s in clone["stops"] if "quantity" in s]:
            stop["quantity"] *= -1

        return clone

    @app(
        app_id="routing-nextroute",
        instance_id="latest",
        parameters={"solve.duration": "30s"},
        full_result=True,
    )
    @repeat(repetitions=3)
    @needs(predecessors=[convert])
    @step
    def solve_nextroute() -> dict[str, Any]:
        """Solve the problem using the Nextroute solver."""
        pass

    @app(app_id="routing-pyvroom", instance_id="latest", full_result=True)
    @needs(predecessors=[align])
    @step
    def solve_vroom() -> dict[str, Any]:
        """Solve the problem using the Vroom solver."""
        pass

    @app(app_id="routing-ortools", instance_id="latest", full_result=True)
    @needs(predecessors=[align])
    @step
    def solve_ortools() -> dict[str, Any]:
        """Solve the problem using the OR-Tools solver."""
        pass

    @needs(predecessors=[solve_nextroute, solve_vroom, solve_ortools])
    @step
    def pick_best(
        nextroute_results: list[nextmv.cloud.RunResult],
        vroom_result: nextmv.cloud.RunResult,
        ortools_result: nextmv.cloud.RunResult,
    ):
        """Pick the best solution based on the result value."""

        results = nextroute_results + [vroom_result, ortools_result]
        best_solution_idx = min(
            range(len(results)),
            key=lambda i: results[i].output["statistics"]["result"]["value"],
        )

        for result in results:
            log(f"{result.metadata.application_id}: " + f"{result.output['statistics']['result']['value']}")

        return results[best_solution_idx].output


def main():
    """Runs the workflow."""

    # Run workflow
    flow = Workflow("DecisionFlow", None)
    flow.run()

    # Write the result
    result = flow.get_result(flow.pick_best)
    nextmv.write(result)


if __name__ == "__main__":
    main()
