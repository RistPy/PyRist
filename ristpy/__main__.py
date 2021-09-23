import argparse

from ristpy import rist, execute

def compile_to(parser, to_read, to_write):
    if not to_read.endswith(".rist"):
        raise TypeError("You must provide the file which is to be to compiled, with extension '.rist'")
    if not to_write.endswith(".py"):
        raise TypeError("You must provide file which will be written with extension '.py'")
    try:
        with open(to_write, 'w', encoding='utf-8') as fp:
            fp.write(rist(to_read))
    except OSError as exc:
        parser.error(f'could not create file ({exc})')
    else:
        print('successfully compiled code at', to_write)

def compile_and_run(fp: str):
    if not fp.endswith(".rist"):
        raise TypeError("You must provide file with extension '.rist'")
    code = rist(fp)
    execute(code)

def compile_fp(parser, args):
    if args.file and args.compile_to:
        compile_to(parser, args.file, args.compile_to)
    elif args.file:
        compile_and_run(args.file)

def parse_args():
    parser = argparse.ArgumentParser(prog='rist', description='Rist Lang')
    parser.add_argument('file', type=str, help='compiles rist lang to python and executes it.')
    parser.set_defaults(func=compile_fp)
    parser.add_argument('--compile-to', help='only compile code and place it to provided file', type=str, metavar="<filepath>")
    return parser, parser.parse_args()

def main():
    parser, args = parse_args()
    args.func(parser, args)

if __name__ == "__main__":
    main()
