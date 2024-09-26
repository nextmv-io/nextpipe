# CSV to JSON multi-solver ensemble example

An example of a pipeline fetching CSV data, converting it to JSON, ensembling across multiple solvers and repetitions and picking the best result.

## Graph

```mermaid
graph TD
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

## Usage

```bash
nextmv app push -a <app-id>
echo '{}' | nextmv app run -a <app-id> -e "8c16gb12h"
```
