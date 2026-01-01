import re
import ast
import enum
import random
import inspect
import secrets
import linecache

import import_expression as _iex

from collections import OrderedDict
from typing import Generator, Callable, Any
from .parsers import (
    IndentParser,
    Token,
    TokenList
)
from .walkers import *


__all__ = (
    "rist", "execute",
    "EXECUTE", "E",
    "COMPILE", "C",
    "WRITE", "W",
    "FILE", "F",
    "encrypt", "decrypt",
)

# Flags
class RistFlags(enum.IntFlag):
    EXECUTE = E = 1
    COMPILE = C = 2
    WRITE   = W = 4
    FILE    = F = 8

    def __repr__(self):
        if self._name_ is not None:
            return f'ristpy.{self._name_}'
        value = self._value_
        members = []
        negative = value < 0
        if negative:
            value = ~value
        for m in self.__class__:
            if value & m._value_:
                value &= ~m._value_
                members.append(f'ristpy.{m._name_}')
        if value:
            members.append(hex(value))
        res = '|'.join(members)
        if negative:
            if len(members) > 1:
                res = f'~({res})'
            else:
                res = f'~{res}'

        return res

    __str__ = object.__str__

C: RistFlags
E: RistFlags
W: RistFlags
F: RistFlags

globals().update(RistFlags.__members__)

def _parse_flags(flags: RistFlags) -> object:
    class _ParsedFlags(object):
        __slots__ = ("COMPILE", "WRITE", "EXECUTE", "FILE")

    old_flags = [flag for flag in RistFlags if flag in flags]

    attrs = {}
    to_adds = [attr for attr in _ParsedFlags.__slots__]
    for to_add in to_adds:
        attrs[to_add] = True if (eval(to_add) in old_flags) else False

    flags = _ParsedFlags()
    for attr in attrs.keys():
        setattr(flags, attr, attrs[attr])

    return flags

def rist(arg: str, fp: bool = True, flags: RistFlags = C, **kwargs) -> str:
    macros = kwargs.pop("macros", {})
    macro_py = kwargs.pop("macros_py", {})
    minify = kwargs.pop("minify", False)
    for n, snippet in macros.items():
        assert n not in macro_py, "Name of all the snippets should be unique"
        macro_py[n] = rist(snippet, False, C, file=f"<macro_{n}>", macro_py=macro_py).splitlines()
    flags = _parse_flags(flags)
    if fp:
        with open(arg, 'r') as f:
            code = f.read()
        fname = arg
    else:
        code = arg
        fname = kwargs.pop("file", "<unknown.rist>")

    class __Transpiler:
        __rules: list[tuple[str, str | tuple]] = [
            ('COMMENT', r'#.*$'),
            ('DOCSTRING', r'"""'),
            ('DOCSTRING', r"'''"),
            ('STRING', r'((".*?")(?<!(\\)))'),
            ('STRING', r"(('.*?')(?<!(\\)))"),
            ('MACRO',    r'(^{_})?{MOD}{MINUS}{_}{NAME}{_}{MINUS}{MOD}{_}$'),
            ('FROM',     r'(^{_})?{PLUS}{AT}{_}(({DOT}*({ATTRIBUTED_NAME}|{NAME}))|{DOT}){_}@{PLUS}{_}({NAME}|{ASTER}|{LPAREN})'),
            ('IMPORT',   r'(^{_})?{AT}{PLUS}{_}{DOT}*({ATTRIBUTED_NAME}|{NAME})'),
            ('DECOR',    r'(^{_})?{AT}{ATTRIBUTED_NAME}'),
            ('INDENT',   r'^({SPACE}|{TABSPACE})+'),
            ('FUNCDEF',  r'{DOLLAR}?{_}{NAME}{DOLLAR}{_}{LPAREN}'),
            ('INLINE_FUNC_START', r'({DOLLAR}{_})?{DOLLAR}{_}{LPAREN}'),
            ('INLINE_FUNC_END', r'{RPAREN}{_}{EQ}{GT}{_}{LCBRACK}'),

            ('RANGE', r'({RPAREN}|{NUMBER}){_}{DOT}{DOT}{_}({LPAREN}|{NUMBER})'),
            ('NUMBER', r'\d+{DOT}\d+j?'),                       ('NUMBER', r'(0(x|o|b))?\d+j?'),
            ('TERNARY', r'{RPAREN}{_}{QMARK}{_}'),         ('AWAIT', r'{QMARK}{_}'),

            ('ATTRIBUTED_NAME', r'{NAME}(\.{NAME})+'),
            ('ATTRIBUTE', r'({RPAREN}|{RBRACK}|{RCBRACK})(\.{NAME})+'),
            ('NAME', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('TABSPACE', '\t'),        ('SPACE', ' '),
            
            ('OPERATOR', r'{PLUS}|{MINUS}|{ASTER}|{DIV}|{MOD}|{DIV}{DIV}'),           # arithmetic operators
            ('OPERATOR', r'{EQ}{EQ}|{EX}{EQ}|{LT}|{GT}|{LT}{EQ}|{GT}{EQ}'),           # comparison operators
            ('OPERATOR', r'\|\||\||&&|&|{EX}'),                                       # boolean operators
            ('OPERATOR', r'(\||&|{PLUS}|{MINUS}|{ASTER}|{DIV}{DIV}?|{MOD}){EQ}'),     # augmentation operators

            ('COMMA',    r',' ),             ('ASSIGN',    r'{COLON}?{EQ}'),
            ('COLON',    r':' ),             ('SEMICOLON',   r';' ),
            ('LPAREN',   r'\('),             ('RPAREN',      r'\)'),
            ('LBRACK',   r'\['),             ('RBRACK',      r'\]'),
            ('LCBRACK',  r'\{'),             ('RCBRACK',     r'\}'),

            ('BACKSLASH', r'\\'),
            ("PYTHINGS",r"(\~|\^|{DOT}{DOT}{DOT})"),

            ('_',      (r'\s*',  0)),        ('QMARK',  (r'\?',   0)),
            ('AT',     (r'@',    0)),        ('EQ',     (r'=',    0)),
            ('EX',     (r'!',    0)),        ('GT',     (r'\>',   0)),
            ('LT',     (r'\<',   0)),        ('DIV',    (r'\/',   0)),
            ('DOT',    (r'\.',   0)),        ('MOD',    (r'%',    0)),
            ('PLUS',   (r'\+',   0)),        ('ASTER',  (r'\*',   0)),
            ('MINUS',  (r'-',    0)),        ('DOLLAR', (r'\$',   0)),
        ]

        __rules2: list[tuple[str, str | tuple]] = [
            ('DOCSTRING', r'"""'),
            ('DOCSTRING', r"'''"),
        ]

        def __init__(self) -> None:
            self.__regex,self.__regex2 = self.__compile_rules()
            self.under_docstring = 0

        @property
        def regex(self) -> re.Pattern:
            return self.__regex2 if self.under_docstring else self.__regex

        def __convert_rules(self,ds=False) -> Generator[str, None, None]:
            rules: list[tuple[str, str | tuple]] = self.__rules2 if ds else self.__rules

            grouped_rules = OrderedDict()
            to_rm = []
            for name, pattern in rules:
                grouped_rules.setdefault(name, [])
                if pattern[-1] == 0:
                    to_rm.append(name)
                    pattern = pattern[0]
                grouped_rules[name].append(pattern)

            for name, patterns in iter(grouped_rules.items()):
                ptrn = '|'.join(['({})'.format(p) for p in patterns])
                for pname, ptrns in iter(grouped_rules.items()):
                    while "{"+pname+"}" in ptrn:
                        ptrn = ptrn.replace("{"+pname+"}", '|'.join(['({ptrn})'.format(ptrn=p) for p in ptrns]))
                grouped_rules[name] = [ptrn]

            for name, patterns in iter(grouped_rules.items()):
                if name in to_rm: continue
                joined_patterns = '|'.join(['({ptrn})'.format(ptrn=p) for p in patterns])
                yield '(?P<{}>{})'.format(name, joined_patterns)

        def __compile_rules(self,):
            return re.compile('|'.join(self.__convert_rules())),re.compile('|'.join(self.__convert_rules(1)))

        def __tokenize_line(self, line, line_num, f) -> Generator[Token, None, None]:
            pos = 0
            tokens = []
            while pos < len(line):
                matches = self.regex.match(line, pos)
                if matches is not None:
                    name = matches.lastgroup
                    pos = matches.end(name)
                    value = matches.group(name)
                    if name == "TABSPACE":
                        value = "	"
                    elif name == "SPACE":
                        value = " "

                    if name == 'DOCSTRING':
                        val={'"':2,"'":1}[value[0]]
                        if self.under_docstring and self.under_docstring==val:
                            self.under_docstring = 0
                        elif not self.under_docstring:
                            self.under_docstring=val
                    tokens.append(Token(name, value, line_num, matches.start() + 1))
                else:
                    if not self.under_docstring:
                        err = SyntaxError(f"Unexpected Character '{line[pos]}' in Identifier")
                        kwrds = dict(filename=f, lineno=line_num, offset=pos+1, text=line)
                        for k, v in kwrds.items():
                            setattr(err, k, v)
                        raise err
                    else:
                        pos += 1
                        tokens.append(Token("UNDER_DOCSTRING",line[pos-1],line_num, pos))

            for token in tokens:
                yield token

        def build_inline_wrapper(self, id_, async_, params, body, name, INDENT):
            params = "".join(str(i) for i in params)
            body = "".join(str(i) for i in body)
            inner_def = f"""{'async ' if async_ else ''}def {name}({params}):\n{body.strip('\n')}"""
            return f"""
def {id_}_wrapper({id_}_g, {id_}_l):
{INDENT}{id_}_scope = {{}}
{INDENT}{id_}_scope.update({id_}_g)
{INDENT}{id_}_scope.update({id_}_l)
{INDENT}del {id_}_g,{id_}_l
{INDENT}exec({inner_def!r}, {id_}_scope)
{INDENT}{name} = {id_}_scope['{name}']

{INDENT}{name}.__name__ = '{'<rist:inline>' if name == id_ else name}'
{INDENT}{name}.__qualname__ = '{'<rist:inline>' if name == id_ else name}'
{INDENT}return {name}

{id_}_wrapper.__name__ = '<rist:inline-wrapper>'
{id_}_wrapper.__qualname__ = '<rist:inline-wrapper>'
"""

        @classmethod
        def transpile(cls, s: str, f: str) -> str:
            self = cls()
            tokens = TokenList()
            line_num = 0
            lines = s.splitlines()
            under = ""
            under_info = {}
            for line_num, line in enumerate(lines, 1):
                line = line.rstrip()
                if not line:
                    tokens.append(Token('NEWLINE', "\n", line_num, 1))
                    continue
                line_tokens = list(self.__tokenize_line(line, line_num, f))
                if line_tokens:
                    tokens.extend(line_tokens)
                    tokens.append(Token('NEWLINE', "\n", line_num, len(line) + 1))

            if self.under_docstring:
                err = SyntaxError(f"EOF while scanning docstring literal")
                kwrds = dict(filename=f, lineno=len(lines), offset=len(lines[-1]), text=lines[-1])
                for k, v in kwrds.items():
                    setattr(err, k, v)
                raise err
            
            ntoks = TokenList()
            i_n=[0,0]
            el = 0
            inline_stack = []
            scope = dict(
                filename = f,
                lines = lines,
                new_tokens = ntoks,
                transpiler = cls,
                inline_stack = inline_stack
            )
            INDENT = scope["INDENT"] = " " if minify else "    "
            IndentParser(scope)
            autoindent: list[int] = []
            ternary: list[tuple[int, int]] = []
            ternary_paren = 0
            listeners: dict[str, Callable[[], Any]] = {}
            for tok in tokens:
                scope["current_token"] = tok
                if tok.line!=i_n[0]: i_n = [tok.line, 0]
                if tok.name not in ("STRING", "DOCSTRING", "COMMENT"):
                    for i in tok.value:
                        i_n[-1]+=1
                        if i not in "[{()}]":
                            continue
                        elif i in ")}]":
                            if (not under) or under[-1]!=i:
                                err = SyntaxError(f"Unmatched '{i}'" if not under else f"Got '{i}', while expecting '{under[-1]}'")
                                kwrds = dict(filename=f, lineno=tok.line, offset=i_n[-1], text=lines[tok.line-1])
                                for k, v in kwrds.items(): setattr(err, k, v)
                                raise err

                            under = under[:-1]
                            under_info = under_info["par"]

                        elif i in "[{(":
                            under+={"[":"]","{":"}","(":")"}[i]
                            under_info["par"] = {**under_info}
                            under_info["line"] = tok.line
                            under_info["offset"] = i_n[-1]

                tok.under=under
                l_n = tok.line + el

                if tok.under in listeners: listeners.pop(tok.under)()
                if tok.name == "RCBRACK" and inline_stack and inline_stack[-1]["start_depth"] == 1 + len(tok.under):
                    inline = inline_stack.pop()
                    scope['indents'].pop()
                    r = ntoks.splice(
                        inline["header_index"] + 1,
                        len(ntoks) - 1,
                        Token("INLINE_CALL", f"({inline['id']}_wrapper(globals(), locals()))", *inline["data"])
                    )
                    stack = inline["stack"]
                    body = r[len(stack)+2:]
                    if stack[0].name == "FUNCDEF": stack.pop(0)
                    stack.pop(0)
                    ret = self.build_inline_wrapper(inline["id"], inline["asynchronous"], stack, body, inline["name"], INDENT)
                    ntoks.insert(0, Token("INLINE_DEF", ret, *inline["data"]))

                    for i in range(len(autoindent)):
                        autoindent[i] -= 1
                    if autoindent[-1] == 0: autoindent.pop()
                    continue
                

                if tok.name == "INLINE_FUNC_END":
                    stack = TokenList()
                    n = len(tok.under)
                    index = 0
                    for ntok in ntoks[::-1]:
                        index -= 1
                        if len(ntok.under) < n:
                            if ntok.name == 'FUNCDEF': stack.append(ntok)
                            break
                        stack.append(ntok)

                    if stack[-1].name == 'INDENT': stack.pop()
                    stack.reverse()
                    assert stack[0].name in "LPAREN FUNCDEF INLINE_FUNC_START"
                    asynchronous = False
                    name = id_ = f"_0x{secrets.token_hex(4)}"
                    v = stack[0].value
                    if stack[0].name == "FUNCDEF":
                        if "async" in v: asynchronous = True
                        name = v.split(" ")[-1]
                        index -= 1
                        for i in range(len(autoindent)): autoindent[i] -= 1
                    elif stack[0].name == "INLINE_FUNC_START":
                        if v.count("$") == 2:
                            asynchronous = True
                    else:
                        for i in range(len(autoindent)): autoindent[i] -= 1

                    inline = dict(
                        id = id_,
                        asynchronous = asynchronous,
                        start_depth = len(tok.under),
                        header_index = len(ntoks) + index,
                        name = name,
                        data = (tok.line, tok.column),
                        stack = stack
                    )
                    inline_stack.append(inline)
                    scope["indents"].append([scope['indents'][-1][-1]])
                    ntoks.append(Token("RPAREN",")",tok.line, tok.column))
                    tok = scope["current_token"] = Token("LCBRACK", "{", tok.line, tok.column)
                    tok.call = True

                indent: str = scope["parse_indent"]()
                if autoindent:
                    if tok.name == "SEMICOLON":
                        ntoks.append(Token("NEWLINE", "\n", tok.line, tok.column))
                        ntoks.append(Token("INDENT", indent+(INDENT*len(autoindent)), tok.line, tok.column))

                        continue
                    elif (tok.name in "LPAREN LBRACK LCBRACK") or (tok.name in "FROM FUNCDEF" and "(" in tok.value):
                        for i in range(len(autoindent)):
                            autoindent[i] += 1
                    elif (tok.name in "RPAREN RBRACK RCBRACK"):
                        for i in range(len(autoindent)):
                            autoindent[i] -= 1
                        if tok.name == "RCBRACK" and autoindent[-1] == 0:
                            autoindent.pop()
                            ntoks.append(Token("NEWLINE", "\n", tok.line, tok.column))
                            ntoks.append(Token("INDENT", indent+(INDENT*len(autoindent)), tok.line, tok.column))
                            continue


                if tok.name in "TABSPACE" and ntoks[-1].name == "INDENT":
                    continue
                elif tok.name == "RANGE":
                    if tok.value[0] == ")":
                        comp = len(tok.under)
                        if tok.value[-1] != "(": comp += 1
                        index = len(ntoks) + 1
                        for ntok in ntoks[::-1]:
                            index -= 1
                            if (not ntok.under) or len(ntok.under) < comp: break

                        ntoks.insert(index, Token("RANGE_KW","(range(", tok.line, tok.column))
                    else:
                        ntoks.append(Token("RANGE_KW", "(range(", tok.line, tok.column, tok.under))
                    ntoks.append(Token("RANGE_ITEMS", tok.value.replace("..", ","), tok.line, tok.column, tok.under))

                    if tok.value[-1] == "(":
                        listeners[tok.under[:-1]] = lambda: ntoks.append(Token("RANGE_END", "))", tok.line, tok.column))
                    else:
                        ntoks.append(Token("RANGE_END", "))", tok.line, tok.column))

                elif tok.name == "MACRO":
                    n = tok.value.split("%-")[1].split("-%")[0].strip()
                    assert n in macro_py, f"Snippet '{n}' not found!"
                    v = indent + f"\n{indent}".join(macro_py[n])
                    el+=len(v.splitlines())-1
                    ntoks.append(Token(f"MACRO_{n}", v, tok.line, 0))
                elif tok.name == "TERNARY":
                    index = len(ntoks) + 1
                    comp = len(tok.under)
                    for ntok in ntoks[::-1]:
                        index -= 1
                        if (not ntok.under) or len(ntok.under) == comp: break

                    ntoks.append(Token("RPAREN", ")", tok.line, tok.column))
                    ternary.append((index, len(ntoks), tok.under))
                    for i in range(len(autoindent)): autoindent[i] -= 1

                elif tok.name == "COLON" and ternary and tok.under == ternary[-1][-1]:
                    index, start, _ = ternary.pop()

                    new = [Token("TERNARY_ELSE"," else ", tok.line, tok.column)]
                    rem = ntoks.splice(start, len(ntoks), *new)
                    if ternary_paren:
                        rem.append(Token("RPAREN", ")", tok.line, tok.column))
                        ternary_paren -= 1
                    if ternary:
                        rem.insert(0, Token("LPAREN", "(", tok.line, tok.column))
                        ternary_paren += 1
                    for ntok in rem:
                        ntoks.insert(index, ntok)
                        index += 1
                    
                    ntoks.insert(index, Token("TERNARY_IF", " if ", tok.line, tok.column))
                elif tok.name == "FUNCDEF":
                    tok.value=tok.value.replace(" ", "").replace("\t","")
                    if tok.value.startswith("$"):val="async def "+tok.value[1:]
                    else:val="def "+tok.value
                    ntoks.append(Token("FUNCDEF", val[:-2], l_n, tok.column))
                    ntoks.append(Token("LPAREN", "(", l_n, tok.column))
                elif tok.name == "FROM":
                    ntoks.append(Token(tok.name, "from "+tok.value.replace("+@","").replace("@+"," import ").strip(), l_n, tok.column))
                elif tok.name == "IMPORT":
                    ntoks.append(Token(tok.name, "import "+tok.value.replace("@+","").strip(), l_n, tok.column))
                elif tok.name == "AWAIT":
                    ntoks.append(Token("AWAIT", "await ", tok.line, tok.column))
                elif tok.name == "LCBRACK":
                    if not ntoks.is_last_real(*"INDENT ASSIGN NEWLINE LPAREN LBRACK LCBRACK COLON".split()):
                        autoindent.append(1)
                        ntoks.append(Token("COLON", ":", tok.line, tok.column))
                        ntoks.append(Token("NEWLINE", "\n", tok.line, tok.column))
                        tok = Token("INDENT", indent+(INDENT*len(autoindent)), tok.line, tok.column)

                    ntoks.append(tok)
                elif tok.name == "OPERATOR" and tok.value in "&& ||".split(" "):
                    tok.value = {
                        "&&": " and ",
                        "||": " or "
                    }[tok.value]
                    ntoks.append(tok)
                else:
                    ntoks.append(tok)

                ntoks[-1].under = under

            if under:
                err = SyntaxError(f"Unexpected EOF")
                kwrds = dict(filename=f, lineno=under_info["line"], offset=under_info["offset"], text=lines[under_info["line"]-1])
                for k, v in kwrds.items():
                    setattr(err, k, v)
                raise err
            elif ternary:
                err = SyntaxError("Incomplete ternary")
                kwrds = dict(
                    filename=f,
                    lineno=ntoks[ternary[-1][0]].line,
                    offset=ntoks[ternary[-1][0]].column,
                    text=lines[ntoks[ternary[-1][0]].line-1],
                    end_lineno=ntoks[ternary[-1][0]].line,
                    end_offset = ntoks[ternary[-1][1]].column
                )
                for k, v in kwrds.items():
                    setattr(err, k, v)
                raise err

            return ntoks.detokenize()

    class __TranspiledCode(str):
        @classmethod
        def setup(cls, code: str, fname: str = '<unknown>') -> None:
            self=cls(code)
            self.__code = code
            self.file = fname
            return self

        def __re__(self) -> str:
            return str(self)

        def __str__(self) -> str:
            return self.__code

        @property
        def code(self) -> str:
            return self.__code

    code = __TranspiledCode.setup(__Transpiler.transpile(code, fname),fname)

    if flags.WRITE and not "compile_to" in kwargs:
        raise ValueError('"compile_to" key-word argument not given when "WRITE" flag passed')

    if flags.WRITE:
        with open(kwargs["compile_to"], "w") as f:
            f.write(code.code)

    if flags.EXECUTE:
        return execute(code)

    return code

def execute(code: str, flags: RistFlags = E, **kwargs) -> None:
    flags = _parse_flags(flags)

    if flags.WRITE and flags.COMPILE:
        return rist(code, fp=flags.FILE, flags=E|W, **kwargs)
    if flags.COMPILE:
        return rist(code, fp=flags.FILE, flags=E)

    if (not getattr(code, "__module__", False)) or (code.__module__!="ristpy"):
        raise TypeError("The code must be compiled from ristpy module not any other")

    class _Scope:
        __slots__ = ('globals', 'locals')

        def __init__(self, globals_: dict = None, locals_: dict = None):
            self.globals: dict = globals_ or {}
            self.locals: dict = locals_ or {}

        def clear_intersection(self, other_dict):
            for key, value in other_dict.items():
                if key in self.globals and self.globals[key] is value:
                    del self.globals[key]
                if key in self.locals and self.locals[key] is value:
                    del self.locals[key]
            return self

        def update(self, other):
            self.globals.update(other.globals)
            self.locals.update(other.locals)
            return self

        def update_globals(self, other: dict):
            self.globals.update(other)
            return self

        def update_locals(self, other: dict):
            self.locals.update(other)
            return self

    __CODE = """
# indent: 4 spaces
def _runner_func({{0}}):
        import asyncio, aiohttp
        from importlib import import_module as {0}

        try:
                pass
        finally:
                _executor.scope.globals.update(locals())
    """.format(_iex.constants.MARKER)

    def _wrap_code(code: str, args: str = '', f=None) -> ast.Module:
        user_code = _iex.parse(code, f, mode='exec')
        mod = _iex.parse(__CODE.format(args), f, mode='exec')
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

    class Sender:
        __slots__ = ('iterator', 'send_value')
        def __init__(self, iterator):
            self.iterator = iterator
            self.send_value = None

        def __iter__(self):
            return self.__internal(self.iterator.__iter__())

        def __internal(self, base):
            try:
                while True:
                    value = base.send(self.send_value)
                    self.send_value = None
                    yield self.set_send_value, value
            except StopIteration:
                pass

        def set_send_value(self, value):
            self.send_value = value

    class _CodeExecutor:
        __slots__ = ('args', 'arg_names', 'code', 'loop', 'scope', 'source', 'fname')

        def __init__(self, code: str, fname: str = "<unknown.rist>", scope: _Scope = None, arg_dict: dict = None):
            self.args = [self]
            self.arg_names = ['_executor']
            self.fname = fname or "<unknown.rist>"

            if arg_dict:
                for key, value in arg_dict.items():
                    self.arg_names.append(key)
                    self.args.append(value)

            self.source = code
            self.code = _wrap_code(code, args=', '.join(self.arg_names), f=self.fname)
            self.scope = scope or _Scope()

        def __iter__(self):
            exec(compile(self.code, self.fname, 'exec'), self.scope.globals, self.scope.locals)
            func_def = self.scope.locals.get('_runner_func') or self.scope.globals['_runner_func']
            return self.__traverse(func_def)

        def __traverse(self, func):
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

    for send, result in Sender(_CodeExecutor(str(code), arg_dict={}, fname=code.file)):
        if result is None:
            continue
        send(result)

def encrypt(code: str, key: int=None, *, depth: int=1) -> list[str, int] | str:
    depth-=1
    if depth<0 or depth>7:
        raise ValueError("Depth should neither be less than 1, nor more than 8")

    is_key = bool(key)
    key=key or random.randint(1,100)
    assert isinstance(key,int)
    res = []
    for letter in code:
        res.append((ord(letter)*key)+key)

    res=" ".join([str(i) for i in res])
    if depth != 0: res = encrypt(res, key, depth=depth)
    if not is_key: res = [res, key]
    return res

def decrypt(enc: str, key: int, *, depth: int = 1):
    c=[]
    for i in enc.split(" "):
        try:
            c.append(int(i))
        except: c.append(i)

    d=depth-1
    if d<0 or d>7:
        raise ValueError("Depth should neither be less than 1, nor more than 8")

    res=[]
    for i in c:
        if isinstance(i,int): res.append(chr(int((i-key)/key)))

    res = "".join([str(i) for i in res])
    if d!=0: res = decrypt(res,key,depth=d)
    return res
