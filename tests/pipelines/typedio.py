import os
import shutil
import tempfile

import nextmv
import nextmv.cloud

from nextpipe import FlowSpec, app, needs, step

# TODO: remove debug helper
os.environ["NEXTMV_API_KEY"] = os.getenv("NEXTMV_API_KEY_PROD")


options = nextmv.Options(
    nextmv.Option("input", str, "inputs/", "Path to input file.", False),
    nextmv.Option("output", str, "outputs/", "Path to output file.", False),
)


# >>> Workflow definition
class Flow(FlowSpec):
    @app(app_id="echo-multi")
    @step
    def solve1():
        """Runs a multi-file model."""
        pass

    @needs(predecessors=[solve1])
    @step
    def transform(result_path: str):
        """Transforms the result for the next step."""
        # Simply copy the files from the given directory to a new temp directory.
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in os.listdir(result_path):
                full_file_name = os.path.join(result_path, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, temp_dir)

            # Add another small file to demonstrate this step passed.
            with open(os.path.join(temp_dir, "transformed.txt"), "w") as f:
                f.write("This file was added in the transform step.\n")

    @app(app_id="echo-multi", content_type=nextmv.InputFormat.MULTI_FILE)
    @needs(predecessors=[transform])
    @step
    def solve2(result: nextmv.cloud.RunResult):
        """Runs another multi-file model."""
        pass

    @needs(predecessors=[solve2])
    @step
    def prepare_output(result_path: str):
        """Transforms the result for the next step."""
        # Simply copy the files from the given directory to the expected output directory.
        os.makedirs(options.output, exist_ok=True)
        for file_name in os.listdir(result_path):
            full_file_name = os.path.join(result_path, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, options.output)

    # # >>>>

    # @step
    # def prepare(input: dict):
    #     """Prepares the data."""
    #     output = nextmv.Output(
    #         output_format=nextmv.OutputFormat.MULTI_FILE,
    #         solution_files=[nextmv.json_solution_file("echo", data=input)],
    #     )
    #     return output

    # @app(app_id="echo-multi")
    # @needs(predecessors=[prepare])
    # @step
    # def solve1():
    #     """Runs a model."""
    #     pass

    # @app(app_id="echo-multi")
    # @needs(predecessors=[solve1])
    # @step
    # def solve2():
    #     """Runs another model."""
    #     pass

    # @app(app_id="echo-multi")
    # @step
    # def solve3():
    #     """Runs another model."""
    #     pass

    # @needs(predecessors=[solve2, solve3])
    # @step
    # def enhance(result_solve2: nextmv.cloud.RunResult, result_solve3: nextmv.cloud.RunResult):
    #     """Enhances the result."""
    #     output = nextmv.Output(
    #         output_format=nextmv.OutputFormat.MULTI_FILE,
    #         solution_files=[
    #             nextmv.json_solution_file("enhanced_from_solve2", data=result_solve2.data),
    #             nextmv.json_solution_file("enhanced_from_solve3", data=result_solve3.data),
    #         ],
    #     )

    #     return output


def main():
    # Run workflow (simply provide the path to the multi-file input)
    flow = Flow("DecisionFlow", options.input)
    flow.run()
    # The last step of the flow already prepares the output, so no need to specify output here.


if __name__ == "__main__":
    main()
