import re
import secrets

from collections import OrderedDict
from typing import Union, List, Generator, Tuple

from .tools import *
from .scope import *
from .walkers import *
from .executor import *
from .builtins import *

__all__ = ("rist", "execute")

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

class __Token:
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
        ('STRING', r'"(\\"|[^"])*"'),
        ('STRING', r"'(\\'|[^'])*'"),
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
        ('OPERATOR', '!'),                  # unary operator
        ('ASSIGN', '='),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACK', r'\['),
        ('RBRACK', r'\]'),
        ('LCBRACK', '{'),
        ('RCBRACK', '}'),
        ('COLON', ':'),
        ('COMMA', ','),
        ('DOT', '.'),
        ('FROM', r'\+@'),
        ('IMPORT', r'@\+'),
        ('LARROW', r'\<'),
        ('RARROW', r'\>')
  ]

  def __init__(self) -> None:
    self.__regex = self.__compile_rules(self.__rules)

  def __convert_rules(self, rules: List[Tuple[str, str]]) -> Generator[str]:
        grouped_rules = OrderedDict()
        for name, pattern in rules:
            grouped_rules.setdefault(name, [])
            grouped_rules[name].append(pattern)

        for name, patterns in iter(grouped_rules.items()):
            joined_patterns = '|'.join(['({})'.format(p) for p in patterns])
            yield '(?P<{}>{})'.format(name, joined_patterns)

  def __compile_rules(self, rules):
    return re.compile('|'.join(self.__convert_rules(rules)))

  def __interprete_line(self, line, line_num) -> Generator[__Token]:
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
         yield __Token(name, value, line_num, matches.start() + 1)

  def interprete(self, s) -> str:
    tokens = []
    line_num = 0
    for line_num, line in enumerate(s.splitlines(), 1):
      line = line.rstrip()
      if not line:
        tokens.append(Token('NEWLINE', "\n", line_num, 1)
        continue
      line_tokens = list(self._tokenize_line(line, line_num))
      if line_tokens:
        tokens.extend(line_tokens)
        tokens.append(Token('NEWLINE', "\n", line_num, len(line) + 1))

    ntoks = []
    for tok in tokens:
      if tok.name == "LCBRACK" and tok.value == "{":
        ntoks.append(__Token("LPAREN", "(", tok.line, tok.coloumn))
      elif tok.name == "RCBRACK" and tok.value == "}":
        ntoks.append(__Token("RPAREN", ")", tok.line, tok.coloumn))
      elif tok.name == "COMMENT" and tok.value.startswith('//'):
        ntoks.append(__Token("COMMENT", ("#" + tok.value[2:]), tok.line, tok.coloumn))
      elif tok.name == "FUNCDEF" and tok.value == "define":
        ntoks.append(__Token("FUNCDEF", "def", tok.line, tok.coloumn))
      elif (tok.name == "LPAREN" and tok.value == "(") or (tok.name == "LARROW" and tok.value == "<"):
        ntoks.append(__Token("LCBRACK", "{", tok.line, tok.coloumn))
      elif (tok.name == "RPAREN" and tok.value == ")") or (tok.name == "RARROW" and tok.value == ">"):
        ntoks.append(__Token("RCBRACK", "}", tok.line, tok.colomn))
      elif tok.name == "ARROW" and tok.value == "} =-=> ":
        ntoks.append(__Token(tok.name, ") -> ", tok.line, tok.coloumn))
      elif tok.name == "FROM" and tok.value == "+@":
        ntoks.append(__Token(tok.name, "from", tok.line, tok.coloumn))
      elif tok.name == "IMPORT" and tok.value == "@+"
        ntoks.append(__Token(tok.name, "import", tok.line, tok.coloumn))
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
    line = line.rstrip("\n")
    if not line:
      nlines.append(line)
      continue
    if not line.endswith(";"):
      raise SyntaxError(f'invalid syntax\nline {index+1}\nevery line should end with ";"')
    nlines.append(line.rstrip(";"))
  code = "\n".join(list(line for line in nlines))
  return __CompiledCode(__Interpreter().interprete, fname)

def execute(code: __CompiledCode) -> None:
  if not isinstance(code, __CompiledCode):
    raise TypeError("The code must be compiled from ristpy module not any other")
  for send, result in Sender(CodeExecutor(str(code), arg_dict=get_builtins(), fname=code.file)):
    if result is None:
      continue
    send(result)
