# JSON echo

This is a sample app that reads input files and echoes them as output. This app
is meant to be used for the `multi-file` I/O format.

This app is used for testing.

## Usage

```bash
python main.py -threads 10 -duration 10
```

## Push to Nextmv

```bash
nextmv app create -a echo-multi -n "JSON echo multi-file" -d "This is a sample app that reads input files and echoes them as output."
nextmv app push -a echo-multi
```
