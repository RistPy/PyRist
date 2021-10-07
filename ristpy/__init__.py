import secrets

from .tools import *
from .scope import *
from .walkers import *
from .executor import *
from .builtins import *

__all__ = ("rist", "execute")

class __CompiledCode:
  def __init__(self, code: str, fname: str = '<rist-executor>`) -> None:
    self.__code = code
    self.file = fname

  def __repr__(self) -> str:
    return str(self)

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
  code = __replace(code, ") → ", ") -> ")
  code = __replace(__replace(code, d1, "{"), d2, "}")
  code = __replace(code, "define", "def")
  return code

def rist(arg: str, fp: bool = True) -> str:
  if fp:
    with open(arg, 'r') as f:
      code = f.read()
    fname = arg
  else:
    code = arg
    fname = None
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
  return __CompiledCode(__compileall(code), fname)

def execute(code: __CompiledCode) -> None:
  if not isinstance(code, __CompiledCode):
    raise TypeError("The code must be compiled from ristpy module not any other")
  for send, result in Sender(CodeExecutor(str(code), arg_dict=get_builtins(), fname=code.file)):
    if result is None:
      continue
    send(result)
