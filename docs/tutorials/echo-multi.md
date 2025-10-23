# The `echo-multi` app

Several examples assume you have a Nextmv application called `echo-multi`. This
is just a simple application created for demonstration purposes. It takes the
input files and echoes them as output files.

Let's get set up with the `echo-multi` application. Before starting:

1. [Sign up][signup] for a Nextmv account.
2. Get your API key. Go to [Team > API Key][api-key].

Make sure that you have your API key set as an environment variable:

```bash
export NEXTMV_API_KEY="<YOUR-API-KEY>"
```

Now that you have a valid Nextmv account and API key, let's create the
`echo-multi` Nextmv app (start in an empty directory).

1. Create a folder `inputs/` and add some sample input files to it. For example,
   you can create two text files `input.csv` and `input.txt` with some sample
   content.
1. In a new directory, create a file called `main.py` with the code for the
   basic app that echoes the input.

    ```python
    import glob

    import os
    import time

    import nextmv

    def main():
        options = nextmv.Options(
            nextmv.Option("input", str, "inputs/", "Path to input file.", False),
            nextmv.Option("output", str, "outputs/", "Path to output file.", False),
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
    ```

    Note that the application uses the [`nextmv`][nextmv-docs] library. This
    library is a dependency of `nextpipe` and should be installed automatically
    when you install `nextpipe`.

    You may run the app locally to test it:

    ```bash
    python main.py
    ```

1. Create a `requirements.txt` file with the following requirements for running
   the app:

    ```requirements.txt
    nextmv
    ```

1. Create an `app.yaml` file (the app manifest) with the following instructions:

    ```yaml
    type: python
    runtime: ghcr.io/nextmv-io/runtime/python:3.11
    files:
        - main.py
    python:
        pip-requirements: requirements.txt
    ```

1. Push the application to your Nextmv account. Create a `push.py` script in
   the same directory with the following code:

    ```python
    import os

    from nextmv import cloud

    client = cloud.Client(api_key=os.getenv("NEXTMV_API_KEY"))
    app = cloud.Application.new(client=client, name="echo-multi", id="echo-multi", description="Sample echo multi-file app.", exist_ok=True)
    app.push(verbose=True)
    ```

1. Execute the `push.py` script to push the app to your Nextmv account:

    ```bash
    $ python push.py
    💽 Starting build for Nextmv application.
    🐍 Bundling Python dependencies.
    📋 Copied files listed in "app.yaml" manifest.
    📦 Packaged application (588 files, 5.39 MiB).
    🌟 Pushing to application: "echo-multi".
    💥️ Successfully pushed to application: "echo-multi".
    {
    "app_id": "echo-multi",
    "endpoint": "https://api.cloud.nextmv.io",
    "instance_url": "v1/applications/echo-multi/runs?instance_id=devint"
    }
    ```

    Alternatively, you can use the [Nextmv CLI][nextmv-cli] to create and push the app:

    ```bash
    nextmv app create -a echo-multi -n echo-multi -d "Sample echo multi-file app."
    nextmv app push -a echo-multi
    ```

Now you are ready to run the examples.

[signup]: https://cloud.nextmv.io
[api-key]: https://cloud.nextmv.io/team/api-keys
[nextmv-docs]: https://nextmv-py.readthedocs.io/en/latest/nextmv/
[nextmv-cli]: https://docs.nextmv.io/docs/using-nextmv/reference/cli
