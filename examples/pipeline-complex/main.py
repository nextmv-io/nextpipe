import json
import os

import nextmv
import requests

from nextpipe import FlowSpec, app, needs, repeat, step


# >>> Workflow definition
class Flow(FlowSpec):
    @step
    def fetch_data(_):
        """Fetches data from the database."""
        file_url = "https://gist.githubusercontent.com/merschformann/a90959b87d1360b604e4a9f6457340ca/raw/661e631376bdf78a07548a3cd136c1fc6e47c639/muenster.json"
        response = requests.get(file_url)
        return response.json()

    @repeat(repetitions=3)
    @app(app_id="routing-nextroute")
    @needs(predecessors=[fetch_data])
    @step
    def run_nextroute():
        """Runs the model."""
        pass

    @app(app_id="routing-ortools")
    @needs(predecessors=[fetch_data])
    @step
    def run_ortools():
        """Runs the model."""
        pass

    @app(app_id="routing-pyvroom")
    @needs(predecessors=[fetch_data])
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

        return results[best_solution_idx]


def main():
    # Read API key from file (until secrets management support)
    with open("key.json") as f:
        os.environ["NEXTMV_API_KEY"] = json.load(f)["nextmv_api_key"]

    # Run workflow
    flow = Flow("DecisionFlow", None)
    flow.run()
    result = flow.get_result(flow.pick_best)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
