import ast

import pytest

from miniast import (
    alias,
    arg,
    Attribute,
    call,
    class_,
    def_,
    FALSE,
    for_,
    idx,
    if_,
    from_,
    mod,
    Name,
    NONE,
    pass_,
    return_,
    sub,
    TRUE,
    var,
    while_,
)

from miniast import sourcify


def eq(a, b):
    """Test equality of AST nodes, because Python doesn't define __eq__ for
    them :(
    """
    if isinstance(a, (ast.Load, ast.Store)):
        return isinstance(b, type(a))
    if isinstance(a, list):
        return isinstance(b, list) and all(map(eq, a, b))
    return a == b or (
        isinstance(a, type(b)) and
        isinstance(b, type(a)) and
        hasattr(a, '_fields') and
        hasattr(b, '_fields') and
        a._fields == b._fields and
        all(eq(getattr(a, field), getattr(b, field)) for field in a._fields)
    )


def test_eq():
    assert not eq(1, 0)
    assert eq('a', 'a')

    assert not eq('a', 1)

    assert not eq(
        ast.Name(id='x', ctx=ast.Load()),
        ast.Name(id='x', ctx=ast.Store())
    )
    assert eq(
        ast.Name(id='x', ctx=ast.Load()),
        ast.Name(id='x', ctx=ast.Load())
    )


def test_load():
    assert eq(var.foo, ast.Name(id='foo', ctx=ast.Load()))
    assert eq(var['bar'], ast.Name(id='bar', ctx=ast.Load()))


def test_assign():
    assert eq(
        var.foo.store(0),
        ast.Assign(
            targets=[ast.Name(id='foo', ctx=ast.Store())],
            value=ast.Num(n=0)
        )
    )


def test_arg():
    assert eq(arg.fizzbuzz, ast.arg(arg='fizzbuzz', annotation=None))


def test_call():
    assert eq(
        call.func(),
        ast.Call(
            func=ast.Name(id='func', ctx=ast.Load()), args=[], keywords=[]
        )
    )
    assert eq(
        call.func(var.a, b=var.b),
        ast.Call(
            func=ast.Name(id='func', ctx=ast.Load()),
            args=[ast.Name(id='a', ctx=ast.Load())],
            keywords=[
                ast.keyword(arg='b', value=ast.Name(id='b', ctx=ast.Load()))
            ]
        )
    )


def test_attr():
    assert eq(
        var.foo.get_a_thing,
        Attribute(
            value=Name(id='foo', ctx=ast.Load()),
            attr='get_a_thing',
            ctx=ast.Load(),
        )
    )


@pytest.mark.parametrize('i', range(5))
def test_idx(i):
    assert eq(idx(i), ast.Index(value=ast.Num(n=i)))


@pytest.mark.parametrize('i', range(5))
def test_sub(i):
    assert eq(
        sub(var.a, idx(i)),
        ast.Subscript(
            value=ast.Name(id='a', ctx=ast.Load()),
            slice=ast.Index(value=ast.Num(n=i)),
            ctx=ast.Load()
        )
    )


def test_alias():
    assert eq(
        alias.foo,
        ast.alias(name='foo', asname=None)
    )
    assert eq(
        alias['foo', 'bar'],
        ast.alias(name='foo', asname='bar')
    )


def test_import_from():
    assert eq(
        from_.bar.import_(alias.foo, baz=alias.foo),
        ast.ImportFrom(
            module='bar',
            names=[
                ast.alias(name='foo', asname=None),
                ast.alias(name='foo', asname='baz')
            ],
            level=0
        )
    )


def test_constants():
    assert eq(NONE, ast.NameConstant(value=None))
    assert eq(TRUE, ast.NameConstant(value=True))
    assert eq(FALSE, ast.NameConstant(value=False))


def test_classdef():

    myklass = class_.Yuge(var.object, metaclass=var.object)[
        def_.method1(arg.self, arg.a)[
            if_(var.a == 1)[return_(var.a + 1)].else_[return_(1)]
        ]
    ]
    s = sourcify(myklass)
    assert s == """\
class Yuge(object, metaclass=object):
    def method1(self, a):
        if a == 1:
            return a + 1
        else:
            return 1"""


def test_while():
    loop = while_(var.x < var.y)[
        pass_
    ]
    assert sourcify(loop) == """\
while x < y:
    pass"""
    assert loop is not None


def test_for():
    loop = for_(var.x).in_(var.y)[
        call.print(1)
    ]
    assert sourcify(loop) == """\
for x in y:
    print(1)"""
    assert loop is not None


def test_complex_class():
    klass = class_.Average[
        def_.__init__(arg.self)[
            var.self.value.store(0.0),
            var.self.count.store(0),
        ],
        def_.step(arg.self, arg.value)[
            if_(var.value.is_not(NONE))[
                var.self.value.iadd(var.value),
                var.self.count.iadd(1)
            ]
        ],
        def_.finalize(arg.self)[
            if_(var.self.count)[
                return_(var.self.value / var.self.count)
            ]
        ]
    ]
    assert sourcify(klass) == """\
class Average:
    def __init__(self):
        self.value = 0.0
        self.count = 0

    def step(self, value):
        if value is not None:
            self.value += value
            self.count += 1

    def finalize(self):
        if self.count:
            return self.value / self.count"""


def test_exec_class():
    klass = class_.Average[
        def_.__init__(arg.self)[
            var.self.value.store(0.0)
        ]
    ]
    exec(compile(mod(klass), __file__, 'exec'))
    assert 'Average' in locals()


def test_store_compile():
    expr = mod(var.self.x.store(0))
    assert sourcify(expr) == 'self.x = 0'
    assert ast.dump(expr) == ast.dump(ast.parse('self.x = 0'))
