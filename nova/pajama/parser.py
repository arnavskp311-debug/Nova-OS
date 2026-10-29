"""
Pajama Language Parser (AST Builder).
Builds an Abstract Syntax Tree from the token stream produced by Lexer.
Designed to be forgiving, friendly, and robust against formatting variations.
"""

from typing import List, Optional, Any, Tuple
from nova.pajama.lexer import Token, TokenType, Lexer


# =============================================================================
# AST Node Hierarchy
# =============================================================================

class ASTNode:
    """Base class for all AST nodes."""
    def __init__(self, line: int = 1, col: int = 1):
        self.line = line
        self.col = col

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class Program(ASTNode):
    def __init__(self, statements: List[ASTNode]):
        super().__init__(1, 1)
        self.statements = statements

    def __repr__(self):
        return f"Program({self.statements})"


# Statements
class SayStmt(ASTNode):
    def __init__(self, expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.expr = expr

    def __repr__(self):
        return f"SayStmt({self.expr})"


class AssignStmt(ASTNode):
    def __init__(self, name: str, expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.expr = expr

    def __repr__(self):
        return f"AssignStmt({self.name} = {self.expr})"


class ChangeStmt(ASTNode):
    """increase <var> by <num> or decrease <var> by <num>"""
    def __init__(self, name: str, op: str, amount: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.op = op  # "increase" or "decrease"
        self.amount = amount

    def __repr__(self):
        return f"ChangeStmt({self.op} {self.name} by {self.amount})"


class IfStmt(ASTNode):
    def __init__(self, branches: List[Tuple[ASTNode, List[ASTNode]]], otherwise_branch: Optional[List[ASTNode]] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.branches = branches  # list of (condition, [statements])
        self.otherwise_branch = otherwise_branch

    def __repr__(self):
        return f"IfStmt(branches={len(self.branches)}, has_else={self.otherwise_branch is not None})"


class RepeatStmt(ASTNode):
    """repeat <count_expr> times: <body>"""
    def __init__(self, count_expr: ASTNode, body: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.count_expr = count_expr
        self.body = body

    def __repr__(self):
        return f"RepeatStmt({self.count_expr} times)"


class WhileStmt(ASTNode):
    def __init__(self, condition: ASTNode, body: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"WhileStmt({self.condition})"


class ForEachStmt(ASTNode):
    """for each <var> in <iterable>: <body>"""
    def __init__(self, var_name: str, iterable: ASTNode, body: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.var_name = var_name
        self.iterable = iterable
        self.body = body

    def __repr__(self):
        return f"ForEachStmt({self.var_name} in {self.iterable})"


class WaitStmt(ASTNode):
    """wait <num> seconds or sleep <num>"""
    def __init__(self, seconds_expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.seconds_expr = seconds_expr

    def __repr__(self):
        return f"WaitStmt({self.seconds_expr})"


class RoutineDef(ASTNode):
    """routine <name>(<params>): <body>"""
    def __init__(self, name: str, params: List[str], body: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.params = params
        self.body = body

    def __repr__(self):
        return f"RoutineDef({self.name}({self.params}))"


class GiveStmt(ASTNode):
    """give <expr> or return <expr>"""
    def __init__(self, expr: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.expr = expr

    def __repr__(self):
        return f"GiveStmt({self.expr})"


class FileActionStmt(ASTNode):
    """write <path>, <content> or append <path>, <content>"""
    def __init__(self, action: str, path_expr: ASTNode, content_expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.action = action  # "write" or "append"
        self.path_expr = path_expr
        self.content_expr = content_expr

    def __repr__(self):
        return f"FileActionStmt({self.action} {self.path_expr})"


class ReadExpr(ASTNode):
    """read <path>"""
    def __init__(self, path_expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.path_expr = path_expr

    def __repr__(self):
        return f"ReadExpr({self.path_expr})"


class BeepStmt(ASTNode):
    """beep <freq>, <duration>"""
    def __init__(self, freq_expr: ASTNode, dur_expr: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.freq_expr = freq_expr
        self.dur_expr = dur_expr

    def __repr__(self):
        return f"BeepStmt({self.freq_expr}, {self.dur_expr})"


class WindowsAppActionStmt(ASTNode):
    """launch <app>, close <app>, open <path>"""
    def __init__(self, verb: str, target: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.verb = verb.lower()
        self.target = target

    def __repr__(self):
        return f"WindowsAppActionStmt({self.verb} {self.target})"


class RunningExpr(ASTNode):
    """running <app_name>"""
    def __init__(self, target: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.target = target

    def __repr__(self):
        return f"RunningExpr({self.target})"


class NovaActionStmt(ASTNode):
    """Native OS actions: play, notify, note, remind, research, flush ram"""
    def __init__(self, verb: str, args: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.verb = verb.lower()
        self.args = args

    def __repr__(self):
        return f"NovaActionStmt({self.verb}, args={self.args})"


class ExprStmt(ASTNode):
    def __init__(self, expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.expr = expr

    def __repr__(self):
        return f"ExprStmt({self.expr})"


# Expressions
class BinaryOp(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.left} {self.op} {self.right})"


class UnaryOp(ASTNode):
    def __init__(self, op: str, operand: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.op} {self.operand})"


class Literal(ASTNode):
    def __init__(self, value: Any, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.value = value

    def __repr__(self):
        return f"Literal({repr(self.value)})"


class Variable(ASTNode):
    def __init__(self, name: str, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name

    def __repr__(self):
        return f"Variable({self.name})"


class RoutineCall(ASTNode):
    def __init__(self, name: str, args: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.args = args

    def __repr__(self):
        return f"RoutineCall({self.name}({self.args}))"


class ListExpr(ASTNode):
    def __init__(self, items: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.items = items

    def __repr__(self):
        return f"ListExpr({self.items})"


class AskExpr(ASTNode):
    def __init__(self, prompt_expr: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.prompt_expr = prompt_expr

    def __repr__(self):
        return f"AskExpr({self.prompt_expr})"


class CpuExpr(ASTNode):
    def __init__(self, line: int = 1, col: int = 1):
        super().__init__(line, col)

    def __repr__(self):
        return "CpuExpr()"


class RamExpr(ASTNode):
    def __init__(self, line: int = 1, col: int = 1):
        super().__init__(line, col)

    def __repr__(self):
        return "RamExpr()"


# =============================================================================
# Parser Implementation
# =============================================================================

class Parser:
    """Forgiving recursive-descent parser for the Pajama language."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def match(self, *token_types) -> bool:
        if self.current().type in token_types:
            self.advance()
            return True
        return False

    def skip_newlines(self):
        while self.current().type == TokenType.NEWLINE:
            self.advance()

    def error(self, msg: str):
        tok = self.current()
        raise SyntaxError(f"Pajama Syntax Error [line {tok.line}, col {tok.column}]: {msg}")

    def parse(self) -> Program:
        statements: List[ASTNode] = []
        self.skip_newlines()

        while self.current().type != TokenType.EOF:
            try:
                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
            except Exception:
                # Forgiving: skip malformed line to next NEWLINE or EOF
                while self.current().type not in (TokenType.NEWLINE, TokenType.EOF):
                    self.advance()
            self.skip_newlines()

        return Program(statements)

    def parse_statement(self) -> Optional[ASTNode]:
        self.skip_newlines()
        tok = self.current()

        if tok.type == TokenType.EOF:
            return None

        # Forgiving: skip stray indents or dedents at statement level
        if tok.type in (TokenType.INDENT, TokenType.DEDENT):
            self.advance()
            return None

        # Forgiving: skip 'end', 'end if', 'end repeat', 'end while', 'pass', 'break', 'continue'
        if tok.type == TokenType.IDENTIFIER and tok.value.lower() in ("end", "pass", "break", "continue"):
            self.advance()
            if self.current().type in (TokenType.IF, TokenType.REPEAT, TokenType.WHILE, TokenType.ROUTINE) or (
                self.current().type == TokenType.IDENTIFIER and self.current().value.lower() in ("if", "repeat", "while", "routine", "for", "loop")
            ):
                self.advance()
            return None

        # Forgiving: skip label headers like 'stopwatch:' or 'monitor_memory:'
        if tok.type == TokenType.IDENTIFIER and self.peek().type == TokenType.COLON:
            self.advance()
            self.advance()
            return None

        # say <expr>
        if tok.type == TokenType.SAY:
            return self.parse_say()

        # set <var> to <expr>
        if tok.type == TokenType.SET:
            return self.parse_set()

        # increase / decrease <var> by <amount>
        if tok.type in (TokenType.INCREASE, TokenType.DECREASE):
            return self.parse_change()

        # if <cond>:
        if tok.type == TokenType.IF:
            return self.parse_if()

        # repeat <n> times:
        if tok.type == TokenType.REPEAT:
            return self.parse_repeat()

        # while <cond>:
        if tok.type == TokenType.WHILE:
            return self.parse_while()

        # for each <item> in <list>:
        if tok.type == TokenType.FOR:
            return self.parse_for_each()

        # wait <num> seconds
        if tok.type == TokenType.WAIT:
            return self.parse_wait()

        # routine <name>(<args>):
        if tok.type == TokenType.ROUTINE:
            return self.parse_routine_def()

        # give <expr> / return <expr>
        if tok.type == TokenType.GIVE:
            return self.parse_give()

        # Stopwatch Action: stopwatch / timer
        if tok.type == TokenType.STOPWATCH:
            st_tok = self.advance()
            return NovaActionStmt("stopwatch", [], st_tok.line, st_tok.column)

        # Beep Action: beep <freq>, <duration>
        if tok.type == TokenType.BEEP:
            b_tok = self.advance()
            freq_expr = self.parse_expression()
            dur_expr = None
            if self.match(TokenType.COMMA):
                dur_expr = self.parse_expression()
            # Optional 'seconds' or 's'
            while self.current().type == TokenType.IDENTIFIER and self.current().value.lower() in ("seconds", "second", "s", "sec"):
                self.advance()
            return BeepStmt(freq_expr, dur_expr, b_tok.line, b_tok.column)

        # File Actions: write / append
        if tok.type in (TokenType.WRITE, TokenType.APPEND):
            act_tok = self.advance()
            action = act_tok.value.lower()
            path_expr = self.parse_expression()
            self.match(TokenType.COMMA)
            content_expr = self.parse_expression()
            return FileActionStmt(action, path_expr, content_expr, act_tok.line, act_tok.column)

        # Windows App Actions: launch, close, open
        if tok.type in (TokenType.LAUNCH, TokenType.CLOSE, TokenType.OPEN):
            verb_tok = self.advance()
            target_expr = self.parse_expression()
            return WindowsAppActionStmt(verb_tok.value, target_expr, verb_tok.line, verb_tok.column)

        # Native actions: play, notify, note, remind, research, flush
        if tok.type in (TokenType.PLAY, TokenType.NOTIFY, TokenType.NOTE, TokenType.REMIND, TokenType.RESEARCH, TokenType.FLUSH):
            return self.parse_nova_action()

        # Identifier assignments: name = <expr> or function calls
        if tok.type == TokenType.IDENTIFIER:
            # Lookahead for assignment: name = ...
            if self.peek().type == TokenType.ASSIGN:
                ident_tok = self.advance()
                self.advance()  # eat '='
                expr = self.parse_expression()
                return AssignStmt(ident_tok.value, expr, ident_tok.line, ident_tok.column)

        # Fallback to expression statement
        expr = self.parse_expression()
        return ExprStmt(expr, tok.line, tok.column)

    def parse_say(self) -> SayStmt:
        start_tok = self.advance()  # eat 'say'
        # Support optional parentheses: say("Hello") or say "Hello"
        has_paren = False
        if self.current().type == TokenType.LPAREN:
            has_paren = True
            self.advance()

        expr = self.parse_expression()

        if has_paren and self.current().type == TokenType.RPAREN:
            self.advance()

        return SayStmt(expr, start_tok.line, start_tok.column)

    def parse_set(self) -> AssignStmt:
        start_tok = self.advance()  # eat 'set'
        if self.current().type != TokenType.IDENTIFIER:
            self.error("Expected variable name after 'set'")
        var_name = self.advance().value

        if self.current().type != TokenType.TO:
            self.error("Expected 'to' after variable name in 'set' statement")
        self.advance()  # eat 'to'

        expr = self.parse_expression()
        return AssignStmt(var_name, expr, start_tok.line, start_tok.column)

    def parse_change(self) -> ChangeStmt:
        op_tok = self.advance()  # 'increase' or 'decrease'
        op_name = op_tok.value.lower()

        if self.current().type != TokenType.IDENTIFIER:
            self.error(f"Expected variable name after '{op_name}'")
        var_name = self.advance().value

        # Optional 'by'
        if self.current().type == TokenType.BY:
            self.advance()

        amount = self.parse_expression()
        return ChangeStmt(var_name, op_name, amount, op_tok.line, op_tok.column)

    def parse_wait(self) -> WaitStmt:
        start_tok = self.advance()  # eat 'wait' or 'sleep'
        # Optional lparen
        has_paren = self.match(TokenType.LPAREN)
        sec_expr = self.parse_expression()
        if has_paren:
            self.match(TokenType.RPAREN)

        # Forgiving: consume all occurrences of 'seconds', 'second', 'sec', 's'
        while self.current().type == TokenType.IDENTIFIER and self.current().value.lower() in ("seconds", "second", "s", "sec"):
            self.advance()

        return WaitStmt(sec_expr, start_tok.line, start_tok.column)

    def parse_nova_action(self) -> NovaActionStmt:
        verb_tok = self.advance()
        verb = verb_tok.value.lower()

        # Handle 'flush ram' or 'flush memory'
        if verb == "flush":
            if self.current().type in (TokenType.RAM, TokenType.IDENTIFIER):
                sub = self.advance()
                return NovaActionStmt("flush", [Literal(sub.value, verb_tok.line, verb_tok.column)], verb_tok.line, verb_tok.column)
            return NovaActionStmt("flush", [Literal("ram", verb_tok.line, verb_tok.column)], verb_tok.line, verb_tok.column)

        # Other actions take arguments: play "sound", notify "title", "text", etc.
        args: List[ASTNode] = []
        has_paren = self.match(TokenType.LPAREN)

        if self.current().type not in (TokenType.NEWLINE, TokenType.EOF, TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())

        if has_paren:
            self.match(TokenType.RPAREN)

        return NovaActionStmt(verb, args, verb_tok.line, verb_tok.column)

    def parse_block(self) -> List[ASTNode]:
        """Parses a suite of statements, handling INDENT/DEDENT, { }, or single line."""
        body: List[ASTNode] = []
        self.skip_newlines()

        # Optional curly braces { ... }
        if self.match(TokenType.LBRACE):
            self.skip_newlines()
            while self.current().type not in (TokenType.RBRACE, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()
            self.match(TokenType.RBRACE)
            return body

        # Standard indentation block
        if self.match(TokenType.INDENT):
            self.skip_newlines()
            while self.current().type not in (TokenType.DEDENT, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
                self.skip_newlines()
            self.match(TokenType.DEDENT)
            return body

        # Single statement on same or next line
        stmt = self.parse_statement()
        if stmt:
            body.append(stmt)
        return body

    def parse_if(self) -> IfStmt:
        start_tok = self.advance()  # eat 'if'
        condition = self.parse_expression()
        self.match(TokenType.COLON)  # Optional colon

        body = self.parse_block()
        branches: List[Tuple[ASTNode, List[ASTNode]]] = [(condition, body)]
        otherwise_branch: Optional[List[ASTNode]] = None

        while True:
            self.skip_newlines()
            # Check for 'otherwise if' or 'otherwise'
            if self.current().type == TokenType.OTHERWISE:
                self.advance()  # eat 'otherwise'
                if self.current().type == TokenType.IF:
                    self.advance()  # eat 'if'
                    cond = self.parse_expression()
                    self.match(TokenType.COLON)
                    b = self.parse_block()
                    branches.append((cond, b))
                else:
                    self.match(TokenType.COLON)
                    otherwise_branch = self.parse_block()
                    break
            else:
                break

        return IfStmt(branches, otherwise_branch, start_tok.line, start_tok.column)

    def parse_repeat(self) -> RepeatStmt:
        start_tok = self.advance()  # eat 'repeat'
        count_expr = self.parse_expression()
        if self.current().type == TokenType.TIMES:
            self.advance()
        self.match(TokenType.COLON)

        body = self.parse_block()
        return RepeatStmt(count_expr, body, start_tok.line, start_tok.column)

    def parse_while(self) -> WhileStmt:
        start_tok = self.advance()  # eat 'while'
        cond = self.parse_expression()
        self.match(TokenType.COLON)

        body = self.parse_block()
        return WhileStmt(cond, body, start_tok.line, start_tok.column)

    def parse_for_each(self) -> ForEachStmt:
        start_tok = self.advance()  # eat 'for'
        # Optional 'each'
        self.match(TokenType.EACH)

        if self.current().type != TokenType.IDENTIFIER:
            self.error("Expected item variable name in 'for each' loop")
        var_name = self.advance().value

        if self.current().type != TokenType.IN:
            self.error("Expected 'in' after variable in 'for each' loop")
        self.advance()

        iterable = self.parse_expression()
        self.match(TokenType.COLON)

        body = self.parse_block()
        return ForEachStmt(var_name, iterable, body, start_tok.line, start_tok.column)

    def parse_routine_def(self) -> RoutineDef:
        start_tok = self.advance()  # eat 'routine', 'def', 'function'
        if self.current().type != TokenType.IDENTIFIER:
            self.error("Expected routine name")
        name = self.advance().value

        params: List[str] = []
        if self.match(TokenType.LPAREN):
            if self.current().type == TokenType.IDENTIFIER:
                params.append(self.advance().value)
                while self.match(TokenType.COMMA):
                    if self.current().type == TokenType.IDENTIFIER:
                        params.append(self.advance().value)
                    else:
                        break
            self.match(TokenType.RPAREN)

        self.match(TokenType.COLON)
        body = self.parse_block()
        return RoutineDef(name, params, body, start_tok.line, start_tok.column)

    def parse_give(self) -> GiveStmt:
        start_tok = self.advance()  # eat 'give' or 'return'
        if self.current().type in (TokenType.NEWLINE, TokenType.EOF, TokenType.DEDENT):
            return GiveStmt(None, start_tok.line, start_tok.column)
        expr = self.parse_expression()
        return GiveStmt(expr, start_tok.line, start_tok.column)

    # -------------------------------------------------------------------------
    # Expression Parsing (Precedence Climbing)
    # -------------------------------------------------------------------------

    def parse_expression(self) -> ASTNode:
        return self.parse_logical_or()

    def parse_logical_or(self) -> ASTNode:
        left = self.parse_logical_and()
        while self.current().type == TokenType.OR:
            op = self.advance().value
            right = self.parse_logical_and()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_logical_and(self) -> ASTNode:
        left = self.parse_equality()
        while self.current().type == TokenType.AND:
            op = self.advance().value
            right = self.parse_equality()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_equality(self) -> ASTNode:
        left = self.parse_comparison()
        while self.current().type in (TokenType.EQ, TokenType.NEQ, TokenType.IS):
            tok = self.advance()
            op = tok.value
            if tok.type == TokenType.IS:
                if self.match(TokenType.NOT):
                    op = "!="
                else:
                    op = "=="
            right = self.parse_comparison()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_comparison(self) -> ASTNode:
        left = self.parse_additive()
        while self.current().type in (TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op = self.advance().value
            right = self.parse_additive()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_unary()
        while self.current().type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self.advance().value
            right = self.parse_unary()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_unary(self) -> ASTNode:
        if self.current().type in (TokenType.MINUS, TokenType.NOT):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOp(op, operand, operand.line, operand.col)
        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        tok = self.current()

        # Literals
        if tok.type in (TokenType.NUMBER, TokenType.STRING, TokenType.BOOLEAN, TokenType.NONE):
            self.advance()
            return Literal(tok.value, tok.line, tok.column)

        # OS Keywords
        if tok.type == TokenType.CPU:
            self.advance()
            return CpuExpr(tok.line, tok.column)

        if tok.type == TokenType.RAM:
            self.advance()
            return RamExpr(tok.line, tok.column)

        # read <path>
        if tok.type == TokenType.READ:
            self.advance()
            path_expr = self.parse_primary()
            return ReadExpr(path_expr, tok.line, tok.column)

        # running <app_name>
        if tok.type == TokenType.RUNNING:
            self.advance()
            target = self.parse_primary()
            return RunningExpr(target, tok.line, tok.column)

        # ask <prompt>
        if tok.type == TokenType.ASK:
            self.advance()
            prompt = None
            if self.current().type not in (TokenType.NEWLINE, TokenType.EOF, TokenType.RPAREN, TokenType.COMMA):
                prompt = self.parse_expression()
            return AskExpr(prompt, tok.line, tok.column)

        # List literal [a, b, c]
        if self.match(TokenType.LBRACKET):
            items: List[ASTNode] = []
            if self.current().type != TokenType.RBRACKET:
                items.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    if self.current().type == TokenType.RBRACKET:
                        break
                    items.append(self.parse_expression())
            self.match(TokenType.RBRACKET)
            return ListExpr(items, tok.line, tok.column)

        # Grouping (expr)
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.match(TokenType.RPAREN)
            return expr

        # Identifiers and Routine Calls
        if tok.type == TokenType.IDENTIFIER:
            self.advance()
            # Function / Routine Call
            if self.match(TokenType.LPAREN):
                args: List[ASTNode] = []
                if self.current().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        if self.current().type == TokenType.RPAREN:
                            break
                        args.append(self.parse_expression())
                self.match(TokenType.RPAREN)
                return RoutineCall(tok.value, args, tok.line, tok.column)

            return Variable(tok.value, tok.line, tok.column)

        # Forgiving: consume stray delimiter or indentation instead of crashing
        if tok.type in (TokenType.INDENT, TokenType.DEDENT, TokenType.NEWLINE, TokenType.COLON, TokenType.EOF):
            self.advance()
            return Literal(None, tok.line, tok.column)

        bad_tok = self.advance()
        return Literal(bad_tok.value, bad_tok.line, bad_tok.column)


def parse_pajama(source: str) -> Program:
    """Convenience helper: lexes and parses Pajama source code into an AST."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()
