import math, json

def get_builtins():
  return {
    "JSON": dict,
    "Json": dict,
    "json": json,
    "math": math,
    "Math": math,
    "String": str,
    "Str": str,
    "Num": float,
    "Number": float,
    "Int": int,
    "Integer": int,
    "true": True,
    "false": False,
    "Boolean": bool,
    "boolean": bool,
    "Bool": bool
  }
