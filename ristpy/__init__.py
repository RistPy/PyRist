import re
import ast
import enum
import typing
import asyncio
import inspect
import secrets
import linecache

import import_expression as _iex

from collections import OrderedDict
from typing import Union, List, Generator, Tuple

from .walkers import *
from .builtins import *


__all__ = (
  "rist", "execute",
  "EXECUTE", "E",
  "COMPILE", "C",
  "WRITE", "W"
)

# Flags
class RistFlags(enum.IntFlag):
    EXECUTE = E = 1
    COMPILE = C = 2
    WRITE = W = 4
    
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

globals().update(RistFlags.__members__)

class _ParsedFlags(object):
  __slots__ = ("COMPILE", "WRITE", "EXECUTE")

def _parse_flags(flags: RistFlags) -> _ParsedFlags:
  old_flags = [flag for flag in RistFlags if flag in flags]

  while E in old_flags:
    old_flags[old_flags.index(E)] = EXECUTE
  while C in old_flags:
    old_flags[old_flags.index(C)] = COMPILE
  while W in old_flags:
    old_flags[old_flags.index(W)] = WRITE

  attrs = {}
  to_adds = ["WRITE", "COMPILE", "EXECUTE"]
  for to_add in to_adds:
    attrs[to_add] = True if (eval(to_add) in old_flags) else False

  flags = _ParsedFlags()
  for attr in attrs.keys():
    setattr(flags, attr, attrs[attr])

  return flags

# Scope/Environment
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

def get_parent_scope_from_var(name, global_ok=False, skip_frames=0) -> typing.Optional[_Scope]:
  stack = inspect.stack()
  try:
    for frame_info in stack[skip_frames + 1:]:
      frame = None
      try:
        frame = frame_info.frame
        if name in frame.f_locals or (global_ok and name in frame.f_globals):
          return _Scope(globals_=frame.f_globals, locals_=frame.f_locals)
      finally:
        del frame
  finally:
        del stack
  return None

def get_parent_var(name, global_ok=False, default=None, skip_frames=0):
  scope = get_parent_scope_from_var(name, global_ok=global_ok, skip_frames=skip_frames + 1)
  if not scope:
    return default
  if name in scope.locals:
    return scope.locals.get(name, default)
  return scope.globals.get(name, default)

__CODE = """
def _runner_func({{0}}):
    import asyncio, aiohttp
    from importlib import import_module as {0}

    try:
        pass
    finally:
        _executor.scope.globals.update(locals())
""".format(_iex.constants.IMPORTER)

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

class __CompiledCode:
  def __init__(self, code: str, fname: str = '<unknown>') -> None:
    self.__code = code
    self.file = fname

  def __repr__(self) -> str:
    return str(self)

  def __str__(self) -> str:
    return self.__code

  @property
  def code(self) -> str:
    return self.__code

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

    def __init__(self, code: str, fname: str = "<unknown>", scope: _Scope = None, arg_dict: dict = None, loop: asyncio.BaseEventLoop = None):
        self.args = [self]
        self.arg_names = ['_executor']
        self.fname = fname or "<unknown>"

        if arg_dict:
            for key, value in arg_dict.items():
                self.arg_names.append(key)
                self.args.append(value)

        self.source = code
        self.code = _wrap_code(code, args=', '.join(self.arg_names), f=self.fname)
        self.scope = scope or _Scope()
        self.loop = loop or asyncio.get_event_loop()

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

class _Token:
  def __init__(
    self,
    name: str,
    value: Union[str, int],
    line: int,
    coloumn: int
  ) -> None:
    self.name = name
    self.value = str(value)
    self.line = line
    self.coloumn = coloumn

  def __repr__(self) -> str:
    return "<Token name='{0.name}' value='{0.value}' line={0.line} coloumn={0.coloumn}>".format(
      self
    )

  def __str__(self) -> str:
    return str(self.value)

class __Interpreter:
  __rules = [
        ('COMMENT', r'//.*'),
        ('STRING', r'"(\\"|[^\n?"])*"'),
        ('STRING', r"'(\\'|[^\n?'])*'"),
        ('FROM', r'\+@ '),
        ('IMPORT', r'@\+ '),
        ('AT', '@'),
        ('LARROW', r'\<'),
        ('RARROW', r'\>'),
        ('NUMBER', r'\d+\.\d+'),
        ('NUMBER', r'\d+'),
        ('ARROW', r'\} \=\-\=\> '),
        ('FUNCDEF', 'define'),
        ('NAME', r'[a-zA-Z_]\w*|[a-zA-Z0-9_]\w*'),
        ('TABSPACE', '\t'),
        ('SPACE', ' '),
        ('OPERATOR', r'[\+\*\-\/%]'),       # arithmetic operators
        ('OPERATOR', r'<=|>=|==|!=|<|>'),   # comparison operators
        ('OPERATOR', r'\|\||&&'),           # boolean operators
        ('OPERATOR', r'\.\.\.|\.\.'),       # range operators
        ('OPERATOR', r'!'),
        ('ASSIGN', '='),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACK', r'\['),
        ('RBRACK', r'\]'),
        ('LCBRACK', '{'),
        ('RCBRACK', '}'),
        ('DOT', r'\:\:'),
        ('COLON', r'\:'),
        ('SEMICOLON', r'\;'),
        ('COMMA', ','),
  ]

  def __init__(self) -> None:
    self.__regex = self.__compile_rules(self.__rules)

  def __convert_rules(self, rules: List[Tuple[str, str]]) -> Generator[str, None, None]:
        grouped_rules = OrderedDict()
        for name, pattern in rules:
            grouped_rules.setdefault(name, [])
            grouped_rules[name].append(pattern)

        for name, patterns in iter(grouped_rules.items()):
            joined_patterns = '|'.join(['({})'.format(p) for p in patterns])
            yield '(?P<{}>{})'.format(name, joined_patterns)

  def __compile_rules(self, rules):
    return re.compile('|'.join(self.__convert_rules(rules)))

  def __interprete_line(self, line, line_num) -> Generator[_Token, None, None]:
    pos = 0
    while pos < len(line):
      matches = self.__regex.match(line, pos)
      if matches is not None:
        name = matches.lastgroup
        pos = matches.end(name)
        value = matches.group(name)
        if name == "TABSPACE":
          value = "	"
        elif name == "SPACE":
          value = " "
        yield _Token(name, value, line_num, matches.start() + 1)
      else:
        raise SyntaxError(f"{line}\n{' '*(pos-1)}^\nUnexpected Character '{line[pos-1]}' in Identifier")

  @classmethod
  def interprete(cls, s,) -> str:
    self = cls()
    tokens = []
    line_num = 0
    for line_num, line in enumerate(s.splitlines(), 1):
      line = line.rstrip()
      if not line:
        tokens.append(_Token('NEWLINE', "\n", line_num, 1))
        continue
      line_tokens = list(self.__interprete_line(line, line_num))
      if line_tokens:
        tokens.extend(line_tokens)
        tokens.append(_Token('NEWLINE', "\n", line_num, len(line) + 1))

    ntoks = []
    for tok in tokens:
      if tok.name == "LCBRACK" and tok.value == "{":
        ntoks.append(_Token("LPAREN", "(", tok.line, tok.coloumn))
      elif tok.name == "RCBRACK" and tok.value == "}":
        ntoks.append(_Token("RPAREN", ")", tok.line, tok.coloumn))
      elif tok.name == "COMMENT" and tok.value.startswith('//'):
        ntoks.append(_Token("COMMENT", ("#" + tok.value[2:]), tok.line, tok.coloumn))
      elif tok.name == "FUNCDEF" and tok.value == "define":
        ntoks.append(_Token("FUNCDEF", "def", tok.line, tok.coloumn))
      elif (tok.name == "LPAREN" and tok.value == "(") or (tok.name == "LARROW" and tok.value == "<"):
        ntoks.append(_Token("LCBRACK", "{", tok.line, tok.coloumn))
      elif (tok.name == "RPAREN" and tok.value == ")") or (tok.name == "RARROW" and tok.value == ">"):
        ntoks.append(_Token("RCBRACK", "}", tok.line, tok.coloumn))
      elif tok.name == "ARROW" and tok.value == "} =-=> ":
        ntoks.append(_Token(tok.name, ") -> ", tok.line, tok.coloumn))
      elif tok.name == "FROM" and tok.value == "+@ ":
        ntoks.append(_Token(tok.name, "from ", tok.line, tok.coloumn))
      elif tok.name == "IMPORT" and tok.value == "@+ ":
        ntoks.append(_Token(tok.name, "import ", tok.line, tok.coloumn))
      elif tok.name == "DOT" and tok.value == "::":
        ntoks.append(_Token(tok.name, ".", tok.line, tok.coloumn))
      else:
        ntoks.append(tok)

    return "".join(list(str(t) for t in ntoks))


def rist(arg: str, fp: bool = True) -> __CompiledCode:
  if fp:
    with open(arg, 'r') as f:
      code = f.read()
    fname = arg
  else:
    code = arg
    fname = '<unknown>'
  lines = code.splitlines()
  nlines = []
  for index, line in enumerate(lines):
    _line = line.rstrip("\n")
    while _line.startswith(" "):
      _line = _line.lstrip(" ")
    while _line.startswith("	"):
      _line = _line.lstrip("	")
    if not _line:
      nlines.append(line)
      continue
    if not line.endswith(";"):
      raise SyntaxError(f"At line {index+1}, Line shoud must end with ';' not '{line[-1]}'")
    nlines.append(line.rstrip(";"))
  code = "\n".join(list(line for line in nlines))
  return __CompiledCode(__Interpreter.interprete(code), fname)

def execute(code: __CompiledCode) -> None:
  if not isinstance(code, __CompiledCode):
    raise TypeError("The code must be compiled from ristpy module not any other")
  for send, result in Sender(_CodeExecutor(str(code), arg_dict=get_builtins(), fname=code.file)):
    if result is None:
      continue
    send(result)
