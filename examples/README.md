# Examples

This directory contains examples of how to use `nextpipe`.

## Prerequisites

- Create and push all necessary apps in your account (check the README of the example and look for `@app` in the pipeline definition).
  - Some simple apps are available in the `./apps` directory. Push them as described in their READMEs.
  - Some examples make use of marketplace apps. Follow instructions in the example READMEs to subscribe to them.
    - Alternative, you can use the `nextmv community clone -a <app-id>` command to clone the app from the community apps repository.

## Table of contents

- [pipeline-chain](./pipeline-chain): Example of a simple pipeline with a chain of steps.
- [pipeline-foreach](./pipeline-foreach): Example of a pipeline with a fanout step (`@foreach`) that runs the same input through a solve step with different app options.
- [pipeline-complex](./pipeline-complex): A more complex pipeline combining some concepts and multiple solvers.
- [pipeline-ensemble](./pipeline-ensemble): Example of a pipeline ensembling the results of multiple solvers.
- [pipeline-preprocess](./pipeline-preprocess): Example of a pipeline doing some preprocessing before running a solver.
