"""
The PAJAMA Programming Language for NOVA OS.
Simpler, friendlier, and more forgiving than Python.
"""

from nova.pajama.spec import PAJAMA_LANGUAGE_DOCS, AI_PAJAMA_SYSTEM_PROMPT
from nova.pajama.lexer import Lexer, Token, TokenType
from nova.pajama.parser import Parser, parse_pajama
from nova.pajama.runtime import PajamaInterpreter, execute_pajama, Environment
from nova.pajama.ai_assistant import PajamaAIAssistant, PAJAMA_PRESET_TEMPLATES

__all__ = [
    "PAJAMA_LANGUAGE_DOCS",
    "AI_PAJAMA_SYSTEM_PROMPT",
    "Lexer",
    "Token",
    "TokenType",
    "Parser",
    "parse_pajama",
    "PajamaInterpreter",
    "execute_pajama",
    "Environment",
    "PajamaAIAssistant",
    "PAJAMA_PRESET_TEMPLATES",
]
