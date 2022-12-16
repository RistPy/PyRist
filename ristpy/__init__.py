import re
import ast
import sys
import enum
import random
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

globals().update(RistFlags.__members__)

class _ParsedFlags(object):
  __slots__ = ("COMPILE", "WRITE", "EXECUTE", "FILE")

def _parse_flags(flags: RistFlags) -> _ParsedFlags:
  old_flags = [flag for flag in RistFlags if flag in flags]

  attrs = {}
  to_adds = [attr for attr in _ParsedFlags.__slots__]
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

class __CompiledCode(str):
  @classmethod
  def setup(cls, code: str, fname: str = '<unknown>') -> None:
    self=cls(code)
    self.__code = code
    self.file = fname
    return self

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

  def __init__(self, code: str, fname: str = "<unknown.rist>", scope: _Scope = None, arg_dict: dict = None, loop: asyncio.BaseEventLoop = None):
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
  __rules: List[Tuple[str, str]] = [
    ('COMMENT', r'#.*'),
    ('STRING', r'((".*?")(?<!(\\)))'),
    ('STRING', r"(('.*?')(?<!(\\)))"),
    ('FROM', r'^(\s)*\+@(\s*)({ATTRIBUTED_NAME}|{NAME})(\s*)@\+(\s*){ATTRIBUTED_NAME}'),
    ('IMPORT', r'^(\s)*@\+(\s*){ATTRIBUTED_NAME}'),
    ('ERR_IMPORT', r'\+@ ({ATTRIBUTED_NAME}|{NAME}) @\+ {ATTRIBUTED_NAME}'),
    ('ERR_IMPORT', r'@\+ {ATTRIBUTED_NAME}'),
    ('FUNCDEF', r'(\$)?{NAME}\$\{'),
    ('PREDEFS', r'\$(i|p|d|t|n|m|s|u|o|g|r|eval|ei|la|y|fi|ex|e|l|x)'),
    ('AT', '@{ATTRIBUTED_NAME}'),
    ('ARROW', r'\}( )?\-\>( )?{ATTRIBUTED_NAME}?'),
    ('GTORLT', r'__(\<|\>)'),
    ('AWAIT', r'\?(\s+)?'),
    ('LARROW', r'\<'),
    ('RARROW', r'\>'),
    ('NUMBER', r'\d+\.\d+'),
    ('NUMBER', r'\d+'),
    ('ATTRIBUTED_NAME', r'{NAME}?([.]*(?=[a-zA-Z_])([a-zA-Z0-9_]*))+'),
    ('NAME', r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('TABSPACE', '\t'),
    ('SPACE', ' '),
    ('OPERATOR', r'[\+\*\-\/%]'),       # arithmetic operators
    ('OPERATOR', r'==|!='),             # comparison operators
    ('OPERATOR', r'\|\||\||&|&&'),      # boolean operators
    ('OPERATOR', r'\.\.\.|\.\.'),       # range operators
    ('OPERATOR', r'!'),
    ('ASSIGN', '='),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('LBRACK', r'\['),
    ('RBRACK', r'\]'),
    ('LCBRACK', '{'),
    ('RCBRACK', '}'),
    ('COLON', r'\:'),
    ('SEMICOLON', r'\;'),
    ('COMMA', ','),
    ("PYTHINGS",r"(\\|\~|\^)"),
  ]

  def __init__(self) -> None:
    self.__regex = self.__compile_rules()

  def __convert_rules(self) -> Generator[str, None, None]:
    rules: List[Tuple[str, str]] = self.__rules

    grouped_rules = OrderedDict()
    for name, pattern in rules:
      grouped_rules.setdefault(name, [])
      grouped_rules[name].append(pattern)

    for name, patterns in iter(grouped_rules.items()):
      ptrn = '|'.join(['({})'.format(p) for p in patterns])
      for pname, ptrns in iter(grouped_rules.items()):
        while "{"+pname+"}" in ptrn:
          ptrn = ptrn.replace("{"+pname+"}", '|'.join(['({ptrn})'.format(ptrn=p) for p in ptrns]))
      grouped_rules[name] = [ptrn]

    for name, patterns in iter(grouped_rules.items()):
      joined_patterns = '|'.join(['({ptrn})'.format(ptrn=p) for p in patterns])
      yield '(?P<{}>{})'.format(name, joined_patterns)

  def __compile_rules(self,):
    return re.compile('|'.join(self.__convert_rules()))

  def __interprete_line(self, line, line_num, f) -> Generator[_Token, None, None]:
    pos = 0
    tokens = []

    if line.endswith("//:Rist://NC"):
      tokens.append(_Token("lInE", line[:-12], line_num, 1))
    else:
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

          if name == "ERR_IMPORT":
            err = SyntaxError(f"Unexpected position of 'IMPORT' syntax, it should not come after any text")
            kwrds = dict(filename=f, lineno=line_num, offset=matches.start()+1, text=line)
            for k, v in kwrds.items():
              setattr(err, k, v)
            if sys.version_info>(3,9):setattr(err, end_offset, pos+1+len(value))
            raise err

          tokens.append(_Token(name, value, line_num, matches.start() + 1))
        else:
          err = SyntaxError(f"Unexpected Character '{line[pos]}' in Identifier")
          kwrds = dict(filename=f, lineno=line_num, offset=pos+1, text=line)
          for k, v in kwrds.items():
            setattr(err, k, v)

          raise err

    for token in tokens:
      yield token

  @classmethod
  def interprete(cls, s, f) -> str:
    self = cls()
    tokens = []
    line_num = 0
    for line_num, line in enumerate(s.splitlines(), 1):
      line = line.rstrip()
      if not line:
        tokens.append(_Token('NEWLINE', "\n", line_num, 1))
        continue
      line_tokens = list(self.__interprete_line(line, line_num, f))
      if line_tokens:
        tokens.extend(line_tokens)
        tokens.append(_Token('NEWLINE', "\n", line_num, len(line) + 1))

    ntoks = []
    for tok in tokens:
      if tok.name == "LCBRACK" and tok.value == "{":
        ntoks.append(_Token("LPAREN", "(", tok.line, tok.coloumn))
      elif tok.name == "RCBRACK" and tok.value == "}":
        ntoks.append(_Token("RPAREN", ")", tok.line, tok.coloumn))
      elif tok.name == "FUNCDEF":
        if tok.value.startswith("$"):val="async def "+tok.value[1:]
        else:val="def "+tok.value
        val=val.replace("${","(")
        ntoks.append(_Token("FUNCDEF", val, tok.line, tok.coloumn))
      elif (tok.name == "LPAREN" and tok.value == "(") or (tok.name == "LARROW" and tok.value == "<"):
        ntoks.append(_Token("LCBRACK", "{", tok.line, tok.coloumn))
      elif (tok.name == "RPAREN" and tok.value == ")") or (tok.name == "RARROW" and tok.value == ">"):
        ntoks.append(_Token("RCBRACK", "}", tok.line, tok.coloumn))
      elif tok.name=="PREDEFS":
        r="__import__('ristpy').rist"
        e="(lambda code:__import__('ristpy').execute(code,[2])"
        x="(lambda a,b:((not (a and b)) and (a or b)))"
        extra={"o":"locals","g":"globals","r":r,"eval":e,"e":"else","ei":"elif","la":"lambda","x":x,"y":"try","fi":"finally","ex":"except"}
        ntoks.append(_Token("PREDEFS",
          {'i':"int",'p':"print",'d':"dict",'l':"list",'t':"type",'n':"input",'m':"__import__",'s':"str",'u':"tuple",**extra}[tok.value[1:]],
          tok.line,tok.coloumn
        ))
      elif tok.name == "ARROW":
        ntoks.append(_Token(tok.name, ")"+tok.value[1:], tok.line, tok.coloumn))
      elif tok.name == "AWAIT":
        ntoks.append(_Token(tok.name, "await ", tok.line, tok.coloumn))
      elif tok.name == "FROM":
        ntoks.append(_Token(tok.name, tok.value.replace("+@","from").replace("@+","import"), tok.line, tok.coloumn))
      elif tok.name == "IMPORT":
        ntoks.append(_Token(tok.name, tok.value.replace("@+","import"), tok.line, tok.coloumn))
      elif tok.name == "GTORLT" and tok.value.startswith('__'):
        ntoks.append(_Token(tok.name, tok.value[-1], tok.line, tok.coloumn))
      else:
        ntoks.append(tok)

    code = "".join(list(str(t) for t in ntoks))

    return code


def rist(arg: str, fp: bool = True, flags: RistFlags = C, **kwargs) -> __CompiledCode:
  flags = _parse_flags(flags)
  if fp:
    with open(arg, 'r') as f:
      code = f.read()
    fname = arg
  else:
    code = arg
    fname = '<unknown.rist>'
  code = __CompiledCode.setup(__Interpreter.interprete(code, fname),fname)

  if flags.WRITE and not "compile_to" in kwargs:
    raise ValueError('"compile_to" key-word argument not given when "WRITE" flag passed')

  if flags.WRITE:
    with open(kwargs["compile_to"], "w") as f:
      f.write(code.code)

  if flags.EXECUTE:
    return execute(code)

  return code

def execute(code: Union[str, __CompiledCode], flags: RistFlags = E, **kwargs) -> None:
  flags = _parse_flags(flags)

  if flags.WRITE and flags.COMPILE:
    return rist(code, fp=flags.FILE, flags=E|W, **kwargs)
  if flags.COMPILE:
    return rist(code, fp=flags.FILE, flags=EXECUTE)

  if not isinstance(code, __CompiledCode):
    raise TypeError("The code must be compiled from ristpy module not any other")
  for send, result in Sender(_CodeExecutor(str(code), arg_dict=get_builtins(), fname=code.file)):
    if result is None:
      continue
    send(result)

def encrypt(code: str, key: int=None, *, depth: int=1):
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
