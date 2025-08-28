import argparse
import glob
import multiprocessing
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Logs randomly and echoes the input.")
    parser.add_argument(
        "-input",
        default="inputs",
        help="Path to input directory. Default is 'inputs'.",
    )
    parser.add_argument(
        "-output",
        default="outputs/solutions",
        help="Path to output directory. Default is 'outputs'.",
    )
    parser.add_argument(
        "-duration",
        type=float,
        default=300.0,
        help="Duration of the simulation in seconds.",
    )
    parser.add_argument(
        "-threads",
        default=0,
        type=int,
        help="Number of threads to use for the simulation.",
    )
    args = parser.parse_args()

    # Set the number of threads to the number of CPUs if not specified.
    if args.threads == 0:
        args.threads = os.cpu_count()

    # Read and prepare the input data.
    input_data = read_input(args.input)

    # Log information about the input files.
    log(f"Size of input files (count: {len(input_data)}):")
    for file_path, content in input_data.items():
        log(f"  {file_path}: {len(content)} bytes")

    # Simulate some load.
    simulate(args.threads, args.duration)

    # Write the output.
    write_output(args.output, input_data)


def worker(timeout: float = 1.0):
    """
    Simulates some CPU-intensive computation.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        result = 0
        for i in range(1000000):
            result += i


def simulate(thread_count: int, duration: float):
    """
    Simulates some load for the given duration and number of threads.
    """
    log(f"Simulating {thread_count} threads for {duration} seconds.")

    # Start the processes.
    processes = [multiprocessing.Process(target=worker, args=(duration,)) for _ in range(thread_count)]
    for process in processes:
        process.start()

    # Wait for the processes to finish.
    for process in processes:
        process.join()

    log("Simulating work done.")


def log(message: str) -> None:
    """Logs a message. We need to use stderr since stdout is used for the solution."""

    print(message, file=sys.stderr)


def read_input(input_path: str) -> dict[str, bytes]:
    """Reads the input files."""
    input_files = glob.glob(os.path.join(input_path, "**/*"), recursive=True)
    content = {}
    for file_path in input_files:
        if os.path.isfile(file_path):
            with open(file_path, "rb") as file:
                log(f"Reading file: {file_path}")
                content[file_path] = file.read()
    return content


def write_output(output_path: str, content: dict[str, bytes]) -> None:
    """Writes the output files."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for file_path, data in content.items():
        output_file_path = os.path.join(output_path, os.path.basename(file_path))
        with open(output_file_path, "wb") as file:
            log(f"Writing file: {output_file_path}")
            file.write(data)


if __name__ == "__main__":
    main()
