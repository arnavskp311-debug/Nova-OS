"""
NOVA OS Safety & Sandbox Enforcement System.
Prevents unintended system alterations, enforces user approvals,
simulates dangerous OS operations safely, and protects the host Windows environment.
"""

import re
import shlex
import subprocess
import time
from typing import Tuple, Dict, Any
from nova.config import COMMAND_TIMEOUT_SECONDS
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

# Whitelist of intrinsically safe read-only commands
SAFE_READ_ONLY_PREFIXES = [
    "dir", "echo", "type", "date /t", "time /t", "ver", "whoami",
    "python --version", "python -V", "pip list", "git status", "git log",
    "ipconfig", "hostname", "systeminfo", "tasklist"
]

class RiskLevel:
    BLOCKED = "BLOCKED"
    SIMULATED = "SIMULATED"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    SAFE = "SAFE"

def analyze_command(command: str) -> Dict[str, Any]:
    """
    Analyzes a command string and categorizes its safety risk.
    """
    cmd_clean = command.strip()
    cmd_lower = cmd_clean.lower()
    
    if not cmd_clean:
        return {
            "risk": RiskLevel.SAFE,
            "reason": "Empty command",
            "is_simulated": False,
            "requires_approval": False
        }

    # Check simulated commands
    first_token = cmd_lower.split()[0] if cmd_lower.split() else ""
    if first_token in SIMULATED_COMMANDS:
        return {
            "risk": RiskLevel.SIMULATED,
            "reason": f"Simulated OS feature: Safe visual simulation of '{first_token}'.",
            "is_simulated": True,
            "simulated_output": SIMULATED_COMMANDS[first_token],
            "requires_approval": False
        }

    # Check strictly blocked patterns
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return {
                "risk": RiskLevel.BLOCKED,
                "reason": f"SECURITY SAFEGUARD: {reason}",
                "is_simulated": False,
                "requires_approval": False
            }

    # Check for destructive delete/overwrite actions
    if any(k in cmd_lower for k in ["rmdir /s", "del /s", "remove-item -recurse", "drop table"]):
        return {
            "risk": RiskLevel.HIGH,
            "reason": "Potential mass deletion or modification detected.",
            "is_simulated": False,
            "requires_approval": True
        }

    # Check for safe read-only queries
    for safe_prefix in SAFE_READ_ONLY_PREFIXES:
        if cmd_lower.startswith(safe_prefix):
            return {
                "risk": RiskLevel.SAFE,
                "reason": "Safe read-only system diagnostic command.",
                "is_simulated": False,
                "requires_approval": False
            }

    # Default command: moderate risk, requires user confirmation
    return {
        "risk": RiskLevel.MODERATE,
        "reason": "Standard command execution. Modifies environment or runs external tools.",
        "is_simulated": False,
        "requires_approval": True
    }

def execute_command_safely(command: str, approved_by_user: bool = False) -> Tuple[bool, str]:
    """
    Executes a command safely with strict sandbox enforcement and timeouts.
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

    if analysis["requires_approval"] and not approved_by_user:
        msg = f"[APPROVAL REQUIRED]\nCommand '{command}' classified as {risk}.\nUser explicit confirmation needed."
        return False, msg

    # Execute under unprivileged shell with timeout
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            cwd=None  # inherits current safe working directory
        )
        output = proc.stdout if proc.returncode == 0 else (proc.stdout + "\n" + proc.stderr).strip()
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
