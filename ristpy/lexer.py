import re

from typing import Union


LexerError = SyntaxError

class Token:
  def __init__(
    self,
    name: str,
    value: Union[str, int],
    line: int,
    coloumn: int
  ) -> None:
    self.name = name
    self.value = value
    self.line = line
    self.coloumn = coloumn

  def __repr__(self) -> str:
    return '<Token name={0.name} value={0.value} line={1} coloumn={2.coloumn}>'.format(
      self, 
      self.line,
      self
    )

class Stream(list):
  pass

class Lexer:
    rules = [
        ('COMMENT', r'//.*'),
        ('STRING', r'"(\\"|[^"])*"'),
        ('STRING', r"'(\\'|[^'])*'"),
        ('NUMBER', r'\d+\.\d+'),
        ('NUMBER', r'\d+'),
        ('NAME', r'[a-zA-Z_]\w*|[a-zA-Z0-9_]\w*'),
        ('WHITESPACE', '[ \t]+'),
        ('NEWLINE', r'\n+'),
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

    ignore_tokens = [
        'WHITESPACE',
        'COMMENT',
    ]

    def __init__(self):
        self.source_lines = []
        self._regex = self._compile_rules(self.rules)

    def _convert_rules(self, rules):
        grouped_rules = OrderedDict()
        for name, pattern in rules:
            grouped_rules.setdefault(name, [])
            grouped_rules[name].append(pattern)

        for name, patterns in iteritems(grouped_rules):
            joined_patterns = '|'.join(['({})'.format(p) for p in patterns])
            yield '(?P<{}>{})'.format(name, joined_patterns)

    def _compile_rules(self, rules):
        return re.compile('|'.join(self._convert_rules(rules)))

    def _tokenize_line(self, line, line_num):
        pos = 0
        while pos < len(line):
            matches = self._regex.match(line, pos)
            if matches is not None:
                name = matches.lastgroup
                pos = matches.end(name)
                if name not in self.ignore_tokens:
                    value = matches.group(name)
                    if name in self.decoders:
                        value = self.decoders[name](value)
                    elif name == 'NAME' and value in self.keywords:
                        name = self.keywords[value]
                        value = None
                    yield Token(name, value, line_num, matches.start() + 1)
            else:
                raise LexerError('Unexpected character {}'.format(line[pos]), line_num, pos + 1)

    def _count_leading_characters(self, line, char):
        count = 0
        for c in line:
            if c != char:
                break
            count += 1
        return count

    def _detect_indent(self, line):
        if line[0] in (' ', '\t'):
            return line[0] * self._count_leading_characters(line, line[0])

    def tokenize(self, s):
        indent_symbol = None
        tokens = []
        last_indent_level = 0
        line_num = 0
        for line_num, line in enumerate(s.splitlines(), 1):
            line = line.rstrip()

            if not line:
                self.source_lines.append('')
                continue

            if indent_symbol is None:
                indent_symbol = self._detect_indent(line)

            if indent_symbol is not None:
                indent_level = line.count(indent_symbol)
                line = line[indent_level*len(indent_symbol):]
            else:
                indent_level = 0

            self.source_lines.append(line)

            line_tokens = list(self._tokenize_line(line, line_num))
            if line_tokens:
                if indent_level != last_indent_level:
                    if indent_level > last_indent_level:
                        tokens.extend([Token('INDENT', None, line_num, 0)] * (indent_level - last_indent_level))
                    elif indent_level < last_indent_level:
                        tokens.extend([Token('DEDENT', None, line_num, 0)] * (last_indent_level - indent_level))
                    last_indent_level = indent_level

                tokens.extend(line_tokens)
                tokens.append(Token('NEWLINE', None, line_num, len(line) + 1))

        if last_indent_level > 0:
            tokens.extend([Token('DEDENT', None, line_num, 0)] * last_indent_level)

        return Stream(tokens)

