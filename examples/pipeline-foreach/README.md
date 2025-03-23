# Foreach fanout example

Example of a pipeline with a fanout step (`@foreach`) that runs the same input through a solve step with different app options.

## Graph

```mermaid
graph LR
  fanout{ }
  fanout(fanout)
  fanout -- foreach --> solve
  stats(stats)
  stats -- join --> merge
  solve(solve)
  solve -- join --> merge
  merge(merge)
```

## Pre-requisites

- Push the echo app as described in the [echo app README](../apps/echo/README.md)

## Usage

```bash
nextmv app push -a <app-id>
echo '{}' | nextmv app run -a <app-id>
```
