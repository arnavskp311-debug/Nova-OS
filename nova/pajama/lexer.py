"""
Pajama Language Lexer (Tokenizer).
Extremely forgiving, supports Python-style comments (#), C-style comments (//),
optional punctuation, and natural English keyword tokens.
"""

import re
from typing import List, NamedTuple, Optional


class TokenType:
    # Keywords
    SAY = "SAY"
    ASK = "ASK"
    WAIT = "WAIT"
    PLAY = "PLAY"
    NOTIFY = "NOTIFY"
    NOTE = "NOTE"
    REMIND = "REMIND"
    RESEARCH = "RESEARCH"
    FLUSH = "FLUSH"
    SET = "SET"
    TO = "TO"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    BY = "BY"
    REPEAT = "REPEAT"
    TIMES = "TIMES"
    WHILE = "WHILE"
    FOR = "FOR"
    EACH = "EACH"
    IN = "IN"
    ROUTINE = "ROUTINE"
    GIVE = "GIVE"
    IF = "IF"
    OTHERWISE = "OTHERWISE"
    IS = "IS"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    CPU = "CPU"
    RAM = "RAM"
    LAUNCH = "LAUNCH"
    RUNNING = "RUNNING"
    CLOSE = "CLOSE"
    OPEN = "OPEN"
    STOPWATCH = "STOPWATCH"
    BEEP = "BEEP"
    WRITE = "WRITE"
    APPEND = "APPEND"
    READ = "READ"

    # Literals & Identifiers
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    NONE = "NONE"

    # Operators & Delimiters
    ASSIGN = "ASSIGN"          # =
    PLUS = "PLUS"              # +
    MINUS = "MINUS"            # -
    MULTIPLY = "MULTIPLY"      # *
    DIVIDE = "DIVIDE"          # /
    MODULO = "MODULO"          # %
    EQ = "EQ"                  # == or is
    NEQ = "NEQ"                # != or is not
    LT = "LT"                  # <
    GT = "GT"                  # >
    LTE = "LTE"                # <=
    GTE = "GTE"                # >=

    COLON = "COLON"            # :
    COMMA = "COMMA"            # ,
    LPAREN = "LPAREN"          # (
    RPAREN = "RPAREN"          # )
    LBRACKET = "LBRACKET"      # [
    RBRACKET = "RBRACKET"      # ]
    LBRACE = "LBRACE"          # {
    RBRACE = "RBRACE"          # }

    INDENT = "INDENT"
    DEDENT = "DEDENT"
    DOT = "DOT"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


class Token(NamedTuple):
    type: str
    value: any
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, line={self.line})"


KEYWORDS = {
    "say": TokenType.SAY,
    "ask": TokenType.ASK,
    "wait": TokenType.WAIT,
    "sleep": TokenType.WAIT,
    "play": TokenType.PLAY,
    "sound": TokenType.PLAY,
    "notify": TokenType.NOTIFY,
    "alert": TokenType.NOTIFY,
    "print": TokenType.SAY,
    "note": TokenType.NOTE,
    "remind": TokenType.REMIND,
    "research": TokenType.RESEARCH,
    "flush": TokenType.FLUSH,
    "launch": TokenType.LAUNCH,
    "start": TokenType.LAUNCH,
    "running": TokenType.RUNNING,
    "close": TokenType.CLOSE,
    "kill": TokenType.CLOSE,
    "open": TokenType.OPEN,
    "stopwatch": TokenType.STOPWATCH,
    "timer": TokenType.STOPWATCH,
    "beep": TokenType.BEEP,
    "write": TokenType.WRITE,
    "append": TokenType.APPEND,
    "read": TokenType.READ,
    "set": TokenType.SET,
    "to": TokenType.TO,
    "increase": TokenType.INCREASE,
    "decrease": TokenType.DECREASE,
    "by": TokenType.BY,
    "repeat": TokenType.REPEAT,
    "times": TokenType.TIMES,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "each": TokenType.EACH,
    "in": TokenType.IN,
    "routine": TokenType.ROUTINE,
    "def": TokenType.ROUTINE,
    "function": TokenType.ROUTINE,
    "give": TokenType.GIVE,
    "return": TokenType.GIVE,
    "if": TokenType.IF,
    "otherwise": TokenType.OTHERWISE,
    "else": TokenType.OTHERWISE,
    "is": TokenType.IS,
    "not": TokenType.NOT,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "cpu": TokenType.CPU,
    "ram": TokenType.RAM,
    "true": TokenType.BOOLEAN,
    "false": TokenType.BOOLEAN,
    "yes": TokenType.BOOLEAN,
    "no": TokenType.BOOLEAN,
    "none": TokenType.NONE,
    "null": TokenType.NONE,
}


class Lexer:
    """Tokenizes Pajama source code into a linear token stream with indent tracking."""

    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.indent_stack = [0]

    def error(self, msg: str):
        raise SyntaxError(f"Pajama Lexer Error [line {self.line}, col {self.col}]: {msg}")

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < self.length else ""

    def advance(self) -> str:
        if self.pos < self.length:
            ch = self.source[self.pos]
            self.pos += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            return ch
        return ""

    def match(self, expected: str) -> bool:
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        at_line_start = True

        while self.pos < self.length:
            ch = self.peek()

            # Handle markdown code fences (```, ```pajama, ```pj)
            if ch == "`":
                while self.peek() and self.peek() != "\n":
                    self.advance()
                continue

            # Handle markdown tables or decorative lines starting with '|'
            if at_line_start and ch == "|":
                while self.peek() and self.peek() != "\n":
                    self.advance()
                continue

            # Handle comments (//, #, /* */)
            if ch == "/" and self.peek(1) == "/":
                while self.peek() and self.peek() != "\n":
                    self.advance()
                continue
            elif ch == "#":
                while self.peek() and self.peek() != "\n":
                    self.advance()
                continue
            elif ch == "/" and self.peek(1) == "*":
                self.advance()
                self.advance()
                while self.peek() and not (self.peek() == "*" and self.peek(1) == "/"):
                    self.advance()
                if self.peek(): self.advance()
                if self.peek(): self.advance()
                continue

            # Newlines and indentation
            if ch == "\n":
                self.advance()
                tokens.append(Token(TokenType.NEWLINE, "\n", self.line - 1, self.col))
                at_line_start = True
                continue

            # Handle Indentation at line start
            if at_line_start:
                indent = 0
                while self.peek() in (" ", "\t"):
                    indent += 4 if self.peek() == "\t" else 1
                    self.advance()

                # Ignore blank lines
                if self.peek() in ("\n", "", "#") or (self.peek() == "/" and self.peek(1) in ("/", "*")):
                    at_line_start = False
                    continue

                current_indent = self.indent_stack[-1]
                if indent > current_indent:
                    self.indent_stack.append(indent)
                    tokens.append(Token(TokenType.INDENT, indent, self.line, self.col))
                elif indent < current_indent:
                    while self.indent_stack and indent < self.indent_stack[-1]:
                        self.indent_stack.pop()
                        tokens.append(Token(TokenType.DEDENT, indent, self.line, self.col))

                at_line_start = False
                continue

            # Skip spaces within a line
            if ch in (" ", "\t", "\r"):
                self.advance()
                continue

            # Strings
            if ch in ('"', "'"):
                quote = ch
                start_line = self.line
                start_col = self.col
                self.advance()
                chars = []
                while self.peek() and self.peek() != quote:
                    if self.peek() == "\\" and self.peek(1):
                        self.advance()
                        esc = self.advance()
                        if esc == "n": chars.append("\n")
                        elif esc == "t": chars.append("\t")
                        elif esc == "r": chars.append("\r")
                        else: chars.append(esc)
                    else:
                        chars.append(self.advance())
                if self.peek() == quote:
                    self.advance()
                tokens.append(Token(TokenType.STRING, "".join(chars), start_line, start_col))
                continue

            # Numbers (integers and floats)
            if ch.isdigit():
                start_col = self.col
                num_str = ""
                while self.peek().isdigit():
                    num_str += self.advance()
                if self.peek() == "." and self.peek(1).isdigit():
                    num_str += self.advance()  # '.'
                    while self.peek().isdigit():
                        num_str += self.advance()
                    tokens.append(Token(TokenType.NUMBER, float(num_str), self.line, start_col))
                else:
                    tokens.append(Token(TokenType.NUMBER, int(num_str), self.line, start_col))
                continue

            # Words / Identifiers / Keywords
            if ch.isalpha() or ch == "_":
                start_col = self.col
                ident = ""
                while self.peek().isalnum() or self.peek() == "_":
                    ident += self.advance()

                ident_lower = ident.lower()

                # Handle multi-word tokens like 'is not', 'otherwise if', 'greater than'
                if ident_lower in KEYWORDS:
                    ttype = KEYWORDS[ident_lower]
                    val = ident_lower
                    if ttype == TokenType.BOOLEAN:
                        val = True if ident_lower in ("true", "yes") else False
                    elif ttype == TokenType.NONE:
                        val = None
                    tokens.append(Token(ttype, val, self.line, start_col))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, ident, self.line, start_col))
                continue

            # Two-character operators
            start_col = self.col
            if ch == "=" and self.peek(1) == "=":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.EQ, "==", self.line, start_col))
                continue
            if ch == "!" and self.peek(1) == "=":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.NEQ, "!=", self.line, start_col))
                continue
            if ch == "<" and self.peek(1) == "=":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.LTE, "<=", self.line, start_col))
                continue
            if ch == ">" and self.peek(1) == "=":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.GTE, ">=", self.line, start_col))
                continue
            if ch == "|" and self.peek(1) == "|":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.OR, "or", self.line, start_col))
                continue
            if ch == "&" and self.peek(1) == "&":
                self.advance(); self.advance()
                tokens.append(Token(TokenType.AND, "and", self.line, start_col))
                continue

            # Handle pipes, ampersands, semicolons, and dots gracefully
            if ch == "|":
                self.advance()
                tokens.append(Token(TokenType.OR, "or", self.line, start_col))
                continue
            if ch == "&":
                self.advance()
                tokens.append(Token(TokenType.AND, "and", self.line, start_col))
                continue
            if ch == ";":
                self.advance()
                tokens.append(Token(TokenType.NEWLINE, "\n", self.line, start_col))
                continue
            if ch == "!":
                self.advance()
                tokens.append(Token(TokenType.NOT, "not", self.line, start_col))
                continue
            if ch == ".":
                self.advance()
                tokens.append(Token(TokenType.DOT, ".", self.line, start_col))
                continue

            # Single-character tokens
            self.advance()
            char_map = {
                "=": TokenType.ASSIGN,
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.MULTIPLY,
                "/": TokenType.DIVIDE,
                "%": TokenType.MODULO,
                "<": TokenType.LT,
                ">": TokenType.GT,
                ":": TokenType.COLON,
                ",": TokenType.COMMA,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
            }

            if ch in char_map:
                tokens.append(Token(char_map[ch], ch, self.line, start_col))
            else:
                # ZERO FRUSTRATION: Never crash on unknown characters ($, @, ~, ^, emoji, etc.)!
                continue

        # Emit remaining DEDENT tokens at EOF
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.append(Token(TokenType.DEDENT, 0, self.line, self.col))

        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens
