import ast
import asyncio
import inspect
import linecache

import import_expression

from .scope import Scope
from .tools import Sender
from .walkers import KeywordTransformer

CODE = """
def _runner_func({{0}}):
    import asyncio
    from importlib import import_module as {0}
    import aiohttp
    import discord
    from discord.ext import commands

    try:
        pass
    finally:
        _executor.scope.globals.update(locals())
""".format(import_expression.constants.IMPORTER)

def wrap_code(code: str, args: str = '') -> ast.Module:
    user_code = import_expression.parse(code, mode='exec')
    mod = import_expression.parse(CODE.format(args), mode='exec')

    definition = mod.body[-1]
    assert isinstance(definition, ast.FunctionDef)

    try_block = definition.body[-1]
    assert isinstance(try_block, ast.Try)

    try_block.body.extend(user_code.body)

    ast.fix_missing_locations(mod)

    KeywordTransformer().generic_visit(try_block)

    last_expr = try_block.body[-1]

    if not isinstance(last_expr, ast.Expr):
        return mod

    if not isinstance(last_expr.value, ast.Yield):
        yield_stmt = ast.Yield(last_expr.value)
        ast.copy_location(yield_stmt, last_expr)
        yield_expr = ast.Expr(yield_stmt)
        ast.copy_location(yield_expr, last_expr)
        try_block.body[-1] = yield_expr

    return mod

class CodeExecutor:
    __slots__ = ('args', 'arg_names', 'code', 'loop', 'scope', 'source', 'fname')

    def __init__(self, code: str, fname: str = "<rist-executor>", scope: Scope = None, arg_dict: dict = None, loop: asyncio.BaseEventLoop = None):
        self.args = [self]
        self.arg_names = ['_executor']

        if arg_dict:
            for key, value in arg_dict.items():
                self.arg_names.append(key)
                self.args.append(value)

        self.source = code
        self.code = wrap_code(code, args=', '.join(self.arg_names))
        self.scope = scope or Scope()
        self.fname = fname
        self.loop = loop or asyncio.get_event_loop()

    def __iter__(self):
        exec(compile(self.code, self.fname, 'exec'), self.scope.globals, self.scope.locals)
        func_def = self.scope.locals.get('_runner_func') or self.scope.globals['_runner_func']

        return self.traverse(func_def)

    def traverse(self, func):
        try:
            if inspect.isgeneratorfunction(func):
                for send, result in Sender(func(*self.args)):
                    send((yield result))
            else:
                yield func(*self.args)
        except Exception:
            linecache.cache[self.fname] = (
                len(self.source),
                None,
                [line + '\n' for line in self.source.splitlines()],
                self.fname
            )
            raise
