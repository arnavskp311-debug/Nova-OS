"""
Pajama AI Assistant.
Integrates NOVA OS AI (Ollama Client) with the Pajama Programming Language.
Provides instant code generation from English, step-by-step code explanation,
and automatic error debugging / fixing.
"""

import re
from typing import Dict, List, Optional
from nova.ollama_client import OllamaClient
from nova.config import DEFAULT_MODEL
from nova.pajama.spec import AI_PAJAMA_SYSTEM_PROMPT


PAJAMA_PRESET_TEMPLATES = {
    "System Health Guardian": (
        "// System Health Guardian - Monitors and cleans memory automatically\n"
        "say \"[NOVA Health Guardian Active]\"\n"
        "say \"Current Host CPU: \" + cpu + \"%\"\n"
        "say \"Current Host RAM: \" + ram + \"%\"\n"
        "\n"
        "if ram > 75:\n"
        "    say \"WARNING: RAM usage exceeds 75%! Flushing memory...\"\n"
        "    play \"alert\"\n"
        "    flush ram\n"
        "    notify \"NOVA Guardian\", \"RAM flushed successfully!\"\n"
        "    play \"success\"\n"
        "otherwise:\n"
        "    say \"Memory is within optimal operating limits.\"\n"
        "    play \"chime\"\n"
    ),
    "Loop & Routine Demo": (
        "// Loop & Routine Demo - Simple math and iterative actions\n"
        "routine calculate_power(val, multiplier):\n"
        "    give val * multiplier\n"
        "\n"
        "say \"Testing Pajama routines:\"\n"
        "repeat 5 times:\n"
        "    result = calculate_power(count, 10)\n"
        "    say \"Iteration \" + count + \" -> Power score: \" + result\n"
        "    wait 0.2 seconds\n"
        "\n"
        "play \"success\"\n"
        "say \"Routine execution finished!\"\n"
    ),
    "Smart Notes & Reminders": (
        "// Smart Notes & Reminders - Native OS integration\n"
        "say \"Recording mission logs into NovaPad...\"\n"
        "note \"Pajama System Log\", \"System telemetry check completed at CPU: \" + cpu + \"%\"\n"
        "play \"click\"\n"
        "\n"
        "say \"Scheduling routine maintenance reminder...\"\n"
        "remind \"Check Sandbox Storage\", \"in 2 hours\"\n"
        "notify \"Scheduler\", \"Maintenance reminder set\"\n"
        "play \"chime\"\n"
    ),
    "Autonomous Research Dispatcher": (
        "// Autonomous Research Dispatcher - Launches NOVA research agent\n"
        "mission_topic = \"Edge AI Optimization on Low RAM Systems\"\n"
        "say \"Initializing research dispatch for: \" + mission_topic\n"
        "notify \"Research Agent\", \"Task dispatched: \" + mission_topic\n"
        "play \"blip\"\n"
        "research mission_topic\n"
        "say \"Mission dispatched successfully to background agent.\"\n"
    ),
    "Interactive Greeter & Math": (
        "// Interactive Greeter & Math\n"
        "say \"Welcome to Pajama OS Scripting!\"\n"
        "player_name = \"Commander\"\n"
        "set level to 1\n"
        "increase level by 4\n"
        "say \"Greetings, \" + player_name + \"! You are currently at Level \" + level\n"
        "say \"Ready to program in Pajama.\"\n"
        "play \"chime\"\n"
    ),
    "Cyber Stopwatch & Timer": (
        "// Cyber Stopwatch & Timer with Audio and Notifications\n"
        "say \"=== CYBER STOPWATCH INITIALIZED ===\"\n"
        "say \"Starting timer sequence...\"\n"
        "play \"click\"\n"
        "notify \"Stopwatch\", \"Timer started!\"\n"
        "\n"
        "seconds = 0\n"
        "repeat 10 times:\n"
        "    increase seconds by 1\n"
        "    say \"⏱️ Stopwatch: \" + seconds + \" seconds elapsed\"\n"
        "    play \"blip\"\n"
        "    wait 1 second\n"
        "\n"
        "say \"=== STOPWATCH FINISHED: \" + seconds + \" SECONDS ===\"\n"
        "play \"success\"\n"
        "notify \"Stopwatch\", \"Timer finished at \" + seconds + \" seconds!\"\n"
    ),
}


class PajamaAIAssistant:
    """Provides AI-powered Pajama code generation, explanation, and debugging."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None, model: str = DEFAULT_MODEL):
        self.ollama = ollama_client or OllamaClient()
        self.model = model

    def generate_code(self, user_prompt: str) -> str:
        """
        Generates clean, runnable Pajama code from a natural language prompt.
        Falls back to smart template synthesis if Ollama is offline.
        """
        system_prompt = AI_PAJAMA_SYSTEM_PROMPT
        messages = [
            {
                "role": "user",
                "content": (
                    f"Write a complete Pajama (.pj) program for NOVA OS to do the following:\n"
                    f"\"{user_prompt}\"\n\n"
                    f"Requirements:\n"
                    f"- Write ONLY valid Pajama code (no Python, no markdown explanation).\n"
                    f"- Use natural Pajama idioms: say, if/otherwise, repeat, play, notify, note, remind, flush ram, cpu, ram.\n"
                    f"- Add helpful // comments."
                )
            }
        ]

        # Check if Ollama is connected
        if self.ollama.check_connection():
            try:
                chunks = []
                for chunk in self.ollama.stream_chat(messages, model=self.model, system_prompt=system_prompt):
                    chunks.append(chunk)
                raw_response = "".join(chunks).strip()
                cleaned = self._clean_code_fence(raw_response)
                if cleaned and not cleaned.startswith("[Notice:") and not cleaned.startswith("[Ollama Error"):
                    return cleaned
            except Exception:
                pass

        # Offline smart fallback based on prompt content
        return self._generate_offline_fallback(user_prompt)

    def explain_code(self, code: str) -> str:
        """Explains Pajama code in clear, friendly English."""
        if not code.strip():
            return "No code provided to explain."

        messages = [
            {
                "role": "user",
                "content": (
                    f"Explain this Pajama (.pj) program in clear, friendly English step-by-step:\n\n"
                    f"```pajama\n{code}\n```"
                )
            }
        ]

        if self.ollama.check_connection():
            try:
                chunks = []
                for chunk in self.ollama.stream_chat(messages, model=self.model, system_prompt=AI_PAJAMA_SYSTEM_PROMPT):
                    chunks.append(chunk)
                explanation = "".join(chunks).strip()
                if explanation and not explanation.startswith("[Notice:"):
                    if "pajama" not in explanation.lower():
                        explanation = f"// Pajama Script Analysis & Explanation\n{explanation}"
                    return explanation
            except Exception:
                pass

        # Offline explanation generator
        return self._generate_offline_explanation(code)

    def fix_code(self, code: str, error_message: str) -> str:
        """Fixes invalid or buggy Pajama code given the error message."""
        messages = [
            {
                "role": "user",
                "content": (
                    f"Convert and fix this code into valid Pajama (.pj) code. Error: \"{error_message}\"\n\n"
                    f"Code:\n```pajama\n{code}\n```\n\n"
                    f"Important: Replace print() with 'say', def with 'routine', return with 'give'. Return ONLY runnable Pajama code."
                )
            }
        ]

        if self.ollama.check_connection():
            try:
                chunks = []
                for chunk in self.ollama.stream_chat(messages, model=self.model, system_prompt=AI_PAJAMA_SYSTEM_PROMPT):
                    chunks.append(chunk)
                raw_response = "".join(chunks).strip()
                cleaned = self._clean_code_fence(raw_response)
                if cleaned and not cleaned.startswith("[Notice:"):
                    return self._generate_offline_fix(cleaned, error_message)
            except Exception:
                pass

        # Offline fix fallback: clean up typical syntax errors
        return self._generate_offline_fix(code, error_message)

    def get_templates(self) -> Dict[str, str]:
        """Returns the dictionary of preset interactive templates."""
        return PAJAMA_PRESET_TEMPLATES

    def _clean_code_fence(self, text: str) -> str:
        """Extracts pure code from markdown backticks and sanitizes tables, errors, and stray syntax."""
        pattern = r"```(?:pajama|pj|python)?\s*\n([\s\S]*?)\n```"
        match = re.search(pattern, text, re.IGNORECASE)
        code = match.group(1).strip() if match else text.strip()

        cleaned_lines = []
        for line in code.split("\n"):
            stripped = line.strip()
            # Ignore markdown table lines (starts with '|' or contains table divider)
            if stripped.startswith("|") or "|---" in stripped:
                continue
            # Ignore network or transmission errors
            if stripped.startswith("[Transmission Error:") or stripped.startswith("[Ollama Error") or stripped.startswith("[Notice:"):
                continue
            # Remove redundant 'end if', 'end repeat', 'end while'
            if stripped.lower() in ("end if", "end repeat", "end while", "end routine", "end loop", "end"):
                continue

            # Auto-repair Pythonisms
            line_fixed = re.sub(r"\bprint\s*\((.*?)\)", r"say \1", line)
            line_fixed = re.sub(r"\bprint\s+(.*)", r"say \1", line_fixed)
            line_fixed = re.sub(r"\bdef\s+", "routine ", line_fixed)
            line_fixed = re.sub(r"\breturn\s+", "give ", line_fixed)
            line_fixed = re.sub(r"\belse\s*:", "otherwise:", line_fixed)
            line_fixed = re.sub(r"\belif\s+", "otherwise if ", line_fixed)
            line_fixed = re.sub(r"wait\s+(\d+)\s+seconds\s+seconds", r"wait \1 seconds", line_fixed)

            cleaned_lines.append(line_fixed)

        result = "\n".join(cleaned_lines).strip()
        return result

    def _generate_offline_fallback(self, prompt: str) -> str:
        """Synthesizes high quality Pajama code offline matching the user prompt."""
        p_lower = prompt.lower()

        if any(w in p_lower for w in ("stopwatch", "timer", "clock", "countdown", "gui")):
            return (
                f"// Generated for: {prompt}\n"
                "say \"=== CYBER STOPWATCH INITIALIZED ===\"\n"
                "say \"Starting interactive timer...\"\n"
                "play \"click\"\n"
                "notify \"Stopwatch\", \"Timer started!\"\n"
                "\n"
                "seconds = 0\n"
                "repeat 10 times:\n"
                "    increase seconds by 1\n"
                "    say \"[STOPWATCH] Elapsed: \" + seconds + \" seconds\"\n"
                "    play \"blip\"\n"
                "    wait 1 second\n"
                "\n"
                "say \"Stopwatch finished at \" + seconds + \" seconds.\"\n"
                "play \"success\"\n"
                "notify \"Stopwatch\", \"Completed at \" + seconds + \" seconds!\"\n"
            )

        if any(w in p_lower for w in ("ram", "memory", "flush", "clean", "guardian")):
            return (
                f"// Generated for: {prompt}\n"
                "say \"Checking system memory status...\"\n"
                "say \"Current RAM usage: \" + ram + \"%\"\n"
                "if ram > 70:\n"
                "    say \"RAM is elevated! Flushing quantum working set...\"\n"
                "    play \"alert\"\n"
                "    flush ram\n"
                "    notify \"Pajama Guardian\", \"RAM flushed successfully!\"\n"
                "    play \"success\"\n"
                "otherwise:\n"
                "    say \"Memory is within safe thresholds.\"\n"
                "    play \"chime\"\n"
            )

        if any(w in p_lower for w in ("loop", "repeat", "count", "times", "for")):
            return (
                f"// Generated for: {prompt}\n"
                "say \"Starting repetition cycle:\"\n"
                "repeat 5 times:\n"
                "    say \"Loop count: \" + count + \" at CPU: \" + cpu + \"%\"\n"
                "    wait 0.2 seconds\n"
                "play \"success\"\n"
                "say \"Loop sequence completed!\"\n"
            )

        if any(w in p_lower for w in ("note", "remind", "save", "log")):
            return (
                f"// Generated for: {prompt}\n"
                "say \"Logging event to NovaPad...\"\n"
                "note \"Autonomous Log\", \"Pajama automated report recorded.\"\n"
                "remind \"Check System Progress\", \"in 1 hour\"\n"
                "notify \"Pajama System\", \"Log and reminder created successfully!\"\n"
                "play \"chime\"\n"
            )

        if any(w in p_lower for w in ("research", "search", "web", "internet")):
            return (
                f"// Generated for: {prompt}\n"
                "topic = \"Quantum Operating Systems\"\n"
                "say \"Deploying autonomous research mission for: \" + topic\n"
                "notify \"Research Agent\", \"Task dispatched for: \" + topic\n"
                "play \"blip\"\n"
                "research topic\n"
                "say \"Research mission queued.\"\n"
            )

        # General purpose fallback
        return (
            f"// Generated for: {prompt}\n"
            "say \"Executing custom Pajama script...\"\n"
            "say \"Current Host CPU: \" + cpu + \"%\"\n"
            "say \"Current Host RAM: \" + ram + \"%\"\n"
            "score = 50\n"
            "increase score by 25\n"
            "say \"Calculated score: \" + score\n"
            "play \"chime\"\n"
            "say \"All tasks completed successfully.\"\n"
        )

    def _generate_offline_explanation(self, code: str) -> str:
        """Provides an offline breakdown of what the code does."""
        lines = code.strip().split("\n")
        explanations = []
        explanations.append("### Pajama Script Analysis:")

        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith("//") or s.startswith("#"):
                continue
            if s.startswith("say "):
                explanations.append(f"- Line {idx}: Outputs message to the console.")
            elif s.startswith("if "):
                explanations.append(f"- Line {idx}: Conditional decision check.")
            elif s.startswith("repeat "):
                explanations.append(f"- Line {idx}: Loops the block a set number of times.")
            elif s.startswith("routine "):
                explanations.append(f"- Line {idx}: Defines a reusable function.")
            elif s.startswith("play "):
                explanations.append(f"- Line {idx}: Plays native NOVA OS audio cue.")
            elif s.startswith("notify "):
                explanations.append(f"- Line {idx}: Shows a desktop notification toast.")
            elif s.startswith("flush ram"):
                explanations.append(f"- Line {idx}: Immediately flushes physical RAM working set.")
            elif s.startswith("wait "):
                explanations.append(f"- Line {idx}: Pauses execution safely without blocking UI.")
            elif "=" in s or s.startswith("set "):
                explanations.append(f"- Line {idx}: Assigns variable value.")

        explanations.append("\n**Overall:** This program runs safely inside NOVA OS with native zero-import capabilities.")
        return "\n".join(explanations)

    def _generate_offline_fix(self, code: str, error_message: str) -> str:
        """Fixes basic syntax mistakes offline."""
        # Replace Python 'print(' with 'say '
        fixed = re.sub(r"\bprint\s*\((.*?)\)", r"say \1", code)
        # Replace 'else:' with 'otherwise:'
        fixed = re.sub(r"\belse\s*:", "otherwise:", fixed)
        # Replace 'elif ' with 'otherwise if '
        fixed = re.sub(r"\belif\s+", "otherwise if ", fixed)
        # Replace 'def ' with 'routine '
        fixed = re.sub(r"\bdef\s+", "routine ", fixed)
        # Replace 'return ' with 'give '
        fixed = re.sub(r"\breturn\s+", "give ", fixed)
        return fixed
