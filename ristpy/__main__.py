import argparse

from ristpy import rist, execute

def compile_and_run(fp: str):
    if not fp.endswith(".rist"):
        raise TypeError("You must provide file with extension '.rist'")
    code = rist(fp)
    execute(code)

def compile_fp(parser, args):
    if args.file:
        compile(args.file)

def parse_args():
    parser = argparse.ArgumentParser(prog='rist', description='Rist Lang')
    parser.add_argument('file', type=str, help='compiles rist lang to python and executes it.')
    parser.set_defaults(func=compile_fp)
    return parser, parser.parse_args()

def main():
    parser, args = parse_args()
    args.func(parser, args)

if __name__ == "__main__":
    main()
