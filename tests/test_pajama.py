"""
PAJAMA LANGUAGE & AI INTEGRATION TEST SUITE.
Validates the Lexer, Parser, AST, Sandboxed Runtime, Auto-Coercion,
OS Superpowers, AI Assistant, and Studio Widget.
"""

import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ['QT_QPA_PLATFORM'] = 'offscreen' 

from nova.pajama.lexer import Lexer, TokenType
from nova.pajama.parser import (
    parse_pajama, Program, SayStmt, AssignStmt, ChangeStmt,
    IfStmt, RepeatStmt, RoutineDef, GiveStmt, NovaActionStmt
)
from nova.pajama.runtime import PajamaInterpreter, execute_pajama
from nova.pajama.ai_assistant import PajamaAIAssistant, PAJAMA_PRESET_TEMPLATES


class TestPajamaLexer(unittest.TestCase):
    """Verifies token generation, comments, and forgiving indentation."""

    def test_keywords_and_literals(self):
        source = 'say "Hello" set count to 10 increase count by 1 cpu ram'
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected = [
            TokenType.SAY, TokenType.STRING,
            TokenType.SET, TokenType.IDENTIFIER, TokenType.TO, TokenType.NUMBER,
            TokenType.INCREASE, TokenType.IDENTIFIER, TokenType.BY, TokenType.NUMBER,
            TokenType.CPU, TokenType.RAM
        ]
        self.assertEqual(types, expected)

    def test_comments_c_and_python_style(self):
        source = (
            '// Single line comment\n'
            'say "Action" # Python style comment\n'
            '/* Multi line\n'
            '   block comment */\n'
            'say "Finished"\n'
        )
        tokens = Lexer(source).tokenize()
        string_tokens = [t.value for t in tokens if t.type == TokenType.STRING]
        self.assertEqual(string_tokens, ["Action", "Finished"])

    def test_indentation_tracking(self):
        source = (
            "if cpu > 10:\n"
            "    say \"High\"\n"
            "say \"Done\"\n"
        )
        tokens = Lexer(source).tokenize()
        types = [t.type for t in tokens if t.type in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(types, [TokenType.INDENT, TokenType.DEDENT])


class TestPajamaParser(unittest.TestCase):
    """Verifies Abstract Syntax Tree construction."""

    def test_parse_say_and_assign(self):
        ast = parse_pajama('say "Cyber"\nx = 42\n')
        self.assertEqual(len(ast.statements), 2)
        self.assertIsInstance(ast.statements[0], SayStmt)
        self.assertIsInstance(ast.statements[1], AssignStmt)
        self.assertEqual(ast.statements[1].name, "x")

    def test_parse_increase_decrease(self):
        ast = parse_pajama('increase energy by 10\ndecrease energy by 2\n')
        self.assertEqual(len(ast.statements), 2)
        self.assertIsInstance(ast.statements[0], ChangeStmt)
        self.assertEqual(ast.statements[0].op, "increase")
        self.assertEqual(ast.statements[1].op, "decrease")

    def test_parse_routine_and_repeat(self):
        source = (
            "routine multiply(a, b):\n"
            "    give a * b\n"
            "repeat 3 times:\n"
            "    say count\n"
        )
        ast = parse_pajama(source)
        self.assertEqual(len(ast.statements), 2)
        self.assertIsInstance(ast.statements[0], RoutineDef)
        self.assertEqual(ast.statements[0].name, "multiply")
        self.assertIsInstance(ast.statements[1], RepeatStmt)


class TestPajamaRuntime(unittest.TestCase):
    """Verifies execution, auto-coercion, and zero-import OS primitives."""

    def test_auto_string_coercion_no_type_error(self):
        # Python raises TypeError for "Count: " + 5
        # Pajama must smoothly coerce without any error!
        source = (
            'count = 5\n'
            'say "Count is: " + count\n'
            'say 10 + " items remaining"\n'
        )
        output = execute_pajama(source)
        self.assertIn("Count is: 5", output)
        self.assertIn("10 items remaining", output)

    def test_loops_and_routines(self):
        source = (
            "routine cube(x):\n"
            "    give x * x * x\n"
            "repeat 3 times:\n"
            "    say \"Step \" + count + \": \" + cube(count)\n"
        )
        output = execute_pajama(source)
        self.assertIn("Step 1: 1", output)
        self.assertIn("Step 2: 8", output)
        self.assertIn("Step 3: 27", output)

    def test_os_keywords_cpu_and_ram(self):
        source = (
            'say "Host CPU: " + cpu\n'
            'say "Host RAM: " + ram\n'
        )
        output = execute_pajama(source)
        self.assertIn("Host CPU:", output)
        self.assertIn("Host RAM:", output)

    def test_nova_actions(self):
        source = (
            'play "chime"\n'
            'notify "Test Alert", "Message text"\n'
            'flush ram\n'
        )
        output = execute_pajama(source)
        self.assertIn("[Sound played: chime]", output)
        self.assertIn("[Notification: Test Alert - Message text]", output)
        self.assertTrue("flushed" in output.lower() or "trimmed" in output.lower())

    def test_forgiving_conditionals(self):
        source = (
            "score = 85\n"
            "if score > 90:\n"
            "    say \"A\"\n"
            "otherwise if score > 80:\n"
            "    say \"B\"\n"
            "otherwise:\n"
            "    say \"C\"\n"
        )
        output = execute_pajama(source)
        self.assertEqual(output.strip(), "B")

    def test_file_io_beep_and_stopwatch(self):
        source = (
            'write "pajama_unit_test.txt", "Hello Sandbox"\n'
            'append "pajama_unit_test.txt", " 2026"\n'
            'data = read "pajama_unit_test.txt"\n'
            'say "READ: " + data\n'
            'beep 440, 0.05\n'
        )
        output = execute_pajama(source)
        self.assertIn("READ: Hello Sandbox 2026", output)
        self.assertIn("[Beep: 440Hz, 50ms]", output)


class TestPajamaAIAssistant(unittest.TestCase):
    """Verifies the AI generation, explanation, and debugging pipelines."""

    def setUp(self):
        self.assistant = PajamaAIAssistant()

    def test_generate_code_offline_fallback(self):
        # Directly test offline deterministic synthesizer
        offline_code = self.assistant._generate_offline_fallback("Monitor memory and flush if RAM is over 75%")
        self.assertIn("ram", offline_code.lower())
        self.assertIn("flush", offline_code.lower())
        output = execute_pajama(offline_code)
        self.assertTrue(len(output) > 0)

        # Test live / fallback generate_code
        code = self.assistant.generate_code("Check system health")
        self.assertTrue(len(code) > 0)

    def test_explain_code(self):
        code = "say 'Hello'\nif ram > 80:\n    flush ram\n"
        explanation = self.assistant.explain_code(code)
        self.assertTrue(len(explanation) > 0)
        self.assertTrue("pajama" in explanation.lower() or "hello" in explanation.lower() or "ram" in explanation.lower())

    def test_fix_code_from_python_syntax(self):
        # User mistakenly writes Python 'print' or 'def' or 'return'
        py_code = "def test():\n    print('Hello')\n    return 42\n"
        fixed = self.assistant.fix_code(py_code, "Syntax error")
        self.assertIn("say", fixed)
        self.assertTrue("routine" in fixed or "give" in fixed)

    def test_preset_templates_availability(self):
        templates = self.assistant.get_templates()
        self.assertIn("System Health Guardian", templates)
        self.assertIn("Loop & Routine Demo", templates)
        # Verify all templates execute without raising syntax errors
        for name, tmpl in templates.items():
            ast = parse_pajama(tmpl)
            self.assertTrue(len(ast.statements) > 0, f"Template {name} parsed 0 statements")


class TestPajamaStudioWidget(unittest.TestCase):
    """Verifies that Pajama Studio IDE initializes in Qt environment."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            cls.app = QApplication(sys.argv + ["-platform", "offscreen"])
        else:
            cls.app = QApplication.instance()

    def test_widget_instantiation(self):
        from nova.ui.widgets.pajama_studio import PajamaStudioWidget
        widget = PajamaStudioWidget()
        self.assertIsNotNone(widget.editor)
        self.assertIsNotNone(widget.console)
        self.assertIsNotNone(widget.btn_generate)
        # Check initial text loaded
        self.assertTrue(len(widget.editor.toPlainText()) > 0)
        widget.cleanup()


if __name__ == "__main__":
    unittest.main()
