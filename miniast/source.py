import ast
import itertools

from miniast.util import indent


class SourceVisitor(ast.NodeVisitor):
    """An AST visitor to show what our generated function looks like.
    """

    def visit(self, node):
        node_type = type(node)
        node_typename = node_type.__name__
        method = getattr(self, 'visit_{}'.format(node_typename), None)
        if method is None:
            raise TypeError(
                'Node of type {} has no visit method'.format(node_typename)
            )
        return method(node)

    def visit_Lambda(self, node):
        return 'lambda {}: {}'.format(
            ', '.join(map(self.visit, node.args.args)),
            self.visit(node.body)
        )

    def visit_ExceptHandler(self, node):
        type = node.type
        name = node.name
        body = indent('\n'.join(map(self.visit, node.body)))
        if type is None:
            assert name is None, 'type is None but got name'
            return 'except:\n{}'.format(body)

        spec = 'except {}'.format(self.visit(type))
        if name is not None:
            spec += ' as {}'.format(name)
        return '{}:\n{}'.format(spec, body)

    def visit_TryWithFinally(self, node):
        # TODO: can we remove the assemble method?
        return self.visit(node.assemble())

    visit_TryWithElse = visit_TryWithExcept = visit_TryWithFinally

    def visit_Try(self, node):
        lines = [
            'try:',
            indent('\n'.join(map(self.visit, node.body)))
        ] + list(map(self.visit, node.handlers))

        orelse = node.orelse  # else: clause
        if orelse:
            lines.append('else:')
            lines.append(indent('\n'.join(map(self.visit, orelse))))

        finalbody = node.finalbody  # finally: clause
        if finalbody:
            lines.append('finally:')
            lines.append(indent('\n'.join(map(self.visit, finalbody))))
        return '\n'.join(lines)

    def visit_List(self, node):
        return '[{}]'.format(', '.join(map(self.visit, node.elts)))

    def visit_Tuple(self, node):
        elements = node.elts
        length = len(elements)
        if length == 1:
            return '({},)'.format(self.visit(elements[0]))
        return '({})'.format(', '.join(map(self.visit, elements)))

    def visit_Dict(self, node):
        return '{{{}}}'.format(
            ', '.join(map('{}: {}'.format, node.keys, node.values))
        )

    def visit_Set(self, node):
        elements = node.elts
        if not elements:
            return 'set()'
        return '{{{}}}'.format(', '.join(map(self.visit, elements)))

    def visit_NoneType(self, node):
        return ''

    def visit_BinOp(self, node):
        return '{} {} {}'.format(
            self.visit(node.left), self.visit(node.op), self.visit(node.right)
        )

    def visit_Add(self, node):
        return '+'

    def visit_Sub(self, node):
        return '-'

    def visit_Mult(self, node):
        return '*'

    def visit_Div(self, node):
        return '/'

    def visit_FloorDiv(self, node):
        return '//'

    def visit_Pow(self, node):
        return '**'

    def visit_AugAssign(self, node):
        return '{} {}= {}'.format(
            self.visit(node.target),
            self.visit(node.op),
            self.visit(node.value)
        )

    def visit_If(self, node):
        test = self.visit(node.test)
        body = indent('\n'.join(map(self.visit, node.body)))
        if node.orelse:
            orelse = indent('\n'.join(map(self.visit, node.orelse)))
            return 'if {test}:\n{body}\nelse:\n{orelse}'.format(
                test=test,
                body=body,
                orelse=orelse
            )
        return 'if {test}:\n{body}'.format(test=test, body=body)

    def visit_IfExp(self, node):
        return '{body} if {test} else {orelse}'.format(
            body=self.visit(node.body),
            test=self.visit(node.test),
            orelse=self.visit(node.orelse),
        )

    def visit_Yield(self, node):
        return 'yield {}'.format(self.visit(node.value))

    def visit_YieldFrom(self, node):
        return 'yield from {}'.format(self.visit(node.value))

    def visit_And(self, node):
        return 'and'

    def visit_Or(self, node):
        return 'or'

    def visit_Lt(self, node):
        return '<'

    def visit_LtE(self, node):
        return '<='

    def visit_Gt(self, node):
        return '>'

    def visit_GtE(self, node):
        return '>='

    def visit_In(self, node):
        return 'in'

    def visit_NotIn(self, node):
        return 'not in'

    def visit_NotEq(self, node):
        return '!='

    def visit_Eq(self, node):
        return '=='

    def visit_Not(self, node):
        return 'not '

    def visit_Is(self, node):
        return 'is'

    def visit_IsNot(self, node):
        return 'is not'

    def visit_UnaryOp(self, node):
        return '{}{}'.format(self.visit(node.op), self.visit(node.operand))

    def visit_Compare(self, node):
        left = self.visit(node.left)
        return left + ' '.join(
            ' {} {}'.format(self.visit(op), self.visit(comparator))
            for op, comparator in zip(node.ops, node.comparators)
        )

    def visit_BoolOp(self, node):
        return '{} {} {}'.format(
            self.visit(node.left),
            self.visit(node.op),
            self.visit(node.right),
        )

    def visit_Return(self, node):
        return 'return {}'.format(self.visit(node.value))

    def visit_Attribute(self, node):
        return '{}.{}'.format(self.visit(node.value), node.attr)

    def visit_ImportFrom(self, node):
        imports = ', '.join(
            ' as '.join(filter(None, (alias.name, alias.asname)))
            for alias in node.names
        )
        return 'from {} import {}'.format(node.module, imports)

    def visit_Assign(self, node):
        return '{} = {}'.format(
            ', '.join(map(self.visit, node.targets)),
            self.visit(node.value)
        )

    def visit_SpecialArg(self, node):
        return node.arg

    def visit_Args(self, node):
        return '*{}'.format(node)

    def visit_Kwargs(self, node):
        return '**{}'.format(node.arg)

    def visit_FunctionDef(self, node):
        decorator_list = '\n'.join(map(self.visit, node.decorator_list))
        decorators = '@{}\n'.format(decorator_list) if decorator_list else ''
        xargs = node.args
        allargs = itertools.chain(
            xargs.args, filter(None, [xargs.vararg, xargs.kwarg]))
        args = ', '.join(map(self.visit, allargs))
        body = indent('\n'.join(map(self.visit, node.body)))
        return '\n{}def {}({}):\n{}'.format(decorators, node.name, args, body)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            func = self.visit(node.func)
            args = ',\n'.join(itertools.chain(
                map(self.visit, node.args),
                ('{}={!r}'.format(kw.arg, self.visit(kw.value))
                    for kw in node.keywords)
            ))
            indented_args = indent(args)
            template = ('(\n{}\n)' if args else '({})').format(indented_args)
            return '{}{}'.format(func, template)
        else:
            args = ', '.join(itertools.chain(
                map(self.visit, node.args),
                ('{}={!r}'.format(kw.arg, self.visit(kw.value))
                    for kw in node.keywords)
            ))
            return '{}({})'.format(self.visit(node.func), args)

    def visit_NameConstant(self, node):
        return node.value

    def visit_Expr(self, node):
        return self.visit(node.value)

    def visit_Name(self, node):
        return node.id

    def visit_Num(self, node):
        return str(node.n)

    def visit_Str(self, node):
        return repr(node.s)

    def visit_arg(self, node):
        return node.arg

    def visit_Pass(self, node):
        return 'pass'

    def visit_Raise(self, node):
        raise_string = 'raise {}'.format(self.visit(node.exc))
        cause = getattr(node, 'cause', None)

        if cause is not None:
            return '{} from {}'.format(raise_string, self.visit(cause))
        return raise_string

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        slice = self.visit(node.slice)
        return '{}[{}]'.format(value, slice)

    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Module(self, node):
        return '\n'.join(map(self.visit, node.body))

    def visit_ClassDef(self, node):

        bases = list(map(self.visit, node.bases))
        keywords = node.keywords
        buf = ['class {}'.format(node.name)]

        if bases:
            buf.append('({}'.format(', '.join(bases)))

        if keywords:
            kwargs = ', '.join(
                '{}={}'.format(k.arg, self.visit(k.value)) for k in keywords
            )
            buf.append(', {}'.format(kwargs))

        if bases or keywords:
            buf.append(')')

        body = indent('\n'.join(map(self.visit, node.body)))
        buf.append(':{}'.format(body))
        return ''.join(buf)

    def visit_While(self, node):
        body = indent('\n'.join(map(self.visit, node.body)))
        return 'while {}:\n{}'.format(self.visit(node.test), body)

    def visit_For(self, node):
        target = self.visit(node.target)
        iter = self.visit(node.iter)
        body = indent('\n'.join(map(self.visit, node.body)))
        return 'for {} in {}:\n{}'.format(target, iter, body)


def sourcify(mod):
    return SourceVisitor().visit(mod)
