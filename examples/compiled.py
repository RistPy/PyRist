import os, pprint
from typing import Union

def cls():
  os.system("cls" if os.name == "nt" else "clear")

cls()

def something(arg: Union[str, int]):
  pprint.pprint(["myText", [arg]])

something("text2")
