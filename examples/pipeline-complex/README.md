# Complex example

A more complex pipeline combining some concepts.

## Graph

```mermaid
graph LR
  prepare(prepare)
  prepare --> convert
  prepare --> run_nextroute
  convert(convert)
  convert --> run_ortools
  convert --> run_pyvroom
  run_nextroute{ }
  run_nextroute_join{ }
  run_nextroute_0(run_nextroute_0)
  run_nextroute --> run_nextroute_0
  run_nextroute_0 --> run_nextroute_join
  run_nextroute_1(run_nextroute_1)
  run_nextroute --> run_nextroute_1
  run_nextroute_1 --> run_nextroute_join
  run_nextroute_join --> pick_best
  run_ortools(run_ortools)
  run_ortools --> pick_best
  run_pyvroom(run_pyvroom)
  run_pyvroom --> pick_best
  pick_best(pick_best)
```

## Pre-requisites

- Subscribe to the following marketplace apps and name them as follows:
  - _Nextmv Routing_: `routing-nextroute`
  - _OR-Tools Routing_: `routing-ortools`
  - _PyVroom Routing_: `routing-pyvroom`

## Usage

```bash
nextmv app push -a <app-id>
curl "https://gist.githubusercontent.com/merschformann/a90959b87d1360b604e4a9f6457340ca/raw/661e631376bdf78a07548a3cd136c1fc6e47c639/muenster.json" | nextmv app run -a <app-id>
```
