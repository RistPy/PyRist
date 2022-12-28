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
python3 -m pip install git+https://github.com/RistPy/PyRist/
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
$i    # int
$s    # str
$y    # try
$x    # xor
$d    # dict
$ei   # elif
$e    # else
$l    # list
$t    # type
$n    # input
$p    # print
$u    # tuple
$ex   # except
$la   # lambda
$o    # locals
$fi   # finally
$g    # globals
$m    # __import__
$r    # ristpy.rist
$eval # run rist code
```
