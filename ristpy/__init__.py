import secrets

from .tools import *
from .scope import *
from .walkers import *
from .executor import *
from .builtins import *

__all__ = ("rist", "execute")

class _CompiledCode:
  def __init__(self, code: str) -> None:
    self.__code = code

  def __repr__(self) -> str:
    return "<CompiledCode length={0} from=rist to=python>".format(len(self.code))

  def __str__(self) -> str:
    return self.__code

  @property
  def code(self) -> str:
    return self.__code

def _replace(code: str, key: str, value: str = "") -> str:
    while key in code:
        code = code.replace(key, value)

    return code

def _interprete_imports(code: str) -> str:
  lines = code.splitlines()
  nlines = []
  for index, line in enumerate(lines):
      line.rstrip("\n")
      if line.startswith("+@ ") and " @+ " in line:
        nlines.append(_replace(_replace(line, "+@", "from"), "@+", "import"))
      elif line.startswith("@+ "):
        nlines.append(_replace(line, "@+", "import"))
      else:
        nlines.append(line)

  return "\n".join(list(line for line in nlines))

def _replaceall(code: str) -> str:
    d1 = secrets.token_urlsafe(50)
    d2 = secrets.token_urlsafe(50)
    code = _interprete_imports(code)
    code = _replace(_replace(code, "(", d1), ")", d2)
    code = _replace(_replace(code,"}", ")"), "{", "(")
    code = _replace(_replace(code, ">", "}"), "<", "{")
    code = _replace(code, "→", ">")
    code = _replace(_replace(code, d1, "{"), d2, "}")
    code = _replace(code, "define", "def")
    code = _replace(code, ";", "")
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
    return _CompiledCode(_replaceall(code))

def execute(code: _CompiledCode):
    if not isinstance(code, _CompiledCode):
        raise TypeError("The code must be compiled from ristpy module not any other")
    code = str(code)
    for send, result in Sender(CodeExecutor(code, arg_dict=get_builtins())):
        if result is None:
            continue

        send(result)
