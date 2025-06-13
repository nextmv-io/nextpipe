# The `echo` app

Several examples assume you have a Nextmv application called `echo`. This is
just a simple application created for demonstration purposes. It takes the
input and echoes it with some minor modifications.

Let's get set up with the `echo` application. Before starting:

1. [Sign up][signup] for a Nextmv account.
2. Get your API key. Go to [Team > API Key][api-key].

Make sure that you have your API key set as an environment variable:

```bash
export NEXTMV_API_KEY="<YOUR-API-KEY>"
```

Now that you have a valid Nextmv account and API key, let's create the `echo`
Nextmv app.

1. In a new directory, create a file called `main.py` with the code for the
   basic app that echoes the input.

    ```python
    import sys
    import time

    import nextmv

    before = time.time()
    input = nextmv.load()
    output = nextmv.Output(
        solution={
            "echo": {
                "data": input.data,
                "args": sys.argv[1:],
            },
        },
        statistics={"run": {"duration": time.time() - before}},
    )
    nextmv.write(output)
    ```

    Note that the application uses the [`nextmv`][nextmv-docs] library. This
    library is a dependency of `nextpipe` and should be installed automatically
    when you install `nextpipe`.

    You may run the app locally to test it:

    ```bash
    echo '{"hello": "world!"}' | python main.py
    ```

1. Create a `requirements.txt` file with the following
   requirements for running the app:

    ```requirements.txt
    nextmv>=0.28.0
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
    app = cloud.Application.new(client=client, name="echo", id="echo", description="Sample echo app.", exist_ok=True)
    app.push(verbose=True)
    ```

1. Execute the `push.py` script to push the app to your Nextmv account:

    ```bash
    $ python push.py
    💽 Starting build for Nextmv application.
    🐍 Bundling Python dependencies.
    📋 Copied files listed in "app.yaml" manifest.
    📦 Packaged application (552 files, 5.04 MiB).
    🌟 Pushing to application: "echo".
    💥️ Successfully pushed to application: "echo".
    {
      "app_id": "echo",
      "endpoint": "https://api.cloud.nextmv.io",
      "instance_url": "v1/applications/echo/runs?instance_id=devint"
    }
    ```

    Alternatively, you can use the [Nextmv CLI][nextmv-cli] to create and push the app:

    ```bash
    nextmv app create -a echo -n echo -d "Sample echo app."
    nextmv app push -a echo
    ```

Now you are ready to run the examples.

[signup]: https://cloud.nextmv.io
[api-key]: https://cloud.nextmv.io/team/api-keys
[nextmv-docs]: https://nextmv-py.readthedocs.io/en/latest/nextmv/
[nextmv-cli]: https://docs.nextmv.io/docs/using-nextmv/reference/cli
