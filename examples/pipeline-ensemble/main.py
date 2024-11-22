import json
import os

import nextmv

from nextpipe import FlowSpec, app, needs, repeat, step

# Define the options for the workflow
parameters = [
    nextmv.Parameter("instance", str, "devint", "App instance to use. Default is devint.", False),
]
options = nextmv.Options(*parameters)


# >>> Workflow definition
class Flow(FlowSpec):
    @app(
        app_id="routing-nextroute",
        instance_id=options.instance,
        parameters={"model.constraints.enable.cluster": True},
    )
    @repeat(repetitions=3)
    @step
    def run_nextroute():
        """Runs the model."""
        pass

    @needs(predecessors=[run_nextroute])
    @step
    def pick_best(results: list[dict]):
        """Aggregates the results."""
        best_solution_idx = min(
            range(len(results)),
            key=lambda i: results[i]["statistics"]["result"]["value"],
        )
        return results[best_solution_idx]


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
