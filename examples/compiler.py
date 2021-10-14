from ristpy import rist

compiled = str(rist("main.rist"))

with open("compiled.py", "w") as f:
  f.write(compiled)
  f.close()
