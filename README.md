# Nextpipe

<!-- markdownlint-disable MD033 MD013 -->

<p align="center">
  <a href="https://nextmv.io"><img src="https://cdn.prod.website-files.com/60dee0fad10d14c8ab66dd74/65c66addcd07eed09be35114_blog-banner-what-is-cicd-for-decision-science-p-2000.jpeg" alt="Nextmv" width="45%"></a>
</p>
<p align="center">
    <em>Nextmv: The home for all your optimization work</em>
</p>
<p align="center">
<a href="https://github.com/nextmv-io/nextpipe/actions/workflows/test.yml" target="_blank">
    <img src="https://github.com/nextmv-io/nextpipe/actions/workflows/test.yml/badge.svg?event=push&branch=develop" alt="Test">
</a>
<a href="https://github.com/nextmv-io/nextpipe/actions/workflows/lint.yml" target="_blank">
    <img src="https://github.com/nextmv-io/nextpipe/actions/workflows/lint.yml/badge.svg?event=push&branch=develop" alt="Lint">
</a>
<a href="https://pypi.org/project/nextpipe" target="_blank">
    <img src="https://img.shields.io/pypi/v/nextpipe?color=%2334D058&label=nextpipe" alt="Package version">
</a>
<a href="https://pypi.org/project/nextpipe" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/nextpipe.svg?color=%2334D058" alt="Supported Python versions">
</a>
</p>

<!-- markdownlint-enable MD033 MD013 -->

Nextpipe is a Python package that provides a framework for Decision Workflows
modeling and execution. It provides first-class support for Workflows in the
[Nextmv Platform][nextmv].

> [!IMPORTANT]  
> Please note that `nextpipe` is provided as _source-available_ software
> (not _open-source_). For further information, please refer to the
> [LICENSE](./LICENSE.md) file.

📖 To learn more about the `nextpipe`, visit the [docs][docs].

## Installation

The package is hosted on [PyPI][nextpipe-pypi]. Python `>=3.9` is required.

Install via `pip`:

```bash
pip install nextpipe
```

## Preview

Example of a pipeline utilizing multiple routing solvers, and picking the best
result.

```mermaid
graph LR
  fetch_data(prepare_data)
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

[nextpipe-pypi]: https://pypi.org/project/nextpipe/
[nextmv]: https://nextmv.io
[docs]: https://nextpipe.docs.nextmv.io/en/latest/
