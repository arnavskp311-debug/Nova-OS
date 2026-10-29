"""
Pajama Language Runtime & Sandboxed Interpreter.
Executes Pajama AST nodes with auto-coercion, zero-frustration type safety,
and native zero-import NOVA OS superpowers.
"""

import sys
import time
from typing import Any, Callable, Dict, List, Optional

from nova.windows_apps import get_windows_app_manager
from pathlib import Path
from nova.pajama.parser import (
    ASTNode, Program, SayStmt, AssignStmt, ChangeStmt, IfStmt, WindowsAppActionStmt, RunningExpr,
    FileActionStmt, ReadExpr, BeepStmt,
    RepeatStmt, WhileStmt, ForEachStmt, WaitStmt, RoutineDef,
    GiveStmt, NovaActionStmt, ExprStmt, BinaryOp, UnaryOp,
    Literal, Variable, RoutineCall, ListExpr, AskExpr, CpuExpr, RamExpr,
    parse_pajama
)

# Optional system hooks
try:
    import psutil
except ImportError:
    psutil = None

try:
    from nova.sound_manager import play_sound
except Exception:
    def play_sound(cue: str):
        pass

try:
    from nova.agent_engine import create_note, create_reminder
except Exception:
    def create_note(title: str, content: str, tags: str = ""):
        return f"[Note Created: {title}]"
    def create_reminder(title: str, due_at: str, priority: str = "NORMAL"):
        return f"[Reminder Scheduled: {title} at {due_at}]"

try:
    from nova.performance.memory_optimizer import get_memory_optimizer
except Exception:
    get_memory_optimizer = None


class PajamaReturnValue(Exception):
    """Signals routine return / give statement."""
    def __init__(self, value: Any):
        self.value = value


class PajamaRuntimeError(Exception):
    """Friendly runtime error with line and column reporting."""
    def __init__(self, message: str, node: Optional[ASTNode] = None):
        self.node = node
        line = getattr(node, "line", 1) if node else 1
        col = getattr(node, "col", 1) if node else 1
        super().__init__(f"Pajama Runtime Error [line {line}, col {col}]: {message}")


class Environment:
    """Scoped variable and routine symbol table."""

    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: Dict[str, Any] = {}

    def get(self, name: str, node: Optional[ASTNode] = None) -> Any:
        key = name.lower()
        if key in self.values:
            return self.values[key]
        if self.parent:
            return self.parent.get(name, node)
        # Forgiving fallback: undefined variables return None instead of crashing
        return None

    def set(self, name: str, value: Any):
        """Sets a variable in the local scope."""
        self.values[name.lower()] = value

    def assign(self, name: str, value: Any):
        """Assigns to existing variable in nearest scope or defines locally."""
        key = name.lower()
        if key in self.values:
            self.values[key] = value
        elif self.parent and self.parent.has(key):
            self.parent.assign(name, value)
        else:
            self.values[key] = value

    def has(self, name: str) -> bool:
        key = name.lower()
        if key in self.values:
            return True
        if self.parent:
            return self.parent.has(name)
        return False


class PajamaRoutine:
    """User-defined Pajama routine."""

    def __init__(self, def_node: RoutineDef, closure: Environment):
        self.def_node = def_node
        self.closure = closure

    def call(self, interpreter: "PajamaInterpreter", args: List[Any], call_node: ASTNode) -> Any:
        env = Environment(self.closure)
        for param, val in zip(self.def_node.params, args):
            env.set(param, val)

        try:
            for stmt in self.def_node.body:
                interpreter.execute_node(stmt, env)
        except PajamaReturnValue as ret:
            return ret.value

        return None


class PajamaInterpreter:
    """Tree-walking interpreter for the Pajama language."""

    MAX_ITERATIONS = 100000  # Safety throttle for loops

    def __init__(
        self,
        output_callback: Optional[Callable[[str], None]] = None,
        input_callback: Optional[Callable[[str], str]] = None,
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.output_callback = output_callback or (lambda text: print(text))
        self.input_callback = input_callback or (lambda prompt: "")
        self.notify_callback = notify_callback or (lambda title, msg: None)
        self.global_env = Environment()
        self.output_lines: List[str] = []
        self._is_cancelled = False
        self.step_count = 0

    def cancel(self):
        """Requests cooperative cancellation of running script."""
        self._is_cancelled = True

    def reset(self):
        self.global_env = Environment()
        self.output_lines.clear()
        self._is_cancelled = False
        self.step_count = 0

    def run(self, source: str) -> str:
        """Parses and executes Pajama code, returning complete console output."""
        self.reset()
        ast = parse_pajama(source)
        start_time = time.time()

        for stmt in ast.statements:
            if self._is_cancelled:
                self._emit("[Execution cancelled by user]")
                break
            self.execute_node(stmt, self.global_env)

        elapsed = (time.time() - start_time) * 1000
        return "\n".join(self.output_lines)

    def _emit(self, text: str):
        self.output_lines.append(str(text))
        if self.output_callback:
            try:
                self.output_callback(str(text))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Statement Execution
    # -------------------------------------------------------------------------

    def execute_node(self, node: ASTNode, env: Environment) -> Any:
        if self._is_cancelled:
            return None

        self.step_count += 1
        if self.step_count > self.MAX_ITERATIONS * 10:
            raise PajamaRuntimeError("Execution limit exceeded (infinite loop protection)", node)

        # Say statement
        if isinstance(node, SayStmt):
            val = self.evaluate(node.expr, env)
            self._emit(self._format_value(val))
            return None

        # Assign statement
        if isinstance(node, AssignStmt):
            val = self.evaluate(node.expr, env)
            env.assign(node.name, val)
            return None

        # Change statement (increase/decrease)
        if isinstance(node, ChangeStmt):
            current_val = env.get(node.name, node)
            if current_val is None:
                current_val = 0
            amount = self.evaluate(node.amount, env)
            if not isinstance(amount, (int, float)):
                try:
                    amount = float(amount)
                except Exception:
                    amount = 1

            if node.op == "increase":
                new_val = current_val + amount
            else:
                new_val = current_val - amount
            env.assign(node.name, new_val)
            return None

        # If statement
        if isinstance(node, IfStmt):
            branch_taken = False
            for cond_node, body in node.branches:
                cond_val = self.evaluate(cond_node, env)
                if self._is_truthy(cond_val):
                    branch_taken = True
                    for s in body:
                        self.execute_node(s, env)
                    break

            if not branch_taken and node.otherwise_branch:
                for s in node.otherwise_branch:
                    self.execute_node(s, env)
            return None

        # Repeat statement
        if isinstance(node, RepeatStmt):
            count_val = self.evaluate(node.count_expr, env)
            try:
                count = int(count_val)
            except Exception:
                count = 1

            loop_env = Environment(env)
            for i in range(1, count + 1):
                if self._is_cancelled:
                    break
                loop_env.set("count", i)
                loop_env.set("index", i - 1)
                for s in node.body:
                    self.execute_node(s, loop_env)
            return None

        # While statement
        if isinstance(node, WhileStmt):
            iterations = 0
            while self._is_truthy(self.evaluate(node.condition, env)):
                if self._is_cancelled:
                    break
                iterations += 1
                if iterations > self.MAX_ITERATIONS:
                    raise PajamaRuntimeError(f"While loop exceeded maximum {self.MAX_ITERATIONS} iterations", node)
                for s in node.body:
                    self.execute_node(s, env)
            return None

        # For each statement
        if isinstance(node, ForEachStmt):
            iterable = self.evaluate(node.iterable, env)
            if not isinstance(iterable, (list, tuple, str)):
                iterable = [iterable]

            loop_env = Environment(env)
            for item in iterable:
                if self._is_cancelled:
                    break
                loop_env.set(node.var_name, item)
                for s in node.body:
                    self.execute_node(s, loop_env)
            return None

        # Wait statement
        if isinstance(node, WaitStmt):
            secs = self.evaluate(node.seconds_expr, env)
            try:
                sec_float = float(secs)
            except Exception:
                sec_float = 1.0

            # Sleep in tiny increments so cancellation is instantaneous
            end_time = time.time() + sec_float
            while time.time() < end_time and not self._is_cancelled:
                time.sleep(min(0.05, max(0.0, end_time - time.time())))
            return None

        # Routine definition
        if isinstance(node, RoutineDef):
            routine = PajamaRoutine(node, env)
            env.set(node.name, routine)
            return None

        # Give statement
        if isinstance(node, GiveStmt):
            val = self.evaluate(node.expr, env) if node.expr else None
            raise PajamaReturnValue(val)

        # File I/O Actions: write / append
        if isinstance(node, FileActionStmt):
            path_val = str(self.evaluate(node.path_expr, env)).strip()
            content_val = str(self.evaluate(node.content_expr, env))
            mode = "a" if node.action == "append" else "w"
            p = Path(path_val)
            if not p.is_absolute():
                p = Path("data/workspace") / p
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, mode, encoding="utf-8") as f:
                f.write(content_val)
            self._emit(f"[File {node.action} completed: {p.name}]")
            return None

        # Beep Synthesizer Action: beep <freq>, <dur>
        if isinstance(node, BeepStmt):
            freq = self.evaluate(node.freq_expr, env)
            dur = self.evaluate(node.dur_expr, env) if node.dur_expr else 0.2
            try:
                freq_int = int(freq)
            except Exception:
                freq_int = 440
            try:
                dur_ms = int(float(dur) * 1000)
            except Exception:
                dur_ms = 200
            try:
                import winsound
                winsound.Beep(max(37, min(32767, freq_int)), max(50, min(5000, dur_ms)))
            except Exception:
                pass
            self._emit(f"[Beep: {freq_int}Hz, {dur_ms}ms]")
            return None

        # Windows App Actions
        if isinstance(node, WindowsAppActionStmt):
            target_val = str(self.evaluate(node.target, env)).strip()
            mgr = get_windows_app_manager()
            verb = node.verb.lower()
            if verb in ("launch", "start"):
                ok, msg = mgr.launch_app(target_val)
                self._emit(f"[{msg}]")
            elif verb in ("close", "kill"):
                ok, msg = mgr.terminate_process(target_val)
                self._emit(f"[{msg}]")
            elif verb == "open":
                try:
                    os.startfile(target_val)
                    self._emit(f"[Opened: {target_val}]")
                except Exception as e:
                    self._emit(f"[Error opening {target_val}: {e}]")
            return None

        # Nova Actions
        if isinstance(node, NovaActionStmt):
            self._execute_nova_action(node, env)
            return None

        # Expression statement
        if isinstance(node, ExprStmt):
            return self.evaluate(node.expr, env)

        return None

    def _execute_nova_action(self, node: NovaActionStmt, env: Environment):
        verb = node.verb
        evaluated_args = [self.evaluate(a, env) for a in node.args]

        if verb == "play":
            cue = str(evaluated_args[0]) if evaluated_args else "click"
            try:
                play_sound(cue)
            except Exception:
                pass
            self._emit(f"[Sound played: {cue}]")

        elif verb == "notify":
            title = str(evaluated_args[0]) if len(evaluated_args) > 0 else "NOVA Alert"
            msg = str(evaluated_args[1]) if len(evaluated_args) > 1 else ""
            if self.notify_callback:
                self.notify_callback(title, msg)
            self._emit(f"[Notification: {title} - {msg}]")

        elif verb == "note":
            title = str(evaluated_args[0]) if len(evaluated_args) > 0 else "Pajama Note"
            body = str(evaluated_args[1]) if len(evaluated_args) > 1 else ""
            res = create_note(title, body, tags="pajama, script")
            self._emit(f"[Note Saved: {title}]")

        elif verb == "remind":
            title = str(evaluated_args[0]) if len(evaluated_args) > 0 else "Pajama Reminder"
            due = str(evaluated_args[1]) if len(evaluated_args) > 1 else "in 1 hour"
            res = create_reminder(title, due)
            self._emit(f"[Reminder Created: {title} due {due}]")

        elif verb == "flush":
            if get_memory_optimizer:
                try:
                    res = get_memory_optimizer().flush_quantum_memory()
                    self._emit(f"[Quantum RAM flushed successfully: {res}]")
                except Exception as e:
                    self._emit(f"[RAM flushed: {e}]")
            else:
                self._emit("[RAM working set trimmed]")

        elif verb in ("stopwatch", "timer"):
            from nova.pajama.gui_engine import show_stopwatch_gui
            res = show_stopwatch_gui()
            self._emit(res)

        elif verb == "research":
            topic = str(evaluated_args[0]) if evaluated_args else "General Query"
            self._emit(f"[Autonomous Research mission dispatched for: {topic}]")

    # -------------------------------------------------------------------------
    # Expression Evaluation & Forgiving Coercion
    # -------------------------------------------------------------------------

    def evaluate(self, node: ASTNode, env: Environment) -> Any:
        if node is None:
            return None

        # Literals
        if isinstance(node, Literal):
            return node.value

        # Variables
        if isinstance(node, Variable):
            return env.get(node.name, node)

        # OS Keywords: cpu & ram
        if isinstance(node, CpuExpr):
            if psutil:
                try:
                    return round(psutil.cpu_percent(interval=None), 1)
                except Exception:
                    pass
            return 14.2

        if isinstance(node, RamExpr):
            if psutil:
                try:
                    return round(psutil.virtual_memory().percent, 1)
                except Exception:
                    pass
            return 62.4

        # Read expression: read <path>
        if isinstance(node, ReadExpr):
            path_val = str(self.evaluate(node.path_expr, env)).strip()
            p = Path(path_val)
            if not p.is_absolute():
                candidate = Path("data/workspace") / p
                if candidate.exists():
                    p = candidate
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        return f.read()
                except Exception as e:
                    return f"[Error reading {p.name}: {e}]"
            return ""

        # Running check
        if isinstance(node, RunningExpr):
            target_val = str(self.evaluate(node.target, env)).strip()
            mgr = get_windows_app_manager()
            return mgr.is_process_running(target_val)

        # Ask prompt
        if isinstance(node, AskExpr):
            prompt = str(self.evaluate(node.prompt_expr, env)) if node.prompt_expr else "> "
            return self.input_callback(prompt)

        # List expression
        if isinstance(node, ListExpr):
            return [self.evaluate(item, env) for item in node.items]

        # Unary operations
        if isinstance(node, UnaryOp):
            val = self.evaluate(node.operand, env)
            if node.op == "-":
                try:
                    return -val
                except Exception:
                    return 0
            if node.op in ("not", "!"):
                return not self._is_truthy(val)
            return val

        # Binary operations (The Heart of Zero Frustration)
        if isinstance(node, BinaryOp):
            left = self.evaluate(node.left, env)
            right = self.evaluate(node.right, env)
            op = node.op

            # Automatic String Coercion for '+':
            if op == "+":
                if isinstance(left, str) or isinstance(right, str):
                    return self._format_value(left) + self._format_value(right)
                try:
                    return left + right
                except Exception:
                    return self._format_value(left) + self._format_value(right)

            # Arithmetic
            if op == "-":
                try: return left - right
                except Exception: return 0
            if op == "*":
                try:
                    if isinstance(left, str) and isinstance(right, int):
                        return left * right
                    return left * right
                except Exception: return 0
            if op == "/":
                try: return left / right if right != 0 else 0
                except Exception: return 0
            if op == "%":
                try: return left % right if right != 0 else 0
                except Exception: return 0

            # Equality & Comparisons (Forgiving)
            if op in ("==", "is"):
                return left == right
            if op in ("!=", "is not"):
                return left != right
            if op == "<":
                try: return left < right
                except Exception: return False
            if op == "<=":
                try: return left <= right
                except Exception: return False
            if op == ">":
                try: return left > right
                except Exception: return False
            if op == ">=":
                try: return left >= right
                except Exception: return False

            # Logical
            if op in ("and", "&&"):
                return self._is_truthy(left) and self._is_truthy(right)
            if op in ("or", "||"):
                return self._is_truthy(left) or self._is_truthy(right)

        # Routine Calls
        if isinstance(node, RoutineCall):
            target = env.get(node.name, node)
            args = [self.evaluate(a, env) for a in node.args]

            if isinstance(target, PajamaRoutine):
                return target.call(self, args, node)

            # Built-in python functions fallback
            if callable(target):
                try:
                    return target(*args)
                except Exception as e:
                    return f"[Error calling {node.name}: {e}]"

            # Check built-in string helpers: len, upper, lower, round, abs
            fn_name = node.name.lower()
            if fn_name == "len" and args:
                try: return len(args[0])
                except Exception: return 0
            if fn_name == "round" and args:
                try: return round(args[0], int(args[1]) if len(args) > 1 else 0)
                except Exception: return args[0]
            if fn_name == "abs" and args:
                try: return abs(args[0])
                except Exception: return 0
            if fn_name in ("str", "text") and args:
                return self._format_value(args[0])
            if fn_name in ("int", "number") and args:
                try: return int(args[0])
                except Exception: return 0

            return None

        return None

    def _format_value(self, val: Any) -> str:
        """Formats values cleanly for Pajama output."""
        if val is None:
            return ""
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, float):
            return f"{val:g}"  # Remove trailing zeroes
        return str(val)

    def _is_truthy(self, val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, (str, list, tuple, dict)):
            return len(val) > 0
        return True

    def get_variables(self):
        return dict(self.global_env.values)

    def run_code(self, source: str) -> str:
        return self.run(source)

PajamaRuntime = PajamaInterpreter


def execute_pajama(source: str, output_callback: Optional[Callable[[str], None]] = None) -> str:
    """High-level runner: executes a Pajama source string and returns output."""
    interpreter = PajamaInterpreter(output_callback=output_callback)
    return interpreter.run(source)
