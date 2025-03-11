import time

import nextmv

before = time.time()
input = nextmv.load_local()
output = nextmv.Output(
    solution={"echo": input.data},
    statistics={"run": {"duration": time.time() - before}},
)
nextmv.write_local(output)
