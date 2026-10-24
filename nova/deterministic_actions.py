"""
NOVA OS Deterministic Actions Engine.
Executes instant local calculations, unit conversions, and system directives
without needing heavy LLM inference, ensuring zero lag on Intel Core i3 / 4 GB RAM.
"""

import math
import ast
import operator
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Safe Math AST Evaluator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e,
}

def evaluate_math_expression(expr: str) -> Optional[float]:
    """Safely evaluates a basic mathematical expression using AST parsing."""
    try:
        clean_expr = expr.strip().replace("^", "**")
        node = ast.parse(clean_expr, mode='eval').body

        def _eval(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type in SAFE_OPERATORS:
                    return SAFE_OPERATORS[op_type](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type in SAFE_OPERATORS:
                    return SAFE_OPERATORS[op_type](_eval(node.operand))
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
                    args = [_eval(a) for a in node.args]
                    return SAFE_FUNCTIONS[node.func.id](*args)
            elif isinstance(node, ast.Name):
                if node.id in SAFE_FUNCTIONS:
                    return SAFE_FUNCTIONS[node.id]
            raise ValueError("Unsupported syntax")

        result = _eval(node)
        if isinstance(result, (int, float)):
            return round(result, 6) if isinstance(result, float) and result % 1 != 0 else result
        return None
    except Exception:
        return None

def evaluate_deterministic_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Evaluates a query string and returns an instant result if deterministic.
    Returns None if the query should be handled by LLM or search.
    """
    q = query.strip()
    q_lower = q.lower()

    # 1. Date & Time queries
    if q_lower in ["time", "current time", "what time is it", "clock"]:
        now = datetime.now().strftime("%I:%M:%S %p")
        return {"type": "clock", "title": "CURRENT TIME", "result": now, "icon": "🕒"}

    if q_lower in ["date", "today", "what date is it", "today's date"]:
        today = datetime.now().strftime("%A, %B %d, %Y")
        return {"type": "date", "title": "TODAY'S DATE", "result": today, "icon": "📅"}

    # 2. Mathematical evaluation
    # Quick check if it looks like math (contains numbers and operators)
    has_operator = any(op in q for op in ["+", "-", "*", "/", "^", "%", "sqrt", "sin", "cos", "pi"])
    has_digit = any(c.isdigit() for c in q)
    if has_operator and has_digit and not q_lower.startswith(("http", "note", "remind", "term")):
        res = evaluate_math_expression(q)
        if res is not None:
            return {
                "type": "calc",
                "title": f"CALCULATION: {q}",
                "result": f"{q} = {res}",
                "icon": "🔢",
                "value": str(res)
            }

    # 3. Unit conversions (Storage & Temperature)
    # e.g., "16 gb to mb", "100 c to f"
    tokens = q_lower.split()
    if len(tokens) == 4 and tokens[2] in ["to", "in"]:
        try:
            val = float(tokens[0])
            u_from = tokens[1]
            u_to = tokens[3]
            # Storage
            storage_units = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
            if u_from in storage_units and u_to in storage_units:
                bytes_val = val * storage_units[u_from]
                converted = round(bytes_val / storage_units[u_to], 2)
                return {
                    "type": "unit",
                    "title": "UNIT CONVERSION",
                    "result": f"{val} {u_from.upper()} = {converted} {u_to.upper()}",
                    "icon": "📐"
                }
            # Temperature
            if u_from in ["c", "celsius"] and u_to in ["f", "fahrenheit"]:
                f_val = round((val * 9/5) + 32, 2)
                return {"type": "unit", "title": "TEMPERATURE", "result": f"{val}°C = {f_val}°F", "icon": "🌡"}
            if u_from in ["f", "fahrenheit"] and u_to in ["c", "celsius"]:
                c_val = round((val - 32) * 5/9, 2)
                return {"type": "unit", "title": "TEMPERATURE", "result": f"{val}°F = {c_val}°C", "icon": "🌡"}
        except Exception:
            pass

    return None
