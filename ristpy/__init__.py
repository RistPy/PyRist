import re
import secrets

from .tools import *
from .scope import *
from .walkers import *
from .executor import *
from .builtins import *

__all__ = ("rist", "execute")

class __CompiledCode:
  def __init__(self, code: str) -> None:
    self.__code = code

  def __repr__(self) -> str:
    return "<CompiledCode length={0} from=rist to=python>".format(len(self.code))

  def __str__(self) -> str:
    return self.__code

  @property
  def code(self) -> str:
    return self.__code

def __replace(code: str, key: str, value: str = "") -> str:
    while key in code:
        code = code.replace(key, value)
    return code

def __interprete_imports(line: str) -> str:
  if line.startswith("+@ ") and " @+ " in line:
    return __replace(__replace(line, "+@", "from"), "@+", "import")
  if line.startswith("@+ "):
    return __replace(line, "@+", "import")
  return line

def __interprete_comments(line: str) -> str:
  if '//' not in line:
    return line
  if re.search('//.*', line):
    h = secrets.token_urlsafe(50)
    line = __replace(line, '#', h)
    line = __replace(__replace(line, '//', '#'), h, "//")
  return line

def __interpreteall(code: str) -> str:
  lines = code.splitlines()
  nlines = []
  for line in lines:
    line.rstrip("\n")
    line = __interprete_imports(line)
    line = __interprete_comments(line)
    nlines.append(line)
  return "\n".join(list(line for line in nlines))

def __compileall(code: str) -> str:
  d1 = secrets.token_urlsafe(50)
  d2 = secrets.token_urlsafe(50)
  code = __interpreteall(code)
  code = __replace(__replace(code, "(", d1), ")", d2)
  code = __replace(code, "} =-> ", "} → ")
  code = __replace(__replace(code, "}", ")"), "{", "(")
  code = __replace(__replace(code, ">", "}"), "<", "{")
  code = __replace(code, "} → ", "} -> ")
  code = __replace(__replace(code, d1, "{"), d2, "}")
  code = __replace(code, "define", "def")
  return code

def rist(arg: str, fp: bool = True) -> str:
  if fp:
    with open(arg, 'r') as f:
      code = f.read()
  else:
    code = arg
  lines = code.splitlines()
  nlines = []
  for index, line in enumerate(lines):
    line = line.rstrip("\n")
    if line == "":
      nlines.append(line)
      continue
    if not line.endswith(";"):
      raise SyntaxError(f'invalid syntax\nline {index+1}\nevery line should end with ";"')
    nlines.append(line.rstrip(";"))
    code = "\n".join(list(line for line in nlines))
    return __CompiledCode(__compileall(code))

def execute(code: __CompiledCode) -> None:
  if not isinstance(code, __CompiledCode):
    raise TypeError("The code must be compiled from ristpy module not any other")
  code = str(code)
  for send, result in Sender(CodeExecutor(code, arg_dict=get_builtins())):
    if result is None:
      continue
    send(result)
