# CSV to JSON multi-solver ensemble example

An example of a pipeline fetching CSV data, converting it to JSON, ensembling across multiple solvers and repetitions and picking the best result.

## Graph

```mermaid
graph LR
  fetch(fetch)
  fetch --> convert
  convert(convert)
  convert --> solve_nextroute
  convert --> solve_vroom
  convert --> solve_ortools
  solve_nextroute{ }
  solve_nextroute_join{ }
  solve_nextroute_0(solve_nextroute_0)
  solve_nextroute --> solve_nextroute_0
  solve_nextroute_0 --> solve_nextroute_join
  solve_nextroute_1(solve_nextroute_1)
  solve_nextroute --> solve_nextroute_1
  solve_nextroute_1 --> solve_nextroute_join
  solve_nextroute_2(solve_nextroute_2)
  solve_nextroute --> solve_nextroute_2
  solve_nextroute_2 --> solve_nextroute_join
  solve_nextroute_join --> pick_best
  solve_vroom(solve_vroom)
  solve_vroom --> pick_best
  solve_ortools(solve_ortools)
  solve_ortools --> pick_best
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
echo '{}' | nextmv app run -a <app-id>
```
