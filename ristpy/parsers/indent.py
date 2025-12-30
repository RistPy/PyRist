from .core import Token, TokenList


INDENT = "    "

class IndentParser:
    def __init__(self, scope: dict):
        scope["indents"] = [[""]]
        scope["parse_indent"] = self.parse
        self.scope = scope
        self.inline_stack: list[dict] = scope["inline_stack"]

    @property
    def indentlevel(self):
        return len(self.scope["indents"][self.stacklen]) - (0 if self.stacklen else 1)
    
    @property
    def stacklen(self):
        return len(self.inline_stack)

    def parse(self) -> str:
        tok = self.scope["current_token"]
        indents = self.scope["indents"][self.stacklen]
        ntoks: TokenList = self.scope["new_tokens"]
        last_real = ntoks.last_real

        if tok.name in "FROM IMPORT MACRO DECOR":
            indent = tok.value[:len(tok.value) - len(tok.value.lstrip())]
            tok.value = tok.value[len(indent):]
            tok = Token("INDENT", indent, tok.line, 0, under=tok.under)
            ntoks.append(tok)

        if tok.name == "INDENT":
            if tok.value != indents[-1]:
                err = None
                if last_real and last_real.value[-1] in ":({[\\":
                    if last_real.value[-1] != "\\": indents.append(tok.value)
                elif len(tok.value) < len(indents[-1]):
                    if tok.value in indents:
                        while tok.value != indents.pop():...
                        indents.append(tok.value)
                    else:
                        err = IndentationError("unindent does not match any outer indentation level")
                else:
                    err =  IndentationError("Unexpected Indent")
                if err:
                    kwrds = dict(filename=self.scope["filename"], lineno=tok.line, offset=tok.column, text=self.scope["lines"][tok.line-1])
                    for k, v in kwrds.items():
                        setattr(err, k, v)
                    raise err
                
            tok.value = INDENT * self.indentlevel
        elif tok.name not in "NEWLINE COMMENT" and ntoks.is_last_real("NEWLINE"):
            self.scope["indents"][-1] = [""]

        return INDENT * self.indentlevel