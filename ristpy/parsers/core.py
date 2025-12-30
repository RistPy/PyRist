class Token:
    def __init__(
        self,
        name: str,
        value: str | int,
        line: int,
        column: int,
        under: str | None = None
    ) -> None:
        self.name = name
        self.value = str(value)
        self.line = line
        self.column = column
        self.call = False
        self.under = under

    def __repr__(self) -> str:
        return "<Token name='{0.name}' value='{0.value}' line={0.line} column={0.column}>".format(
            self
        )

    def __str__(self) -> str:
        return str(self.value)


class TokenList(list[Token]):
    @property
    def last_real(self) -> Token:
        for tok in self[::-1]:
            if tok.name in "INDENT TABSPACE NEWLINE COMMENT":
                continue

            return tok
        
    def is_last_real(self, *names: str) -> bool:
        for tok in self[::-1]:
            if tok.name in names: return True
            if tok.name in "TABSPACE NEWLINE COMMENT":
                continue

            return tok.name in names
        
        return False
    
    def append(self, token: Token):
        if token.under is None:
            if self and self[-1].under is not None:
                token.under = self[-1].under
            
        return super().append(token)
    
    def count(self, item) -> int:
        if isinstance(item, str):
            c = 0
            for i in self:
                if i.name == item:
                    c += 1

            return c
        return super().count(item)

    def splice(self, start: int, delete_count: int, *items):
        """
        Remove `delete_count` tokens starting at `start`
        and insert `items` in their place.

        Returns a TokenList of removed tokens.
        """
        length = len(self)

        # Normalize start
        if start < 0:
            start = max(length + start, 0)
        elif start > length:
            start = length

        # Normalize delete_count
        delete_count = max(0, min(delete_count, length - start))

        removed = self[start:start + delete_count]

        # Perform replacement
        self[start:start + delete_count] = items

        return TokenList(removed)

    def detokenize(self) -> str:
        res = ""
        cache = []
        push = False
        for i in self:
            if i.name == "NEWLINE":
                if push:
                    res += "".join(cache)
                    push = False
                cache.clear()
            elif i.name in "INDENT":...
            else:push = True

            cache.append(i.value)

        return res
