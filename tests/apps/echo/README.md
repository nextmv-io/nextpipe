# JSON echo

This is a sample app that reads JSON from the input and writes it to the output.
Furthermore, it adds a statistics section to the output.

This app is used for testing.

## Usage

```bash
echo '{"hello": "world!"}' | python main.py
```

## Push to Nextmv

```bash
nextmv app create -a echo -n "JSON echo" -d "This is a sample app that reads JSON from the input and writes it to the output."
nextmv app push -a echo
```
