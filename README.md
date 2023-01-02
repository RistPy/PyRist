# RistPy
A programming language made by me ([@Rishiraj0100](https://GitHub.com/Rishiraj0100))
```
R  - Rist
I  - Is
S  - Short
T  - Text
Py - Python
```
## Usage

First of all, it should be installed by
```sh
python3 -m pip install -U RistLang
```

Create a file named `main.rist`<br />
A sample code is given here
```rist
@+ os, pprint
+@ typing @+ Union

cls${}: os.system{"cls" if os.name == "nt" $e "clear"}

cls{}

something${arg: Union[str, int]}:
  p$p.p$p{["myText", [arg]]};

something{"text2"};
```

Then in your shell
```sh
rist run main.rist
```
Or if you want to compile into python file then run in your shell
```sh
rist run main.rist --compile-to rist_compiled_main.py
```
Or in your python file
```py
from ristpy import rist, E, W

print(rist("main.rist"))
# if you want some text to compile then

code = """
$p{"hello"} # Print
"""
print(rist(code, fp=False))
# if you wanna execute then
rist(code, fp=False, flags=E) # E flag means execute
rist('main.rist', flags=E)
# compile code somewhere
rist("main.rist", flags=W, compile_to="main.py") # W flag means write
# if execute too then
rist("main.rist", flags=W|E, compile_to="main.py")
```

## Syntax
### Importing
#### What can it Import?

It can Import all python modules

#### How to Import?
In python you do `import asyncio`

In rist you have to do `@+ asyncio`

In python you do `from aiohttp import web`

In rist you have to do `+@ aiohttp @+ web`

### Functions
How do i make a function?
#### Making a function
```rist
# synchronous func;
foo${}: # <name_of_func> + $
  pass

# asynchronous func
$bar${}: # $ + <name_of_func> + $
  pass
```
How do i call it?
#### Calling a function
```rist
# synchronous function
foo{}

# asynchronous func
?bar{} # ? + <name_of_func>
```
### Dict 
How can I make dict as `{}` is used as `()`
#### Working With Dict
To make dict to things are here
`()` and `<>`
For example
```rist
("hi": "hello")
("hello": ("wor": "ld"))
<"hi": "hi">

# mixed
<
  1: <
    2: (
      3: 4
    ),
    5: 6
  >,
  7: 8
>
```
### Tuples and lists
#### Making a List 
```rist
[1,2]
[
  1,
  2
]
```
#### Making a Tuple 
```rist
{1,2}
{
  1,
  2
}
```
### Function Return TypeHints
How do I use `def myfunc() -> None:` in rist as `>` symbol
is used in dict?

`>` is used for dictionary but however, typehints
doesn't gets converted, it's like `} -> Any:`
```rist
SomeFunc${} -> None:
  pass
```
### Comments 
To use comments in this language, use `#`, Just like Python

For example:-
```rist
# Some comment
```
### Built-ins
Like every language, this language also have
some built-in functions, but with other syntax

The syntax made for them is `$ + <function name>`
```rist
$f    # for
$i    # int
$s    # str
$y    # try
$x    # xor
$d    # dict
$ei   # elif
$e    # else
$l    # list
$p    # pass
$t    # type
$b    # break
$n    # input
$p    # print
$u    # tuple
$yi   # yield
$ex   # except
$la   # lambda
$o    # locals
$fi   # finally
$g    # globals
$ret  # return
$co   # continue
$m    # __import__
$r    # ristpy.rist
$eval # run rist code
$re   # regex library (re)
```

The `xor` given here is a function provided by rist
which takes two inputs/parameters and returns boolean value as follows:

| Input1 | Input2 | Output |
---------|--------|---------
| False | False | False |
| False | True | True |
| True | False | True |
| True | True | False |

Which can be written as
```rist
t = True
f = False

$p{$x{f,f}}
$p{$x{f,t}}
$p{$x{t,f}}
$p{$x{t,t}}
```
And its output will be
```
False
True
True
False
```

## Encryptions/Decryptions
Encryptions and Decryptions too comes with rist.
You can encrypt anything with rist!

### Encrypting from shell
If you want to encrypt something, then just run this in your shell
```
rist encrypt --filepath <file_to_encrypt> --output <encrypted_output_file> --key <any_integer> --depth 2
```
Here, key is any number of your choice which will be the passcode and it is optional.
Generates automatically if not given
Depth is also a number, between 1 to 8 which specifies the layers/times
it will be encrypted. It is 1 by default

For example:
```
rist encrypt --filepath myfile.rist --output myfile.rist.enc --key 22 --depth 2
```

### Encrypting from rist
If you want to encrypt something from rist, then
```rist
+@ ristpy @+ encrypt

text="Some_Text"
encrypted=encrypt{text,22,depth=2}
$p{encrypted}
```


### Decrypting from shell
If you want to Decrypt something, then just run this in your shell
```
rist decrypt --filepath <file_to_decrypt> --output <decrypted_output_file> --key <your_key> --depth <the_depth_you_used>
```
For example:
```
rist decrypt --filepath myfile.rist.enc --output myfile.rist --key 22 --depth 2
```

### Decrypting from rist
If you want to decrypt something from rist, then
```rist
+@ ristpy @+ decrypt

text="1100 1254 1166 1254 726 1122 1166 1210 1166 726 1122 1166 1122 1078 726 1122 1122 1166 1166 726 1122 1100 1100 1122 726 1100 1254 1232 1078 726 1122 1122 1166 1166 726 1122 1210 1210 1122 726 1122 1188 1232 1166"
decrypted=decrypt{text,22,depth=2}
$p{decrypted}
```
