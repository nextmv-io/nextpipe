# Complex example

A more complex pipeline combining some concepts.

## Graph

```mermaid
graph TD
  fetch_data(fetch_data)
  fetch_data --> run_nextroute
  fetch_data --> run_ortools
  fetch_data --> run_pyvroom
  run_nextroute{ }
  run_nextroute_join{ }
  run_nextroute_0(run_nextroute_0)
  run_nextroute --> run_nextroute_0
  run_nextroute_0 --> run_nextroute_join
  run_nextroute_1(run_nextroute_1)
  run_nextroute --> run_nextroute_1
  run_nextroute_1 --> run_nextroute_join
  run_nextroute_2(run_nextroute_2)
  run_nextroute --> run_nextroute_2
  run_nextroute_2 --> run_nextroute_join
  run_nextroute_join --> pick_best
  run_ortools(run_ortools)
  run_ortools --> pick_best
  run_pyvroom(run_pyvroom)
  run_pyvroom --> pick_best
  pick_best(pick_best)
```

## Usage

```bash
nextmv app push -a <app-id>
echo '{}' | nextmv app run -a <app-id> -e "8c16gb12h"
```
