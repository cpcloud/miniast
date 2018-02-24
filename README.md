`miniast`: Manipulate Python ASTs in Python
---

`miniast` is a Python library that provides APIs for generating Python ASTs
(abstract syntax trees).


Here's a regular Python class


```python
class Average:
    def __init__(self):
	self.value = 0.0
	self.count = 0

    def step(self, value):
	if self.value is not None:
	    self.value += value
	    self.count += 1

    def finalize(self):
	if self.count:
	    return self.value / self.count
```

Here's what it looks like if you were to define it programmatically using
`miniast`:

```python
from miniast import *

class_.Average[
    def_['__init__'](arg.self)[
	store.self.value.assign(0.0),
	store.self.count.assign(0),
    ],
    def_.step(arg.self, arg.value)[
	if_(load.self.value.is_not(NONE))[
	    store.self.value.iadd(value),
	    store.self.count.iadd(1),
	]
    ],
    def_.finalize(arg.self)[
	if_(load.self.count)[
	    return_(load.self.value / load.self.count)
	]
    ]
]
```

Pretty sweet right?

**Why should you care about this?**

Since the ASTs generated are just Python expressions, you're free to manipulate
them as you see fit.

This library arose while writing the
[`slumba`](https://github.com/cpcloud/slumba) library, to generate code that
numba would be able to type infer.
