# Ensemble example

A basic ensemble pipeline.

## Graph

```mermaid
graph LR
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
  pick_best(pick_best)
```

## Pre-requisites

- Subscribe to the following marketplace apps and name them as follows:
  - _Nextmv Routing_: `routing-nextroute`

## Usage

```bash
nextmv app push -a <app-id>
cat /path/to/routing/input.json | nextmv app run -a <app-id> -o 'instance=v171-5s'
```
