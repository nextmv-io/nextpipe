import os
import shutil

import nextmv
import nextmv.cloud

from nextpipe import FlowSpec, app, log, needs, step

options = nextmv.Options(
    nextmv.Option("input", str, "inputs/", "Path to input file.", False),
    nextmv.Option("output", str, "outputs/", "Path to output file.", False),
)


# >>> Workflow definition
class Flow(FlowSpec):
    # The first step receives the path to the input files directly (see main()) and
    # automatically zips the directory and passes it to the 'echo-multi' sub-app.
    @app(app_id="echo-multi")
    @step
    def solve1():
        """Runs a multi-file model."""
        pass

    # The second step receives the path to the output files from the first step. This path
    # will point to a temporary directory containing the output files from the first step.
    @needs(predecessors=[solve1])
    @step
    def transform(result_path: str):
        """Transforms the result for the next step."""
        # Just list the content of the result directory.
        log(f"Contents of result directory {result_path}:")
        for file_name in os.listdir(result_path):
            full_file_name = os.path.join(result_path, file_name)
            if os.path.isfile(full_file_name):
                log(f"- {file_name}")

        # Add a new file to the result for demonstration purposes.
        new_file_path = os.path.join(result_path, "additional_file.txt")
        with open(new_file_path, "w") as f:
            f.write("This is an additional file added in the transform step.\n")
        log(f"Added new file: {new_file_path}")

        return result_path

    # The third step receives the (modified) directory from the transform step and runs
    # another multi-file app on it.
    @app(
        app_id="echo-multi",
        # We specify the content type explicitly here. This is normally done via the app's
        # manifest, but we can do it explicitly like this too.
        run_configuration=nextmv.RunConfiguration(
            format=nextmv.Format(
                format_input=nextmv.FormatInput(input_type=nextmv.InputFormat.MULTI_FILE),
                format_output=nextmv.FormatOutput(output_type=nextmv.OutputFormat.MULTI_FILE),
            )
        ),
        full_result=True,
    )
    @needs(predecessors=[transform])
    @step
    def solve2(result: nextmv.cloud.RunResult):
        """Runs another multi-file model."""
        pass

    # The final step receives the output from 'solve2' as a full result object (see
    # 'full_result=True' above). In this case, the path to the output files is available
    # via 'result.output'.
    @needs(predecessors=[solve2])
    @step
    def prepare_output(result: nextmv.cloud.RunResult):
        """Transforms the result for the next step."""
        # Extract the path to the output files.
        result_path = result.output
        # Simply copy the files from the given directory to the expected output directory.
        os.makedirs(options.output, exist_ok=True)
        for file_name in os.listdir(result_path):
            full_file_name = os.path.join(result_path, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, options.output)


def main():
    # Run workflow (simply provide the path to the multi-file input)
    flow = Flow("DecisionFlow", options.input)
    flow.run()
    # The last step of the flow already prepares the output in the requested directory,
    # so no need to do anything here anymore.


if __name__ == "__main__":
    main()
