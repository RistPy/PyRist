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
      ('DOCSTRING', r'"""'),
      ('DOCSTRING', r"'''"),
      ('STRING', r'((".*?")(?<!(\\)))'),
      ('STRING', r"(('.*?')(?<!(\\)))"),
      ('MACRO', r"^(\s)*\%\-(\s)*{NAME}(\s)*\-\%(\s)*$"),
      ('FROM', r'^(\s)*\+@(\s*)([.]?{ATTRIBUTED_NAME}|{NAME})(\s*)@\+(\s*)({ATTRIBUTED_NAME}|\*|\{)'),
      ('IMPORT', r'^(\s)*@\+(\s*){ATTRIBUTED_NAME}'),
      ('ERR_IMPORT', r'\+@ ({ATTRIBUTED_NAME}|{NAME}) @\+ ({ATTRIBUTED_NAME}|\*|\{)'),
      ('ERR_IMPORT', r'@\+ {ATTRIBUTED_NAME}'),
      ('FUNCDEF', r'(\$)?{NAME}\$\{'),
      ('PREDEFS', r'\$(ret|re|co|yi|pa|b|i|p|d|t|n|m|s|u|o|g|r|eval|ei|la|y|fi|ex|e|l|x|f|wh)'),
      ('AT', '@{ATTRIBUTED_NAME}'),
      ('ARROW', r'\}( )?\-\>( )?{ATTRIBUTED_NAME}?'),
      ('AWAIT', r'\?(\s+)?'),
      ('NUMBER', r'\d+\.\d+'),
      ('NUMBER', r'\d+'),
      ('ATTRIBUTED_NAME', r'{NAME}?([.]*(?=[a-zA-Z_])([a-zA-Z0-9_]*))+'),
      ('NAME', r'[a-zA-Z_][a-zA-Z0-9_]*'),
      ('TABSPACE', '\t'),
      ('SPACE', ' '),
      ('OPERATOR', r'[\+\*\-\/%]'),       # arithmetic operators
      ('OPERATOR', r'==|!=|\<|\>'),             # comparison operators
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

    __rules2: List[Tuple[str, str]] = [
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
      rules: List[Tuple[str, str]] = self.__rules2 if ds else self.__rules
  
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
      return re.compile('|'.join(self.__convert_rules())),re.compile('|'.join(self.__convert_rules(1)))
  
    def __interprete_line(self, line, line_num, f) -> Generator[_Token, None, None]:
      pos = 0
      tokens = []
  
      if line.endswith("//:Rist://NC"):
        tokens.append(_Token("lInE", line[:-12], line_num, 1))
      else:
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
  
            if name == "ERR_IMPORT":
              err = SyntaxError(f"Unexpected position of 'IMPORT' syntax, it should not come after any text")
              kwrds = dict(filename=f, lineno=line_num, offset=matches.start()+1, text=line)
              for k, v in kwrds.items():
                setattr(err, k, v)
              if sys.version_info>(3,9):setattr(err, "end_offset", pos+1+len(value))
              raise err
            if name == 'DOCSTRING':
              val={'"':2,"'":1}[value[0]]
              if self.under_docstring and self.under_docstring==val:
                self.under_docstring = 0
              elif not self.under_docstring:
                self.under_docstring=val
            tokens.append(_Token(name, value, line_num, matches.start() + 1))
          else:
            if not self.under_docstring:
              err = SyntaxError(f"Unexpected Character '{line[pos]}' in Identifier")
              kwrds = dict(filename=f, lineno=line_num, offset=pos+1, text=line)
              for k, v in kwrds.items():
                setattr(err, k, v)
              raise err
            else:
              pos += 1
              tokens.append(_Token("UNDER_DOCSTRING",line[pos-1],line_num, pos))

      for token in tokens:
        yield token
  
    @classmethod
    def interprete(cls, s, f) -> str:
      self = cls()
      tokens = []
      line_num = 0
      lines = s.splitlines()
      under = ""
      under_info = {}
      for line_num, line in enumerate(lines, 1):
        line = line.rstrip()
        if not line:
          tokens.append(_Token('NEWLINE', "\n", line_num, 1))
          continue
        line_tokens = list(self.__interprete_line(line, line_num, f))
        if line_tokens:
          tokens.extend(line_tokens)
          tokens.append(_Token('NEWLINE', "\n", line_num, len(line) + 1))

      if self.under_docstring:
        err = SyntaxError(f"EOF while scanning docstring literal")
        kwrds = dict(filename=f, lineno=len(lines), offset=len(lines[-1]), text=lines[-1])
        for k, v in kwrds.items():
          setattr(err, k, v)
        raise err
      
      ntoks = []
      i_n=[0,0]
      el = 0
      for tok in tokens:
        if tok.line!=i_n[0]:
          i_n = [tok.line, 0]
        if tok.name not in ("STRING", "DOCSTRING", "COMMENT"):
          for i in tok.value:
            i_n[-1]+=1
            if i not in "[{()}]":
              continue
            if i in ")}]":
              if (not under) or under[-1]!=i:
                err = SyntaxError(f"Unmatched '{i}'" if not under else f"Got '{i}', while expecting '{under[-1]}'")
                kwrds = dict(filename=f, lineno=tok.line, offset=i_n[-1], text=lines[tok.line-1])
                for k, v in kwrds.items(): setattr(err, k, v)
                raise err

              under = under[:-1]
              under_info = under_info["par"]
            if i in "[{(":
              under+={"[":"]","{":"}","(":")"}[i]
              under_info["par"] = {**under_info}
              under_info["line"] = tok.line
              under_info["offset"] = i_n[-1]
              
        tok.under=under
        l_n = tok.line + el
        if tok.name == "MACRO":
          indent, n = tok.value.split("%-")
          n = n.split("-%")[0].strip()
          assert n in macro_py, f"Snippet '{n}' not found!"
          v = indent + f"\n{indent}".join(macro_py[n])
          el+=len(v.splitlines())-1
          ntoks.append(_Token(f"MACRO_{n}", v, tok.line, 0))
        elif tok.name == "LCBRACK" and tok.value == "{":
          ntoks.append(_Token("LPAREN", "(", l_n, tok.coloumn))
        elif tok.name == "RCBRACK" and tok.value == "}":
          ntoks.append(_Token("RPAREN", ")", l_n, tok.coloumn))
        elif tok.name == "FUNCDEF":
          if tok.value.startswith("$"):val="async def "+tok.value[1:]
          else:val="def "+tok.value
          val=val.replace("${","(")
          ntoks.append(_Token("FUNCDEF", val, l_n, tok.coloumn))
        elif tok.name == "LPAREN" and tok.value == "(":
          ntoks.append(_Token("LCBRACK", "{", l_n, tok.coloumn))
        elif tok.name == "RPAREN" and tok.value == ")":
          ntoks.append(_Token("RCBRACK", "}", l_n, tok.coloumn))
        elif tok.name=="PREDEFS":
          r="__import__('ristpy').rist"
          e="(lambda code:__import__('ristpy').execute(code,[2])"
          x="(lambda a,b:((not (a and b)) and (a or b)))"
          extra={"o":"locals","g":"globals","r":r,"eval":e,"e":"else","ei":"elif","la":"lambda","x":x,"y":"try","fi":"finally","ex":"except"}
          ex2={"b":"break","f":"for","re":"__import__('re')","ret":"return","co":"continue","yi":"yield","pa":"pass"}
          ntoks.append(_Token("PREDEFS",
            {'i':"int",'p':"print",'d':"dict",'l':"list",'t':"type",'n':"input",'m':"__import__",'s':"str",'u':"tuple","wh":"while",**extra,**ex2}[tok.value[1:]],
            l_n,tok.coloumn
          ))
        elif tok.name == "ARROW":
          ntoks.append(_Token(tok.name, ")"+tok.value[1:], l_n, tok.coloumn))
        elif tok.name == "AWAIT":
          ntoks.append(_Token(tok.name, "await ", l_n, tok.coloumn))
        elif tok.name == "FROM":
          ntoks.append(_Token(tok.name, tok.value.replace("+@","from").replace("@+","import").replace("{","("), l_n, tok.coloumn))
        elif tok.name == "IMPORT":
          ntoks.append(_Token(tok.name, tok.value.replace("@+","import"), l_n, tok.coloumn))
        else:
          ntoks.append(tok)
          
        ntoks[-1].under = under

      if under:
        err = SyntaxError(f"Unexpected EOF")
        kwrds = dict(filename=f, lineno=under_info["line"], offset=under_info["offset"], text=lines[under_info["line"]-1])
        for k, v in kwrds.items():
          setattr(err, k, v)
        raise err
      code = "".join(list(str(t) for t in ntoks))
  
      return code
  
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

  code = __CompiledCode.setup(__Interpreter.interprete(code, fname),fname)

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
    return rist(code, fp=flags.FILE, flags=EXECUTE)

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
