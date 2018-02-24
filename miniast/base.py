"""
Constructing Python ASTs in Python is quite verbose, let's clean it up a bit.
"""

import ast
import collections
import copy
import functools


class StatementWithBody:
    def __getitem__(self, *body):
        return self(*to_list(*body))


def binary_operations(mapping, func):
    def decorator(cls):
        for method_name, op in mapping.items():
            setattr(cls, method_name, functools.partialmethod(func, op=op()))
        return cls
    return decorator


@binary_operations(
    {
        '__eq__': ast.Eq,
        '__ne__': ast.NotEq,
        '__lt__': ast.Lt,
        '__le__': ast.LtE,
        '__gt__': ast.Gt,
        '__ge__': ast.GtE,
        'is_': ast.Is,
        'is_not': ast.IsNot,
    },
    func=lambda self, other, op: ast.Compare(
        left=self, ops=[op], comparators=[to_node(other)]
    )
)
class Comparable:

    def __contains__(self, other):
        return ast.Compare(
            left=to_node(other), ops=[ast.In()], comparators=[self]
        )


@binary_operations(
    {
        '__add__': ast.Add,
        '__sub__': ast.Sub,
        '__mul__': ast.Mult,
        '__floordiv__': ast.FloorDiv,
        '__truediv__': ast.Div,
        '__div__': ast.Div,
        '__pow__': ast.Pow,
    },

    func=lambda self, other, op: ast.BinOp(
        left=self, op=op, right=to_node(other))
)
@binary_operations(
    {
        'iadd': ast.Add,
        'isub': ast.Sub,
        'imul': ast.Mult,
        'ifloordiv': ast.FloorDiv,
        'idiv': ast.Div,
        'ipow': ast.Pow,
    },
    func=lambda self, other, op: ast.AugAssign(
        target=self, op=op, value=to_node(other)
    )
)
class BinOp:
    pass


def s(value):
    return ast.Str(s=value)


class Assign(ast.Assign):
    def __init__(self, targets, value):
        super().__init__(targets=targets, value=value)


class Assignable:
    def assign(self, value):
        fields = {field: getattr(self, field) for field in self._fields}
        fields['ctx'] = ast.Store()
        return Assign(targets=[type(self)(**fields)], value=to_node(value))


class Indexable:
    def __getitem__(self, key):
        return sub(self, idx(key))


class Name(ast.Name, Comparable, BinOp, Assignable, Indexable):
    def __init__(self, id, ctx, lineno=0, col_offset=0):
        super().__init__(id=id, ctx=ctx, lineno=lineno, col_offset=col_offset)

    def __getattr__(self, name):
        return Attribute(
            value=self,
            attr=name,
            ctx=type(self.ctx)(),
            lineno=self.lineno,
            col_offset=self.col_offset)


class Load(Comparable):
    """
    API
    ---
    load.foo == ast.Name('foo', ctx=ast.Load())
    """
    __slots__ = ()

    def __getitem__(self, key):
        return Name(id=key, ctx=ast.Load())

    __getattr__ = __getitem__


load = Load()


class Raise:
    __slots__ = ()

    def __call__(self, exception, cause=None):
        return ast.Raise(exc=exception, cause=cause)


raise_ = Raise()


class Store:
    __slots__ = ()

    def __getitem__(self, key):
        return Name(id=key, ctx=ast.Store())

    __getattr__ = __getitem__


store = Store()


class Arg:
    __slots__ = ()

    def __getitem__(self, key):
        return ast.arg(arg=key, annotation=None)

    __getattr__ = __getitem__


arg = Arg()


def to_node(value):
    if isinstance(value, str):
        return ast.Str(s=value)
    elif isinstance(value, (int, float)):
        return ast.Num(n=value)
    assert value is None or isinstance(value, ast.AST), \
        f'value must be None or AST instance, got {type(value).__name__}'
    return value


def to_expr(value):
    return value if isinstance(value, ast.stmt) else ast.Expr(value=value)


class Call:
    """
    API
    ---
    call.func(load.foo, nopython=TRUE)
    """
    __slots__ = ()

    def __getitem__(self, key):
        return lambda *args, **kwargs: self(load[key], *args, **kwargs)

    __getattr__ = __getitem__

    def __call__(self, callable, *args, **kwargs):
        return ast.Call(
            func=callable,
            args=list(map(to_node, args)),
            keywords=[
                ast.keyword(arg=key, value=value)
                for key, value in kwargs.items()
            ]
        )


call = Call()


class Attribute(ast.Attribute, Assignable, Indexable, Comparable, BinOp):

    def __init__(self, value, attr, ctx, lineno=0, col_offset=0):
        super().__init__(
            value=value,
            attr=attr,
            ctx=ctx,
            lineno=lineno,
            col_offset=col_offset)

    def __getattr__(self, name):
        return type(self)(value=self, attr=name, ctx=type(self.ctx)())

    def __call__(self, *args, **kwargs):
        return call(self, *args, **kwargs)


class Else(StatementWithBody):
    __slots__ = 'ifstmt',

    def __init__(self, ifstmt):
        self.ifstmt = ifstmt

    def __call__(self, *orelse):
        ifstmt = self.ifstmt
        return type(ifstmt)(
            ifstmt.test, ifstmt.body, list(map(to_expr, to_list(orelse))))


class If(ast.If):
    def __init__(self, test, body, orelse=None):
        super().__init__(test=test, body=body, orelse=orelse or [])

    @property
    def else_(self):
        return Else(self)


class IfCond(StatementWithBody):
    __slots__ = 'test',

    def __init__(self, test):
        self.test = test

    def __call__(self, *body):
        return If(test=self.test, body=list(map(to_expr, to_list(body))))


class IfStatement:
    """
    if_(cond)(
    ).else_(
    )
    """
    __slots__ = ()

    def __call__(self, test):
        return IfCond(test)


if_ = IfStatement()


class For:
    """
    for_(target).in_(iter)(
    )
    """
    __slots__ = ()

    def __call__(self, target):
        return TargetedFor(target)


class IteratedFor(StatementWithBody):

    __slots__ = 'target', 'iter',

    def __init__(self, target, iter):
        self.target = target
        self.iter = iter

    def __call__(self, *body):
        return ast.For(target=self.target, iter=self.iter, body=to_list(body))


class TargetedFor:
    __slots__ = 'target',

    def __init__(self, target):
        self.target = target

    def in_(self, iter):
        return IteratedFor(self.target, iter)


for_ = For()


class WhileBody(StatementWithBody):

    __slots__ = 'test',

    def __init__(self, test):
        self.test = test

    def __call__(self, *body):
        return ast.While(test=self.test, body=to_list(body))


class While:
    __slots__ = ()

    def __call__(self, test):
        return WhileBody(test)


while_ = While()


class IfElse:
    __slots__ = ()

    def __call__(self, test, body, orelse):
        return ast.IfExp(test, body, orelse)


def ifelse(test, body, orelse):
    return ast.IfExp(test, body, orelse)


class FunctionDeclaration:

    def __getitem__(self, name):
        return FunctionDef(name=name)

    __getattr__ = __getitem__


def_ = FunctionDeclaration()


class FunctionSignature(StatementWithBody):

    __slots__ = 'name', 'arguments'

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def __call__(self, *body):
        return ast.FunctionDef(
            name=self.name,
            args=self.arguments,
            body=to_list(body),
            decorator_list=[],
            returns=None
        )


class FunctionDef:
    __slots__ = 'name',

    def __init__(self, name):
        self.name = name

    def __call__(self, *arguments):
        return FunctionSignature(
            self.name,
            ast.arguments(
                args=list(arguments),
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwargs=None,
                defaults=[],
            )
        )


def decorate(*functions):
    def wrapper(function_definition):
        func_def = copy.copy(function_definition)
        func_def.decorator_list = list(functions)
        return func_def
    return wrapper


def mod(*lines):
    module = ast.Module(body=list(lines))
    return module


class Index:
    __slots__ = ()

    def __call__(self, index):
        return ast.Index(value=to_node(index))


idx = Index()


class Subscript:
    __slots__ = ()

    def __call__(self, value, index):
        return ast.Subscript(
            value=value,
            slice=index,
            ctx=ast.Load(),
        )


sub = Subscript()


TRUE = ast.NameConstant(value=True)
FALSE = ast.NameConstant(value=False)
NONE = ast.NameConstant(value=None)


class Alias:
    """Shorter version of aliases used in `from foo import bar as baz`.

    API
    ---
    alias.foo == ast.alias(name=name, asname=None)
    """
    __slots__ = ()

    def __getattr__(self, name):
        return ast.alias(name=name, asname=None)

    def __getitem__(self, key):
        try:
            name, asname = key
        except ValueError:
            raise ValueError(
                'Only as imports are allowed with __getitem__, '
                'key length must be 2'
            )
        else:
            return ast.alias(name=name, asname=asname)


alias = Alias()


class ImportFrom:
    __slots__ = ()

    def __getattr__(self, name):
        return DottedModule(name)


import_from = ImportFrom()


class DottedModule:
    __slots__ = 'name',

    def __init__(self, name):
        self.name = name

    def __getitem__(self, key):
        names = [key] if isinstance(key, ast.alias) else list(key)
        return ast.ImportFrom(module=self.name, names=names, level=0)

    def __getattr__(self, name):
        return DottedModule('{}.{}'.format(self.name, name))


class Return:
    __slots__ = ()

    def __call__(self, value=None):
        return ast.Return(value=to_node(value))


return_ = Return()


def to_list(key):
    if isinstance(key, collections.Iterable) and not isinstance(key, str):
        return list(key)
    return [key]


class ClassConstructible:
    __slots__ = ()

    def __call__(self, *body):
        return ast.ClassDef(
            name=self.name,
            bases=list(self.bases),
            keywords=[
                ast.keyword(arg=arg, value=to_node(value))
                for arg, value in self.keywords.items()
            ],
            body=to_list(body),
            decorator_list=[]
        )


class ClassWithArguments(ClassConstructible):
    __slots__ = 'name', 'bases', 'keywords'

    def __init__(self, name, *bases, **keywords):
        self.name = name
        self.bases = bases
        self.keywords = keywords

    def __getitem__(self, body):
        return super().__call__(*to_list(body))


class ClassDefinition(ClassConstructible):
    __slots__ = 'name', 'bases', 'keywords'

    def __init__(self, name):
        self.name = name
        self.bases = []
        self.keywords = {}

    def __call__(self, *bases, **keywords):
        return ClassWithArguments(self.name, *bases, **keywords)

    def __getitem__(self, body):
        return super().__call__(*to_list(body))


class ClassDeclaration:
    __slots__ = ()

    def __getitem__(self, name):
        return ClassDefinition(name)

    __getattr__ = __getitem__


class_ = ClassDeclaration()


pass_ = ast.Pass()
