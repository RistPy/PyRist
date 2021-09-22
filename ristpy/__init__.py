__all__ = ("compile")

def __replace(code: str, key: str, value: str = "") -> str:
    while key in code:
        code = code.replace(key, value)

    return code

def __compile(code: str) -> str:
    code = __replace("{", "(")
    code = __replace("}", ")")
    code = __replace(";", "")
    return code

def compile(code: str) -> str:
    code = __compile(code)
    return code
