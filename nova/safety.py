"""
NOVA OS Safety & Sandbox Enforcement System.
Prevents unintended system alterations, enforces strict security boundaries,
executes safe read-only diagnostics via pure Python, and protects the host Windows environment.
"""

import os
import re
import shlex
import shutil
import subprocess
import time
import socket
import getpass
import platform
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from nova.config import COMMAND_TIMEOUT_SECONDS, BASE_DIR
from nova.database import log_command

# Strictly BLOCKED patterns that could harm host Windows OS
BLOCKED_PATTERNS = [
    (r"\bformat\b", "Formatting drives/partitions is blocked."),
    (r"\bdiskpart\b", "Disk partition manipulation is blocked."),
    (r"\bbcdedit\b", "Modifying Windows Boot Configuration is blocked."),
    (r"\breg\s+(delete|add|import|restore|load)", "Direct Windows registry manipulation is blocked."),
    (r"\b(sfc|dism)\b", "Windows system file modifications are blocked."),
    (r"\b(vssadmin|wbadmin)\b", "Shadow copy / backup manipulation is blocked."),
    (r"\btakeown\b", "System ownership alterations are blocked."),
    (r"\bicacls\b.*\b(grant|deny|reset)", "Host security ACL modifications are blocked."),
    (r"\bdel\s+(/[a-z]\s+)*[a-z]:\\windows", "Deleting files in Windows directory is strictly blocked."),
    (r"\bdel\s+(/[a-z]\s+)*[a-z]:\\", "Root drive file deletion is blocked."),
    (r"\brmdir\s+/[sq]\s+[a-z]:\\", "Root drive directory deletion is blocked."),
    (r"\bRemove-Item\s+.*[a-z]:\\windows", "PowerShell Windows folder alteration is blocked."),
    (r"\bnet\s+user\b", "User account modifications are blocked."),
    (r"\bnetsh\s+firewall\b", "Firewall security modifications are blocked."),
    (r"\bfltmc\b", "Filter driver manipulations are blocked."),
    (r"\b(curl|wget|certutil|bitsadmin)\b.*http", "Unsanctioned remote payload download is blocked."),
    (r"\bpowershell\b.*(-enc|-encodedcommand|bypass)", "Encoded PowerShell execution is blocked."),
]

# Patterns for simulated OS commands that provide cyberpunk OS feel without touching Windows
SIMULATED_COMMANDS = {
    "shutdown": "NOVA OS [SIMULATION]: Powering down quantum cores... All virtual subsystems halted safely.",
    "reboot": "NOVA OS [SIMULATION]: Soft reboot initiated... Virtual memory cycle complete. NOVA OS reinitialized.",
    "poweroff": "NOVA OS [SIMULATION]: Neural link disconnected. Safe virtual standby engaged.",
    "kernel-upgrade": "NOVA OS [SIMULATION]: Synthetic AI kernel upgraded to v2.6.4-cyber (In-Memory Simulation).",
    "clear-cache": "NOVA OS [SIMULATION]: Transient memory buffers purged successfully.",
    "kill-virus": "NOVA OS [SIMULATION]: Neural scanner executed: 0 threats detected in trial sandbox.",
}

# Forbidden shell metacharacters and command chaining operators
SHELL_METACHART_PATTERN = re.compile(r"([&|;`$<>\n\r]|\b2>|\b>>)")

# Sensitive paths and credential protection
SENSITIVE_FILES_PATTERN = re.compile(
    r"(cookies|login data|web data|history|passwords|credentials|\.ssh|\.aws|\.env|id_rsa|appdata\\local\\google\\chrome)",
    re.IGNORECASE
)

# Intrinsically safe diagnostic commands handled directly by Python
SAFE_PYTHON_DIAGNOSTICS = {
    "whoami", "hostname", "ver", "os", "date /t", "date", "time /t", "time",
    "python --version", "python -v", "pip list", "systeminfo"
}

# Whitelist of external tools allowed for read-only invocation via subprocess (shell=False)
ALLOWED_READONLY_TOOLS = {
    "git": {"status", "log", "diff", "branch", "show", "rev-parse", "--version"},
    "ipconfig": {"/all", "/displaydns"},
    "tasklist": {"/fo", "/nh", "/v", "/fi"},
}

class RiskLevel:
    BLOCKED = "BLOCKED"
    SIMULATED = "SIMULATED"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    SAFE = "SAFE"


def execute_python_diagnostic(command_clean: str) -> Optional[str]:
    """
    Executes intrinsically safe system diagnostics directly using Python's standard library,
    completely bypassing shell or subprocess invocations.
    """
    cmd_lower = command_clean.lower().strip()
    if cmd_lower == "whoami":
        return getpass.getuser()
    elif cmd_lower == "hostname":
        return socket.gethostname()
    elif cmd_lower in ["ver", "os"]:
        return f"Microsoft Windows [{platform.version()}]"
    elif cmd_lower in ["date /t", "date"]:
        return datetime.now().strftime("%a %m/%d/%Y")
    elif cmd_lower in ["time /t", "time"]:
        return datetime.now().strftime("%I:%M %p")
    elif cmd_lower in ["python --version", "python -v"]:
        return f"Python {platform.python_version()}"
    elif cmd_lower == "pip list":
        try:
            import importlib.metadata
            pkgs = sorted([f"{dist.metadata['Name']} ({dist.version})" for dist in importlib.metadata.distributions()])
            return "\n".join(pkgs[:50]) + ("\n... [output truncated]" if len(pkgs) > 50 else "")
        except Exception:
            return "pip list diagnostic unavailable."
    elif cmd_lower == "systeminfo":
        try:
            import psutil
            cores_phys = psutil.cpu_count(logical=False) or 1
            cores_log = psutil.cpu_count(logical=True) or 1
            ram = psutil.virtual_memory()
            lines = [
                f"Host Name:                 {platform.node()}",
                f"OS Name:                   Microsoft Windows {platform.release()}",
                f"OS Version:                {platform.version()}",
                f"OS Architecture:           {platform.machine()}",
                f"Processor(s):              {cores_phys} Physical / {cores_log} Logical Cores",
                f"Total Physical Memory:     {round(ram.total / (1024**3), 2)} GB",
                f"Available Physical Memory: {round(ram.available / (1024**3), 2)} GB",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Systeminfo unavailable: {e}"
    elif cmd_lower.startswith("echo"):
        # Pure Python echo
        parts = command_clean.split(maxsplit=1)
        return parts[1] if len(parts) > 1 else ""
    elif cmd_lower == "dir" or cmd_lower.startswith("dir "):
        # Pure Python directory listing strictly within project sandbox
        try:
            parts = shlex.split(command_clean, posix=False)
            target_arg = next((p for p in parts[1:] if not p.startswith("/")), ".")
            target_path = Path(target_arg)
            resolved = (BASE_DIR / target_path).resolve() if not target_path.is_absolute() else target_path.resolve()
            if not resolved.is_relative_to(BASE_DIR.resolve()):
                return "SECURITY SAFEGUARD: Directory listing outside NOVA project sandbox is blocked."
            if not resolved.exists():
                return f"Path not found: {resolved}"
            lines = [f" Directory of {resolved}\n"]
            for item in sorted(resolved.iterdir()):
                itype = "<DIR>" if item.is_dir() else "     "
                size = f"{item.stat().st_size:,}" if item.is_file() else ""
                lines.append(f"{itype}  {size:>12}  {item.name}")
            return "\n".join(lines)
        except Exception as e:
            return f"Directory listing error: {e}"
    return None


def analyze_command(command: str) -> Dict[str, Any]:
    """
    Parses and analyzes a command string, rejecting chaining, shell operators,
    sensitive files, and unverified executables.
    """
    cmd_clean = command.strip()
    if not cmd_clean:
        return {
            "risk": RiskLevel.SAFE,
            "reason": "Empty command",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": []
        }

    # 1. Reject command chaining, shell metacharacters, and redirection
    if SHELL_METACHART_PATTERN.search(cmd_clean):
        return {
            "risk": RiskLevel.BLOCKED,
            "reason": "SECURITY SAFEGUARD: Command chaining, shell redirection, pipes, and metacharacters (&, |, ;, `, $, <, >) are strictly blocked.",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": []
        }

    # 2. Reject sensitive path / browser credential access
    if SENSITIVE_FILES_PATTERN.search(cmd_clean):
        return {
            "risk": RiskLevel.BLOCKED,
            "reason": "SECURITY SAFEGUARD: Access to protected credentials, passwords, or browser profiles is strictly blocked.",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": []
        }

    cmd_lower = cmd_clean.lower()

    # 3. Check simulated OS commands
    first_word = cmd_lower.split()[0] if cmd_lower.split() else ""
    if first_word in SIMULATED_COMMANDS:
        return {
            "risk": RiskLevel.SIMULATED,
            "reason": f"Simulated OS feature: Safe visual simulation of '{first_word}'.",
            "is_simulated": True,
            "simulated_output": SIMULATED_COMMANDS[first_word],
            "requires_approval": False,
            "tokens": [first_word]
        }

    # 4. Check strictly blocked regex patterns
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return {
                "risk": RiskLevel.BLOCKED,
                "reason": f"SECURITY SAFEGUARD: {reason}",
                "is_simulated": False,
                "requires_approval": False,
                "tokens": []
            }

    # 5. Tokenize using shlex without shell expansion
    try:
        tokens = shlex.split(cmd_clean, posix=False)
    except Exception as e:
        return {
            "risk": RiskLevel.BLOCKED,
            "reason": f"SECURITY SAFEGUARD: Malformed command syntax: {e}",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": []
        }

    if not tokens:
        return {
            "risk": RiskLevel.SAFE,
            "reason": "Empty command",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": []
        }

    # 5b. Reject path traversal and absolute path escaping project sandbox
    for t in tokens[1:]:
        if not t.startswith(("-", "/")):
            try:
                p = Path(t)
                resolved = (BASE_DIR / p).resolve() if not p.is_absolute() else p.resolve()
                if (".." in t or p.is_absolute()) and not resolved.is_relative_to(BASE_DIR.resolve()):
                    return {
                        "risk": RiskLevel.BLOCKED,
                        "reason": f"SECURITY SAFEGUARD: Path traversal outside NOVA project sandbox is strictly blocked ({t}).",
                        "is_simulated": False,
                        "requires_approval": False,
                        "tokens": tokens
                    }
            except Exception:
                pass

    # 6. Check intrinsically safe Python diagnostics
    if cmd_lower in SAFE_PYTHON_DIAGNOSTICS or cmd_lower.startswith("echo ") or cmd_lower == "dir" or cmd_lower.startswith("dir "):
        if cmd_lower == "dir" or cmd_lower.startswith("dir "):
            target_arg = next((p for p in tokens[1:] if not p.startswith("/")), ".")
            try:
                target_path = Path(target_arg)
                resolved_target = (BASE_DIR / target_path).resolve() if not target_path.is_absolute() else target_path.resolve()
                if not resolved_target.is_relative_to(BASE_DIR.resolve()):
                    return {
                        "risk": RiskLevel.BLOCKED,
                        "reason": f"SECURITY SAFEGUARD: Directory traversal outside project sandbox is strictly blocked ({resolved_target}).",
                        "is_simulated": False,
                        "requires_approval": False,
                        "tokens": tokens
                    }
            except Exception:
                return {
                    "risk": RiskLevel.BLOCKED,
                    "reason": "SECURITY SAFEGUARD: Invalid directory path argument.",
                    "is_simulated": False,
                    "requires_approval": False,
                    "tokens": tokens
                }
        return {
            "risk": RiskLevel.SAFE,
            "reason": "Safe read-only system diagnostic handled via pure Python.",
            "is_simulated": False,
            "requires_approval": False,
            "tokens": tokens,
            "is_python_diagnostic": True
        }

    # 7. Check allowed external read-only tools
    exe_name = tokens[0].lower()
    if exe_name.endswith(".exe"):
        exe_name = exe_name[:-4]

    if exe_name in ALLOWED_READONLY_TOOLS:
        allowed_subcommands = ALLOWED_READONLY_TOOLS[exe_name]
        # If tool requires subcommands (like git)
        if allowed_subcommands:
            if len(tokens) > 1 and any(sub in allowed_subcommands for sub in tokens[1:]):
                return {
                    "risk": RiskLevel.SAFE,
                    "reason": f"Permitted read-only diagnostic utility: {exe_name}.",
                    "is_simulated": False,
                    "requires_approval": False,
                    "tokens": tokens,
                    "is_python_diagnostic": False
                }
            elif len(tokens) == 1:
                return {
                    "risk": RiskLevel.SAFE,
                    "reason": f"Permitted diagnostic utility: {exe_name}.",
                    "is_simulated": False,
                    "requires_approval": False,
                    "tokens": tokens,
                    "is_python_diagnostic": False
                }
        else:
            return {
                "risk": RiskLevel.SAFE,
                "reason": f"Permitted diagnostic utility: {exe_name}.",
                "is_simulated": False,
                "requires_approval": False,
                "tokens": tokens,
                "is_python_diagnostic": False
            }

    # 8. Check for destructive delete/overwrite actions
    if any(k in cmd_lower for k in ["rmdir /s", "del /s", "remove-item -recurse", "drop table", "rmdir", "del "]):
        return {
            "risk": RiskLevel.HIGH,
            "reason": "Potential mass deletion or modification detected.",
            "is_simulated": False,
            "requires_approval": True,
            "tokens": tokens
        }

    # 9. Default command: moderate risk, requires explicit user confirmation
    return {
        "risk": RiskLevel.MODERATE,
        "reason": "Standard command execution. Modifies environment or runs external tools.",
        "is_simulated": False,
        "requires_approval": True,
        "tokens": tokens
    }


def execute_command_safely(command: str, approved_by_user: bool = False, source: str = "terminal") -> Tuple[bool, str]:
    """
    Executes a command safely with strict sandbox enforcement, no shell=True, and bounded timeouts.
    Returns (success, output).
    """
    analysis = analyze_command(command)
    risk = analysis["risk"]

    if risk == RiskLevel.BLOCKED:
        msg = f"[BLOCKED BY NOVA OS SAFETY CORE]\n{analysis['reason']}\nNo system changes were performed."
        log_command(command, risk, "BLOCKED", msg, approved=False)
        return False, msg

    if analysis["is_simulated"]:
        sim_out = analysis.get("simulated_output", "Simulation complete.")
        log_command(command, risk, "SIMULATED", sim_out, approved=True)
        return True, sim_out

    # 1. Pure Python Diagnostics (instant, zero subprocess, zero shell)
    if analysis.get("is_python_diagnostic", False):
        diag_output = execute_python_diagnostic(command)
        if diag_output is not None:
            log_command(command, risk, "SUCCESS", diag_output, approved=True)
            return True, diag_output

    if analysis["requires_approval"] and not approved_by_user:
        msg = f"[APPROVAL REQUIRED]\nCommand '{command}' classified as {risk}.\nUser explicit confirmation needed."
        return False, msg

    tokens = analysis.get("tokens", [])
    if not tokens:
        tokens = shlex.split(command.strip(), posix=False)

    if not tokens:
        return False, "[Empty command]"

    # Safe mkdir handling inside project directory
    first_token = tokens[0].lower()
    if first_token in ["mkdir", "md"] and len(tokens) > 1:
        target = Path(tokens[1])
        try:
            target_path = (BASE_DIR / target).resolve()
            # Ensure path does not escape project directory
            if not str(target_path).startswith(str(BASE_DIR.resolve())):
                return False, "[BLOCKED] Cannot create directory outside project sandbox."
            target_path.mkdir(parents=True, exist_ok=True)
            out = f"Directory created: {target_path.name}"
            log_command(command, risk, "SUCCESS", out, approved=approved_by_user)
            return True, out
        except Exception as e:
            out = f"[ERROR] mkdir failed: {e}"
            log_command(command, risk, "ERROR", out, approved=approved_by_user)
            return False, out

    # Locate executable binary
    exe = shutil.which(tokens[0])
    if not exe:
        # Check standard Windows System32
        sys32 = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32"
        candidate = sys32 / f"{tokens[0]}.exe"
        if candidate.exists():
            exe = str(candidate)
        else:
            msg = f"[ERROR] Command or executable not found: '{tokens[0]}'."
            log_command(command, risk, "NOT_FOUND", msg, approved=approved_by_user)
            return False, msg

    # Execute strictly with shell=False
    try:
        proc = subprocess.run(
            [exe] + tokens[1:],
            shell=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cwd=str(BASE_DIR)
        )
        output = proc.stdout if proc.returncode == 0 else (proc.stdout + "\n" + proc.stderr).strip()
        # Bound output length to avoid memory bloat
        if len(output) > 50000:
            output = output[:50000] + "\n... [Output truncated at 50,000 characters]"
        if not output:
            output = f"[Process completed with return code {proc.returncode}]"

        status = "SUCCESS" if proc.returncode == 0 else f"EXIT_{proc.returncode}"
        log_command(command, risk, status, output, approved=approved_by_user)
        return (proc.returncode == 0), output

    except subprocess.TimeoutExpired:
        out = f"[TIMEOUT] Command exceeded safe execution threshold ({COMMAND_TIMEOUT_SECONDS}s)."
        log_command(command, risk, "TIMEOUT", out, approved=approved_by_user)
        return False, out
    except Exception as e:
        out = f"[ERROR] Execution failed: {str(e)}"
        log_command(command, risk, "ERROR", out, approved=approved_by_user)
        return False, out
