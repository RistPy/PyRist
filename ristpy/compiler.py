import ast
import asyncio
import inspect
import linecache

import import_expression

from .walkers import KeywordTransformer

CODE = """
def _compiler_func({{0}}):
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
