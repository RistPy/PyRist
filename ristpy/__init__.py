from .tools import *
from .scope import *
from .walkers import *
from .compiler import *

def _replace(code: str, key: str, value: str = "") -> str:
    while key in code:
        code = code.replace(key, value)

    return code

def _replaceall(code: str) -> str:
    code = _replace(code, "+@", "from")
    code = _replace(code, "@+", "import")
    code = _replace(code, "{", "(")
    code = _replace(code,"}", ")")
    code = _replace(code, ";", "")
    return code

def rist(arg: str, fp: bool = True) -> str:
    if fp:
        with open(arg, 'r') as f:
            code = f.read()
    else:
        code = arg

    lines = code.splitlines()
    for index, line in enumerate(lines):
        if line == "":
            continue

        if not line.endswith(";"):
            raise SyntaxError(f'invalid syntax\nline {index+1}\nevery line should end with ";"')

    code = _replaceall(code)
    return code

def execute(code: str):
    for send, result in Sender(CodeExecutor(code)):
        if result is None:
            continue

        send((yield result))
