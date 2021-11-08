import os, pprint
from typing import Union

def cls():
  clear_cmd: str
  if os.name == "nt":
    clear_cmd = "cls"
  else:
    clear_cmd = "clear"
  os.system(clear_cmd)

cls()

def something(arg: Union[str, int]):
  args: dict = {"arg": [arg]}
  pprint.pprint(args)
  return args

smth: dict = something("text2")
print(smth)
