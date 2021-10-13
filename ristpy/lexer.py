import re
import copy

from collections import OrderedDict
from typing import Union, List, Generator


class Token:
  def __init__(
    self,
    name: str,
    value: Union[str, int],
    line: int,
    coloumn: int
  ) -> None:
    self.name = name
    self.value = str(value)
    self.line = line
    self.coloumn = coloumn

  def __repr__(self) -> str:
    return "<Token name='{0.name}' value='{0.value}' line={0.line} coloumn={0.coloumn}>".format(
      self
    )

  def __str__(self) -> str:
    return str(self.value)

class Stream:
  def __init__(self, tokens: List[Token]) -> None:
    self.__tokens = tokens

  @property
  def tokens(self) -> List[Token]:
    return copy.deepcopy(self.__tokens)

  def __repr__(self) -> str:
    return '<Stream tokens={0.tokens}>'.format(self)

  def __str__(self) -> str:
    return "".join(list(str(token) for token in self.tokens))

  def main(self) -> List[Token]:
    ntoks = []
    for tok in self.tokens:
      if tok.name == "LCBRACK" and tok.value == "{":
        ntoks.append(Token("LPAREN", "(", tok.line, tok.coloumn))
      elif tok.name == "RCBRACK" and tok.value == "}":
        ntoks.append(Token("RPAREN", ")", tok.line, tok.coloumn))
      elif tok.name == "COMMENT":
        ntoks.append(Token("COMMENT", ("#"+tok.value[2:]), tok.line, tok.coloumn))
      elif tok.name == "FUNCDEF" and tok.value == "define":
        ntoks.append(Token("FUNCDEF", "def", tok.line, tok.coloumn))
      else:
        ntoks.append(tok)

    return ntoks

class Lexer:
    rules = [
        ('COMMENT', r'//.*'),
        ('STRING', r'"(\\"|[^"])*"'),
        ('STRING', r"'(\\'|[^'])*'"),
        ('NUMBER', r'\d+\.\d+'),
        ('NUMBER', r'\d+'),
        ('FUNCDEF', 'define'),
        ('NAME', r'[a-zA-Z_]\w*|[a-zA-Z0-9_]\w*'),
        ('TABSPACE', '\t'),
        ('SPACE', ' '),
        ('OPERATOR', r'[\+\*\-\/%]'),       # arithmetic operators
        ('OPERATOR', r'<=|>=|==|!=|<|>'),   # comparison operators
        ('OPERATOR', r'\|\||&&'),           # boolean operators
        ('OPERATOR', r'\.\.\.|\.\.'),       # range operators
        ('OPERATOR', '!'),                  # unary operator
        ('ASSIGN', '='),
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACK', r'\['),
        ('RBRACK', r'\]'),
        ('LCBRACK', '{'),
        ('RCBRACK', '}'),
        ('COLON', ':'),
        ('COMMA', ','),
        ('DOT', '.'),
        ('FROM', r'\+@'),
        ('IMPORT', r'@\+')
    ]

    def __init__(self) -> None:
        self.source_lines = []
        self._regex = self._compile_rules(self.rules)

    def _convert_rules(self, rules) -> Generator[str]:
        grouped_rules = OrderedDict()
        for name, pattern in rules:
            grouped_rules.setdefault(name, [])
            grouped_rules[name].append(pattern)

        for name, patterns in iter(grouped_rules.items()):
            joined_patterns = '|'.join(['({})'.format(p) for p in patterns])
            yield '(?P<{}>{})'.format(name, joined_patterns)

    def _compile_rules(self, rules):
        return re.compile('|'.join(self._convert_rules(rules)))

    def _tokenize_line(self, line, line_num) -> Generator[Token]:
        pos = 0
        while pos < len(line):
            matches = self._regex.match(line, pos)
            if matches is not None:
                name = matches.lastgroup
                pos = matches.end(name)
                value = matches.group(name)
                if name == "TABSPACE":
                    value = "	"
                elif name == "SPACE":
                    value = " "
                yield Token(name, value, line_num, matches.start() + 1)

    def tokenize(self, s) -> Stream
        tokens = []
        line_num = 0
        for line_num, line in enumerate(s.splitlines(), 1):
            line = line.rstrip()

            if not line:
                tokens.append(Token('NEWLINE', "\n", line_num, 1)
                continue

            line_tokens = list(self._tokenize_line(line, line_num))
            if line_tokens:
                tokens.extend(line_tokens)
                tokens.append(Token('NEWLINE', "\n", line_num, len(line) + 1))

        return Stream(tokens)

