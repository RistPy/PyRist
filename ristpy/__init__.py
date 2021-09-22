def _replace(code: str, key: str, value: str = "") -> str:
    while key in code:
        code = code.replace(key, value)

    return code

def _replaceall(code: str) -> str:
    code = _replace(code, "{", "(")
    code = _replace(code,"}", ")")
    code = _replace(code, ";", "")
    return code

def rist(fp: str) -> str:
    with open(fp, 'r') as f:
        code = f.read()
    code = _replaceall(code)
    return code
