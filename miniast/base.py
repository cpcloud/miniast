"""Lightweight macros for Python.
"""

import ast
import collections
import copy
import functools


class StatementWithBody:
    """Implement the square bracket syntax for Class, Def, If, While, Try, and
    For statements.
    """
    __slots__ = ()

    def __getitem__(self, *body):
        return self(*to_list(*body))


SWAPPED_ARGUMENT_METHODS = {
    '__radd__',
    '__rmul__',
}


def binary_operations(mapping, func):
    """Decorator providing default implementations of binary operations.

    Parameters
    ----------
    mapping : collections.Mapping
    func : callable

    Returns
    -------
    decorator : callable
    """
    def decorator(cls):
        for method_name, op in mapping.items():
            if method_name in SWAPPED_ARGUMENT_METHODS:
                f = functools.partialmethod(
                    lambda self, other, op: func(to_node(other), self, op),
                    op=op()
                )
            else:
                f = functools.partialmethod(func, op=op())
            setattr(cls, method_name, f)
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
    """Mixin to implement comparison operators.
    """
    __slots__ = ()

    def __contains__(self, other):
        return ast.Compare(
            left=to_node(other), ops=[ast.In()], comparators=[self]
        )


@binary_operations(
    {
        '__add__': ast.Add,
        '__radd__': ast.Add,
        '__sub__': ast.Sub,
        '__mul__': ast.Mult,
        '__rmul__': ast.Mult,
        '__floordiv__': ast.FloorDiv,
        '__truediv__': ast.Div,
        '__div__': ast.Div,
        '__pow__': ast.Pow,
        '__lshift__': ast.LShift,
        '__rshift__': ast.RShift,
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
        'ilshift': ast.LShift,
        'irshift': ast.RShift,
    },
    func=lambda self, other, op: ast.AugAssign(
        target=self, op=op, value=to_node(other)
    )
)
class BinOp:
    """Mixin to implement non-comparison binary operators.
    """


class Callable:
    """Mixin to generate Call nodes.
    """
    def __call__(self, *args, **kwargs):
        return ast.Call(
            func=self,
            args=list(map(to_node, args)),
            keywords=[
                ast.keyword(arg=key, value=value)
                for key, value in kwargs.items()
            ]
        )


def s(value):
    """Convenience function to generate an ast.Str node.

    Parameters
    ----------
    value : str

    Returns
    -------
    node : ast.Str
    """
    return ast.Str(s=value)


class Assignable:
    """Mixin to generate Assign nodes.
    """
    def store(self, value):
        fields = {field: getattr(self, field) for field in self._fields}
        fields['ctx'] = ast.Store()
        return ast.Assign(targets=[type(self)(**fields)], value=to_node(value))


class Indexable:
    """Mixin to generate Subscript nodes.
    """
    def __getitem__(self, key):
        return Subscript(
            value=self,
            slice=ast.Index(value=to_node(key)),
            ctx=ast.Load()
        )


class Attributable:
    """Mixin to generate Attribute nodes.
    """
    def __getattr__(self, name):
        return Attribute(value=self, attr=name, ctx=ast.Load())


class Name(
    ast.Name,
    Comparable,
    BinOp,
    Assignable,
    Indexable,
    Callable,
    Attributable
):
    """Represent a Python variable
    """
    def __init__(self, id, ctx, lineno=0, col_offset=0):
        super().__init__(id=id, ctx=ctx, lineno=lineno, col_offset=col_offset)


class Tuple(ast.Tuple, Comparable, BinOp, Assignable, Indexable):
    """Represent a Python tuple.
    """
    def __init__(self, elts, ctx, lineno=0, col_offset=0):
        super().__init__(
            elts=elts, ctx=ctx, lineno=lineno, col_offset=col_offset)


class Var:
    """Generate variable names.
    """
    __slots__ = ()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            targets = [
                var[target] if isinstance(target, str) else to_node(target)
                for target in key
            ]
            return Tuple(elts=targets, ctx=ast.Load())
        return Name(id=key, ctx=ast.Load())

    __getattr__ = __getitem__


var = Var()


class Raise:
    __slots__ = ()

    def __call__(self, exception, cause=None):
        return ast.Raise(exc=exception, cause=cause)


raise_ = Raise()


class SpecialArg(ast.arg):
    """Turns out you can spoof *args by defining ``__iter__``, and **kwargs by
    defining a ``keys()`` method + ``__getitem__``.

    One wrinkle is that the ``__iter__`` implementation needs to yield a
    ``str`` subclass
    """
    def __init__(self, arg, annotation=None):
        super().__init__(arg=arg, annotation=annotation)

    def __hash__(self):
        return hash((type(self), self.arg, self.annotation))

    def __eq__(self, other):
        return self.arg == other.arg and self.annotation == other.annotation

    def __ne__(self, other):
        return not (self == other)

    def keys(self):
        return collections.KeysView(self)

    def __iter__(self):
        yield Args(self.arg)

    def __getitem__(self, key):
        if isinstance(key, Args):
            return Kwargs(key)
        raise TypeError(
            '__getitem__ not defined for class {}'.format(type(self).__name__)
        )


class Args(str):
    pass


class Kwargs(SpecialArg):
    pass


class Arg:
    __slots__ = ()

    def __getitem__(self, key):
        return SpecialArg(arg=key)

    __getattr__ = __getitem__


arg = Arg()


def to_node(value):
    if isinstance(value, str):
        return ast.Str(s=value)
    elif isinstance(value, (int, float)):
        return ast.Num(n=value)
    elif isinstance(value, list):
        return ast.List(elts=list(map(to_node, value)), ctx=ast.Load())
    elif isinstance(value, tuple):
        return ast.Tuple(elts=list(map(to_node, value)), ctx=ast.Load())
    elif isinstance(value, dict):
        keys = list(map(to_node, value.keys()))
        values = list(map(to_node, value.values()))
        return ast.Dict(keys=keys, values=values)
    elif isinstance(value, set):
        return ast.Set(elts=list(map(to_node, value)))
    assert value is None or isinstance(value, ast.AST), \
        'value must be None or AST instance, got {}'.format(
            type(value).__name__
        )
    return value


def to_expr(value):
    return value if isinstance(value, ast.stmt) else ast.Expr(value=value)


class Attribute(
    ast.Attribute,
    Assignable,
    Indexable,
    Comparable,
    BinOp,
    Callable,
    Attributable
):

    def __init__(self, value, attr, ctx, lineno=0, col_offset=0):
        super().__init__(
            value=value,
            attr=attr,
            ctx=ctx,
            lineno=lineno,
            col_offset=col_offset)


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

    __slots__ = 'target', 'iter'

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


def ifelse(test, body, orelse):
    return ast.IfExp(test, body, orelse)


class FunctionDeclaration:

    def __getitem__(self, name):
        return FunctionDef(name=name)

    __getattribute__ = __getitem__


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

    def __call__(self, *arguments, **kwargs):
        varargs = [a for a in arguments if isinstance(a, Args)]
        kwargs = list(kwargs.values())
        arguments = [a for a in arguments if not isinstance(a, (Args, dict))]
        return FunctionSignature(
            self.name,
            ast.arguments(
                args=list(arguments),
                vararg=varargs[0] if varargs else None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=kwargs[0] if kwargs else None,
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
    module = ast.fix_missing_locations(module)
    return module


class Subscript(
    ast.Subscript,
    Comparable,
    BinOp,
    Assignable,
    Indexable,
    Callable,
    Attributable
):
    def __init__(self, value, slice, ctx, lineno=0, col_offset=0):
        super().__init__(
            value=value,
            slice=slice,
            ctx=ctx,
            lineno=lineno,
            col_offset=col_offset,
        )


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

    def __getattribute__(self, name):
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

    def __getitem__(self, key):
        return DottedModule(key)

    __getattr__ = __getitem__


class DottedModule:
    __slots__ = 'name',

    def __init__(self, name):
        self.name = name

    def import_(self, *aliases, **kwargs):
        names = [*aliases]
        names += [
            ast.alias(name=a.name, asname=asname)
            for asname, a in kwargs.items()
        ]
        return ast.ImportFrom(module=self.name, names=names, level=0)

    def __getattr__(self, name):
        return DottedModule('{}.{}'.format(self.name, name))


class Import:
    __slots__ = ()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            names = [alias[k] for k in key]
        else:
            names = [alias[key]]
        return ast.Import(names=names)

    __getattr__ = __getitem__


from_ = ImportFrom()
import_ = Import()


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


class LambdaWithSignature:
    __slots__ = 'signature',

    def __init__(self, *signature):
        self.signature = list(signature)

    def __getitem__(self, expr):
        return ast.Lambda(args=ast.arguments(args=self.signature), body=expr)


class Lambda:
    __slots__ = ()

    def __call__(self, *signature):
        return LambdaWithSignature(*signature)


lambda_ = Lambda()


def yield_(value):
    return ast.Yield(value=value)


def yield_from(value):
    return ast.YieldFrom(value=value)


class Except:
    def except_(self, *type, as_=None):
        if len(type) == 1:
            type, = type
        return TryWithExceptSetup(self, type, name=as_)


class Finally:
    @property
    def finally_(self):
        return TryWithFinallySetup(self)


class TrySuiteSetup:
    def assemble(self):
        return self.parent.assemble()


class TryWithFinally(ast.stmt):
    def __init__(self, parent, *body):
        self.parent = parent
        self.body = list(body)

    def assemble(self):
        try_ = self.parent.assemble()
        try_.finalbody = self.body
        return try_


class TryWithFinallySetup(StatementWithBody, TrySuiteSetup):
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, *body):
        return TryWithFinally(self, *body)


class TryWithElse(ast.stmt, Finally):
    def __init__(self, parent, *body):
        self.parent = parent
        self.body = list(body)

    def assemble(self):
        try_ = self.parent.assemble()
        try_.orelse = self.body
        return try_


class TryWithElseSetup(StatementWithBody, TrySuiteSetup):
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, *body):
        return TryWithElse(self, *body)


class TryWithExcept(ast.stmt, Except, Finally):
    def __init__(self, parent, *body):
        self.parent = parent
        self.body = list(body)

    @property
    def else_(self):
        return TryWithElseSetup(self)

    def assemble(self):
        try_ = self.parent.assemble()
        handler = ast.ExceptHandler(
            type=self.parent.type, name=self.parent.name, body=self.body)
        try_.handlers.append(handler)
        return try_


class TryWithExceptSetup(StatementWithBody, TrySuiteSetup):
    def __init__(self, parent, typ, name):
        self.parent = parent
        self.type = to_node(typ)
        self.name = name

    def __call__(self, *body):
        return TryWithExcept(self, *body)


class Try(ast.stmt, Except, Finally):
    def __init__(self, *body):
        self.body = list(body)

    def assemble(self):
        return ast.Try(body=self.body, handlers=[], orelse=[], finalbody=[])


class TrySetup(StatementWithBody):
    def __call__(self, *body):
        return Try(*body)


try_ = TrySetup()
