`miniast`: Manipulate Python ASTs in Python
---

`miniast` is a Python library that provides APIs for generating Python ASTs
(abstract syntax trees).

The `ast` module that ships with the standard library is wonderful until you
need to generate more than a few nodes.


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
    def_.__init__(arg.self)[
	var.self.value.store(0.0),
	var.self.count.store(0),
    ],
    def_.step(arg.self, arg.value)[
	if_(var.self.value.is_not(NONE))[
	    var.self.value.iadd(var.value),
	    var.self.count.iadd(1),
	]
    ],
    def_.finalize(arg.self)[
	if_(var.self.count)[
	    return_(var.self.value / var.self.count)
	]
    ]
]
```

Pretty sweet right?

Here's what it would look like if you wrote it using raw `ast` nodes:

```python
ClassDef(
  name='Average',
  bases=[],
  keywords=[],
  body=[
    FunctionDef(
      name='__init__',
      args=arguments(
        args=[arg(
          arg='self',
          annotation=None)],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[]),
      body=[
        Assign(
          targets=[Attribute(
            value=Name(
              id='self',
              ctx=Load()),
            attr='value',
            ctx=Store())],
          value=Num(n=0.0)),
        Assign(
          targets=[Attribute(
            value=Name(
              id='self',
              ctx=Load()),
            attr='count',
            ctx=Store())],
          value=Num(n=0))],
      decorator_list=[],
      returns=None),
    FunctionDef(
      name='step',
      args=arguments(
        args=[
          arg(
            arg='self',
            annotation=None),
          arg(
            arg='value',
            annotation=None)],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[]),
      body=[If(
        test=Compare(
          left=Attribute(
            value=Name(
              id='self',
              ctx=Load()),
            attr='value',
            ctx=Load()),
          ops=[IsNot()],
          comparators=[NameConstant(value=None)]),
        body=[
          AugAssign(
            target=Attribute(
              value=Name(
                id='self',
                ctx=Load()),
              attr='value',
              ctx=Load()),
            op=Add(),
            value=Name(
              id='value',
              ctx=Load())),
          AugAssign(
            target=Attribute(
              value=Name(
                id='self',
                ctx=Load()),
              attr='count',
              ctx=Load()),
            op=Add(),
            value=Num(n=1))],
        orelse=[])],
      decorator_list=[],
      returns=None),
    FunctionDef(
      name='finalize',
      args=arguments(
        args=[arg(
          arg='self',
          annotation=None)],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[]),
      body=[If(
        test=Attribute(
          value=Name(
            id='self',
            ctx=Load()),
          attr='count',
          ctx=Load()),
        body=[Return(value=BinOp(
          left=Attribute(
            value=Name(
              id='self',
              ctx=Load()),
            attr='value',
            ctx=Load()),
          op=Div(),
          right=Attribute(
            value=Name(
              id='self',
              ctx=Load()),
            attr='count',
            ctx=Load())))],
        orelse=[])],
      decorator_list=[],
      returns=None)],
  decorator_list=[])
```

That is truly horrifying.

**Why should you care about this?**

Since the ASTs generated are just Python expressions, you're free to manipulate
them as you see fit.

This library arose while writing the
[`slumba`](https://github.com/cpcloud/slumba) library, to generate code that
numba would be able to type infer.
