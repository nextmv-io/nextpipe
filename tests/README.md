# Tests

This folder contains tests for the project. Since pipeline apps typically utilize other apps, some apps need to be available in the account that runs the tests.

## Setup apps

Setup the custom apps as follows:

```bash
# Setup echo app
cd apps/echo
nextmv app create -a echo -n "Echo" || true
nextmv app push -a echo
cd ../..
```

Furthermore, subscribe to the following marketplace apps and name them as follows:

* _Nextmv Routing_: `routing-nextroute`
* _OR-Tools Routing_: `routing-ortools`
* _PyVroom Routing_: `routing-pyvroom`

## Testing

Run the tests as follows (from the root of the project):

```bash
export NEXTMV_API_KEY_NEXTPIPE=<api_key>
python -m unittest
```

Update the test expectations as follows:

```bash
export NEXTMV_API_KEY_NEXTPIPE=<api_key>
GOLDIE_UPDATE=1 python -m unittest
```
