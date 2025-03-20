import json
import os

import nextmv

from nextpipe import AppOption, AppOptions, FlowSpec, app, convert, foreach, join, needs, read_csv, step


class Flow(FlowSpec):
    @step
    def prepare(csv_files: list[str]):
        """Prepares the data."""
        csvs = [read_csv(f) for f in csv_files]
        jsons = [convert(csv) for csv in csvs]
        search_dive = AppOptions(AppOption("search_strategy", "dive"))
        search_exhaustive = AppOptions(AppOption("search_strategy", "exhaustive"))
        options = [search_dive if len(j["stops"]) > 100 else search_exhaustive for j in jsons]
        return zip(csv_files, options)

    @app(app_id="routing")
    @needs(predecessors=[prepare])
    @foreach  # This causes the step to be executed for each item in the input list
    @step
    def solve():
        """Runs the model."""
        pass

    # @app(app_id="routing")
    # @needs(predecessors=[prepare])
    # @foreach  # This causes the step to be executed for each item in the input list
    # @prep  # This uses the function body that is normally unused as a preparation step for the app run
    # @step
    # def solve(input: dict):
    #     """Runs the model."""
    #     search_dive = AppOptions(AppOption("search_strategy", "dive"))
    #     search_exhaustive = AppOptions(AppOption("search_strategy", "exhaustive"))
    #     return (input, search_dive if len(input["stops"]) > 100 else search_exhaustive)

    @needs(predecessors=[solve])
    @join  # This collects the results from the 'foreach' previous step and combines them into a list passed as the arg
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
