import glob
import os
import time

import nextmv


def main():
    options = nextmv.Options(
        nextmv.Option("input", str, "inputs/", "Path to input file.", False),
        nextmv.Option("output", str, "outputs/solutions/", "Path to output file.", False),
        nextmv.Option("duration", float, 1.0, "Runtime duration (in seconds).", False),
    )

    # Read and prepare the input data.
    input_data = read_input(options.input)

    # Log information about the input files.
    nextmv.log(f"Size of input files (count: {len(input_data)}):")
    for file_path, content in input_data.items():
        nextmv.log(f"  {file_path}: {len(content)} bytes")

    # Sleep for the specified duration.
    nextmv.log(f"Sleeping for {options.duration} seconds...")
    time.sleep(options.duration)
    nextmv.log("Woke up from sleep.")

    # Write the output.
    write_output(options.output, input_data)


def read_input(input_path: str) -> dict[str, bytes]:
    """Reads the input files to memory."""
    input_files = glob.glob(os.path.join(input_path, "**/*"), recursive=True)
    content = {}
    for file_path in input_files:
        if os.path.isfile(file_path):
            with open(file_path, "rb") as file:
                nextmv.log(f"Reading file: {file_path}")
                content[file_path] = file.read()
    return content


def write_output(output_path: str, content: dict[str, bytes]) -> None:
    """Writes the given output files."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for file_path, data in content.items():
        output_file_path = os.path.join(output_path, os.path.basename(file_path))
        with open(output_file_path, "wb") as file:
            nextmv.log(f"Writing file: {output_file_path}")
            file.write(data)


if __name__ == "__main__":
    main()
