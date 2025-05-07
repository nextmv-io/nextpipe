import sys
import time

import nextmv

before = time.time()
input = nextmv.load()
output = nextmv.Output(
    solution={
        "echo": {
            "data": input.data,
            "args": sys.argv[1:],
        },
    },
    statistics={"run": {"duration": time.time() - before}},
)
nextmv.write(output)
