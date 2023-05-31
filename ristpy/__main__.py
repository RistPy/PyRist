import os
import json
import atexit
import signal
import argparse

from ristpy import rist, execute, E, W, encrypt, decrypt


def init(parser, args):
  if "ristconf.json" not in os.listdir():
    return parser.error("A file named 'ristconf.json' should must be in the project directory")
  try:
    with open("ristconf.json", "r") as f: conf=json.load(f)
  except Exception as e:
    raise e

  main=conf.get("main") or ""
  assert bool(main) is True, "A setting named 'main' should must be in the config file"
  assert main.endswith(".rist"), "Your main file should must be a rist file"
  mf=main if "/" in main else "./"+main
  macros = conf.get("snippets", {})
  for name, snippet in macros.items():
    if type(snippet) is list: macros[name] = "\n".join(snippet)
      
  macros_py = conf.get("snippets_py", {})
  for name, snippet in macros_py.items():
    if type(snippet) is list:
      snippet = "\n".join(snippet)
    macros_py[name] = snippet.splitlines()
    
  
  for n, snippet in macros.items():
    assert n not in macros_py, "Name of all the snippets should be unique"
    macros_py[n] = rist(snippet, False, file=f"<macro_{n}>", macro_py=macros_py).splitlines()

  dirs=conf.get("dirs") or []
  ign=conf.get("ignore") or []
  ign.append(mf)
  if "." not in dirs: dirs.append(".")
  pyfiles=[]
  def rm():
    for f in pyfiles:
      try:os.remove(f)
      except:continue
  try:
    def mk(f):
      nonlocal pyfiles
      if f not in ign:
        pyfiles.append(f[:-4]+"py")
        rist(f, flags=W, compile_to=f[:-4]+"py", macros_py={**macros_py})
    for dir in dirs:
      if not dir.endswith("/"): dir+="/"
      for file in os.listdir(dir):
        if file.endswith(".rist"):
          file=dir+file
          mk(file)
    mk(main)
    atexit.register(rm)
    signal.signal(signal.SIGTERM, rm)
    signal.signal(signal.SIGINT, rm)
    os.system(f'python3 {main[:-4]+"py"}')
  except Exception as e:
    rm()
    raise e
  finally:
    rm()

def compile_to(parser, to_read, to_write):
  if not to_read.endswith(".rist"):
    return parser.error("You must provide the file which is to be to compiled, with extension '.rist'")
  try:
    rist(to_read, flags=W, compile_to=to_write)
  except OSError as exc:
    parser.error(f'could not create file ({exc})')
  else:
    print('successfully compiled code at', to_write)

def compile_and_run(parser, fp: str):
  if not fp.endswith(".rist"):
    return parser.error("You must provide file with extension '.rist'")
  rist(fp,flags=E)

def compile_fp(parser, args):
  if args.compile_to:
    compile_to(parser, args.file, args.compile_to)
  compile_and_run(parser, args.file)

def enc(parser, args):
  try:
    arg,depth,key = args.arg,1,True
    if args.filepath: arg = open(args.arg).read()
    if args.depth: depth=args.depth
    if args.key: key = False
    code = encrypt(arg,args.key,depth=depth)
    if key: code,key=code
    if args.output:
      with open(args.output,"w") as f: f.write(code)
    else: print("Encryption success\n\n",code)
    if key: print("\n\n Your encryption key is:",str(key),"\nPlz don't forget it, it is used to decrypt encrypted thing")
  except Exception as e:
    parser.error(e.__class__.__name__+": "+str(e))

def dec(parser, args):
  try:
    arg,depth = args.arg,1
    if not args.key: return parser.error("You must provide a 'key' for decryption")
    if args.filepath: arg = open(args.arg).read()
    if args.depth: depth=args.depth
    code = decrypt(arg,args.key,depth=depth)
    if args.output:
      with open(args.output,"w") as f: f.write(code)
    else: print("Decryption success\n\n",code)
  except Exception as e:
    parser.error(e.__class__.__name__+": "+str(e))

def parse_args():
  _parser_ = argparse.ArgumentParser(prog='rist', description='Rist Lang')
  _parser_.set_defaults(func=(lambda p,a: None))
  _parser = _parser_.add_subparsers(dest="subcommands",title="subcommands")

  runner = _parser.add_parser('init', help="Compile and run rist files in bulk")

  runner.set_defaults(func=init)

  parser = _parser.add_parser("run",help="Run and compile any rist code")

  parser.set_defaults(func=compile_fp)
  parser.add_argument('file', type=str, help='The file to be compiled in python')
  parser.add_argument('--compile-to', '-CT', help='Compiles the code, write in the provided file and then executes it', type=str, metavar="<filepath>")

  writer = _parser.add_parser("compile",help="Compile any rist code")

  writer.set_defaults(func=(lambda p,a: compile_to(p, a.file, a.output)))
  writer.add_argument('file', type=str, help='The file to be compiled')
  writer.add_argument('output', type=str, help='The file where compiled code would be written')

  subp_e = _parser.add_parser("encrypt", help="Encrypt any thing")

  subp_e.set_defaults(func=enc)
  subp_e.add_argument("arg", help="The argument/file to encrypt", metavar="<argument>")
  subp_e.add_argument("--key","-K", help="The key to encrypt (must be integer, default: random generated)", type=int)
  subp_e.add_argument("--depth","-D",help="The depth/layer for encryption (must be integer, default: 1)", type=int, default=1)
  subp_e.add_argument("--filepath","-FP",help="Provide when the argument is a filepath",action='store_true')
  subp_e.add_argument("--output","-O",help="The output file where the encrypted thing will be written, will print if not given",type=str, default=None)

  subp_d = _parser.add_parser("decrypt", help="Decrypt any thing")

  subp_d.set_defaults(func=dec)
  subp_d.add_argument("arg", help="The argument/file to decrypt", metavar="<argument>")
  subp_d.add_argument("--key","-K", help="The key to decrypt (must be integer,)", type=int, metavar="<key>")
  subp_d.add_argument("--depth","-D",help="The depth/layer for encryption to decode (must be integer, default: 1)", type=int, default=1)
  subp_d.add_argument("--filepath","-FP",help="Provide when the argument is a filepath",action='store_true')
  subp_d.add_argument("--output","-O",help="The output file where the decrypted thing will be written, will print if not given",type=str, default=None)

  return _parser_, _parser_.parse_args()

def main():
  parser, args = parse_args()
  args.func(parser, args)

if __name__ == "__main__":
  main()
