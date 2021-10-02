# PyRist
The programming language made by me ([@Rishiraj0100](https://GitHub.com/Rishiraj0100))

## Usage

First of all, it should be installed by
```sh
python3 -m pip install git+https://github.com/Rishiraj0100/PyRist/
```

Create a file named `main.rist`<br />
A sample code is given here
```rist
@+ os, pprint;
+@ typing @+ Union;

define cls{}:;
  os.system{"cls" if os.name == "nt" else "clear"};

cls{};

define something{arg: Union[str, int]}:;
  pprint.pprint{["myText", [arg]]};

something{"text2"};
```

Then in your shell
```sh
python3 -m ristpy main.rist
```

If you want to compile it to python then in your python file
```py
from ristpy import rist, execute

print(rist("main.rist"))
# if you want some text then

code = """
print{"hello"};
"""
print(rist(code, fp=False))
# if you wanna execute then
execute(rist(code, fp=False))
execute(rist('main.rist'))
```

## Syntax
### Note
Every line should end with `;` only if line is not empty
### Importing
#### What can it Import?

It can Import all python3 modules

#### How to Import?
In python you do `import asyncio`

In rist you have to do `@+ asyncio;`

In python you do `from aiohttp import web`

In rist you have to do `+@ aiohttp @+ web;`

### Functions
How do i make a function?
#### Making a function
```rist
# sync func;
define MyFunc{}:;
  pass;
# async func;
async define AsMyFunc{}:;
  pass;
```
How do i call it?
#### Calling a function
```rist
# sync function;
MyFunc{};
# async func;
await AsMyFunc{};
```
### Dict
How can I make dict as `{}` is used as `()`
#### Working With Dict
To make dict to things are here
`()` and `<>`
For example
```rist
("hi": "hello");
("hello": ("wor": "ld"));
<"hi": "hi">;
# mixed;
<;
  1: <;
    2: (;
      3: 4;
    ),;
    5: 6;
  >,;
  7: 8;
>;
```
### Tuples and lists
#### Making a List
```rist
[1,2];
[;
  1,;
  2;
];
```
#### Making a Tuple
```rist
{1,2};
{;
  1,;
  2;
};
```
### More Syntax

Coming soon....
