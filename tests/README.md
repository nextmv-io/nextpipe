# Tests

This folder contains tests for the project. Since pipeline apps typically utilize other apps, some apps need to be available in the account that runs the tests.

## Setup apps

Setup the apps as follows:

```bash
# Setup echo app
cd apps/echo
nextmv app create -a echo -n "Echo" || true
nextmv app push -a echo
cd ../..

# Setup nextroute
nextmv community clone -a go-nextroute
cd go-nextroute
nextmv app create -a routing-nextroute -n "Routing Nextroute" || true
nextmv app push -a routing-nextroute
cd ..

# Setup pyvroom
nextmv community clone -a python-pyvroom-routing
cd python-pyvroom-routing
nextmv app create -a routing-pyvroom -n "Routing Pyvroom" || true
nextmv app push -a routing-pyvroom
cd ..

# Setup ortools
nextmv community clone -a python-ortools-routing
cd python-ortools-routing
nextmv app create -a routing-ortools -n "Routing Ortools" || true
nextmv app push -a routing-ortools
cd ..
```

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
