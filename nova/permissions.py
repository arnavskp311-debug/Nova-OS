"""
NOVA OS Central Permission & Technical Boundary Enforcement Service.
Controls autonomous agent capabilities, validates filesystem targets,
prevents Server-Side Request Forgery (SSRF), and strictly isolates the Windows host environment.
"""

import os
import re
import socket
import logging
import ipaddress
from enum import Enum
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Set
from urllib.parse import urlparse

from nova.config import (
    BASE_DIR, WORKSPACE_DIR, PERMITTED_RESEARCH_EXTENSIONS, PROHIBITED_EXTENSIONS
)

logger = logging.getLogger("nova.permissions")


class Capability(Enum):
    """Fine-grained capability tokens for the Autonomous Agent."""
    # Permitted Autonomous Capabilities
    INTERNET_SEARCH = "internet.search"
    INTERNET_FETCH_PUBLIC = "internet.fetch_public"
    BROWSER_NAVIGATE = "browser.navigate"
    BROWSER_EXTRACT = "browser.extract"
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_WRITE = "workspace.write"
    WORKSPACE_DOWNLOAD = "workspace.download"
    VAULT_INDEX = "vault.index"
    TEST_EXECUTE_RESTRICTED = "test.execute_restricted"

    # Strictly Denied Capabilities (Hard Technical Block)
    HOST_SHELL_EXEC = "host.shell_exec"
    HOST_EXTERNAL_FS_WRITE = "host.external_fs_write"
    HOST_SYSTEM_CONFIG = "host.system_config"
    CREDENTIAL_ACCESS = "credential.access"
    CONSEQUENTIAL_ACTION = "action.consequential"


# Set of capabilities permanently granted to autonomous research tasks
AUTONOMOUS_RESEARCH_CAPABILITIES: Set[Capability] = {
    Capability.INTERNET_SEARCH,
    Capability.INTERNET_FETCH_PUBLIC,
    Capability.BROWSER_NAVIGATE,
    Capability.BROWSER_EXTRACT,
    Capability.WORKSPACE_READ,
    Capability.WORKSPACE_WRITE,
    Capability.WORKSPACE_DOWNLOAD,
    Capability.VAULT_INDEX,
    Capability.TEST_EXECUTE_RESTRICTED,
}

# Set of capabilities strictly blocked in autonomous mode without exception
STRICTLY_BLOCKED_CAPABILITIES: Set[Capability] = {
    Capability.HOST_SHELL_EXEC,
    Capability.HOST_EXTERNAL_FS_WRITE,
    Capability.HOST_SYSTEM_CONFIG,
    Capability.CREDENTIAL_ACCESS,
    Capability.CONSEQUENTIAL_ACTION,
}


class PermissionDeniedSecurityError(PermissionError):
    """Raised when an autonomous action breaches security policy boundaries."""
    pass


class PermissionEnforcer:
    """
    Centralized technical security boundary enforcement engine.
    Validates permissions, verifies network destinations against SSRF,
    and guarantees filesystem isolation.
    """

    def __init__(self, workspace_root: Path = WORKSPACE_DIR):
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def is_capability_allowed(self, capability: Capability) -> bool:
        """Evaluates if the requested capability is permitted in autonomous mode."""
        if capability in STRICTLY_BLOCKED_CAPABILITIES:
            return False
        return capability in AUTONOMOUS_RESEARCH_CAPABILITIES

    def require_permission(self, capability: Capability, target: str = "") -> None:
        """
        Enforces that a capability is permitted.
        Raises PermissionDeniedSecurityError if denied.
        """
        if not self.is_capability_allowed(capability):
            reason = f"SECURITY BREACH DETECTED: Capability '{capability.value}' is strictly blocked in autonomous mode."
            if target:
                reason += f" Target: {target}"
            logger.critical(reason)
            raise PermissionDeniedSecurityError(reason)

    def validate_fs_path(self, target_path: Path | str, mode: str = "read") -> Tuple[bool, str, Optional[Path]]:
        """
        Validates that a path is strictly confined to the dedicated research workspace.
        Protects against directory traversal, path escaping, symlink redirection, and NTFS junctions.
        Returns: (is_valid, reason, resolved_path)
        """
        try:
            raw_path = Path(target_path)
        except Exception as e:
            return False, f"Invalid path syntax: {e}", None

        # Check for obvious traversal tokens before resolution
        raw_str = str(target_path).replace("\\", "/")
        if ".." in raw_str.split("/"):
            return False, "Directory traversal ('..') detected in path.", None

        # Windows alternate data stream protection (e.g. file.txt:secret)
        if ":" in raw_path.name:
            return False, "Alternate data stream access is prohibited.", None

        # Canonicalize and resolve path
        try:
            if raw_path.is_absolute():
                resolved = raw_path.resolve()
            else:
                resolved = (self.workspace_root / raw_path).resolve()
        except Exception as e:
            return False, f"Path canonicalization failure: {e}", None

        # Ensure path is strictly relative to workspace root
        if not resolved.is_relative_to(self.workspace_root):
            return False, f"Access denied: Path '{resolved}' escapes dedicated workspace sandbox.", None

        # Verify parent exists if writing
        if mode in ("write", "download"):
            ext = resolved.suffix.lower()
            if ext in PROHIBITED_EXTENSIONS:
                return False, f"Prohibited executable or script extension: '{ext}'", None
            if ext and ext not in PERMITTED_RESEARCH_EXTENSIONS:
                return False, f"Extension '{ext}' not in permitted research file types.", None

        return True, "Path authorized inside workspace.", resolved

    def validate_network_target(self, url_or_host: str) -> Tuple[bool, str]:
        """
        Validates network target against Server-Side Request Forgery (SSRF).
        Blocks private IP ranges, loopback, link-local, and reserved networks.
        Returns: (is_safe, reason)
        """
        url_clean = url_or_host.strip()
        if not url_clean:
            return False, "Empty URL or host provided."

        # Parse scheme and host
        if "://" in url_clean:
            parsed = urlparse(url_clean)
            scheme = parsed.scheme.lower()
            if scheme not in ("http", "https"):
                return False, f"Disallowed URI scheme '{scheme}': Only 'http' and 'https' are permitted."
            hostname = parsed.hostname
            port = parsed.port
        else:
            hostname = url_clean.split(":")[0]
            port = None

        if not hostname:
            return False, "Unable to extract hostname from URL."

        host_lower = hostname.lower()

        # Reject localhost keywords
        if host_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "local", "internal", "corp"):
            return False, f"Host '{hostname}' resolves to blocked loopback or internal name."

        # Check for common internal service ports
        if port and port in (11434, 22, 23, 25, 3389, 5432, 3306, 27017, 6379):
            return False, f"Port {port} points to internal or restricted service."

        # Resolve hostname to IPv4/IPv6 addresses
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{hostname}': {e}"
        except Exception as e:
            return False, f"Network validation error: {e}"

        # Inspect all resolved IP addresses
        for info in addr_info:
            ip_str = info[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # SSRF checks
            if ip_obj.is_loopback:
                return False, f"SSRF Protection: Host '{hostname}' resolves to loopback IP {ip_str}."
            if ip_obj.is_private:
                return False, f"SSRF Protection: Host '{hostname}' resolves to private network IP {ip_str}."
            if ip_obj.is_link_local:
                return False, f"SSRF Protection: Host '{hostname}' resolves to link-local IP {ip_str}."
            if ip_obj.is_multicast:
                return False, f"SSRF Protection: Host '{hostname}' resolves to multicast IP {ip_str}."
            if ip_obj.is_reserved:
                return False, f"SSRF Protection: Host '{hostname}' resolves to reserved IP {ip_str}."

            # Check specific cloud metadata IPs (AWS/Azure/GCP: 169.254.169.254)
            if str(ip_obj) == "169.254.169.254":
                return False, "SSRF Protection: Cloud metadata endpoint access is blocked."

        return True, "Network destination verified public."


# Singleton instance
_enforcer_instance: Optional[PermissionEnforcer] = None


def get_permission_enforcer() -> PermissionEnforcer:
    """Returns the singleton PermissionEnforcer instance."""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = PermissionEnforcer()
    return _enforcer_instance
