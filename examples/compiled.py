
def _0xe607e4c9_wrapper(_g, _l):
    locals().update(_g)
    locals().update(_l)
    del _g,_l

    def cls():

        
        clear_cmd: str
        if os.name == "nt":
            clear_cmd = "cls"
        else:
            clear_cmd = "clear"
        os.system(clear_cmd)


    cls.__name__ = 'cls'
    cls.__qualname__ = 'cls'
    return cls

_0xe607e4c9_wrapper.__name__ = '<rist:inline-wrapper>'
_0xe607e4c9_wrapper.__qualname__ = '<rist:inline-wrapper>'
import os, pprint
((_0xe607e4c9_wrapper(globals(), locals())))()
def something(arg: str|int):
    args: dict = {"arg": [arg]}
    pprint.pprint(args)
    return args
smth: dict = something("text2")
print(smth)