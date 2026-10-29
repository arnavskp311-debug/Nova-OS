"""
NOVA Safe Web Fetcher & Content Sanitizer.
Fetches public web pages with SSRF defenses, strict size bounds,
and sanitizes HTML into plain text bounded against prompt injection.
"""

import re
import socket
import logging
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import Tuple, Dict, Any, Optional
import urllib.request
import urllib.error

from nova.config import (
    MAX_DOWNLOAD_SIZE_BYTES, MAX_TEXT_EXTRACT_CHARS, WEB_REQUEST_TIMEOUT
)
from nova.permissions import (
    get_permission_enforcer, Capability, PermissionDeniedSecurityError
)
from nova.workspace import get_research_workspace

logger = logging.getLogger("nova.research.fetcher")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 NOVA-ResearchAgent/1.0"
)


class HTMLSanitizingExtractor(HTMLParser):
    """
    Strips scripts, styles, forms, navigation, and advertisement tags,
    extracting clean textual paragraphs and document title.
    """

    IGNORABLE_BLOCK_TAGS = {
        "script", "style", "noscript", "svg", "canvas", "iframe",
        "nav", "footer", "header", "aside"
    }

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img",
        "input", "link", "meta", "param", "source", "track", "wbr"
    }

    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.ignore_stack = []
        self.text_chunks = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in self.IGNORABLE_BLOCK_TAGS:
            self.ignore_stack.append(t)
        elif t == "title":
            self.in_title = True
        elif t in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr", "article", "section"):
            self.text_chunks.append("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if self.ignore_stack and self.ignore_stack[-1] == t:
            self.ignore_stack.pop()
        elif t in self.ignore_stack:
            self.ignore_stack.remove(t)
        elif t == "title":
            self.in_title = False
        elif t in ("p", "div", "h1", "h2", "h3", "h4", "li", "tr", "article", "section"):
            self.text_chunks.append("\n")

    def handle_data(self, data):
        if self.ignore_stack:
            return
        if self.in_title:
            self.title += data.strip()
        else:
            text = data.strip()
            if text:
                self.text_chunks.append(text + " ")

    def get_clean_text(self) -> str:
        raw = "".join(self.text_chunks)
        # Collapse multiple empty lines and excessive whitespace
        lines = [line.strip() for line in raw.split("\n")]
        compacted = [line for line in lines if line]
        return "\n\n".join(compacted)


class SafeFetcher:
    """
    Safely retrieves public web resources, validates against SSRF,
    extracts sanitized text, and manages permitted file downloads.
    """

    def __init__(self):
        self.enforcer = get_permission_enforcer()
        self.workspace = get_research_workspace()

    def fetch_webpage(self, url: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Fetches and sanitizes a public webpage.
        Returns: (success, sanitized_text, metadata)
        """
        self.enforcer.require_permission(Capability.INTERNET_FETCH_PUBLIC, url)

        # 1. SSRF and Protocol Validation
        is_safe, reason = self.enforcer.validate_network_target(url)
        if not is_safe:
            logger.warning(f"SSRF blocked fetch for '{url}': {reason}")
            return False, f"[BLOCKED BY NOVA OS SECURITY: {reason}]", {"error": reason, "url": url}

        parsed = urlparse(url)
        domain = parsed.netloc

        # 2. HTTP Request with bounded timeout & headers
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=WEB_REQUEST_TIMEOUT) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                # Enforce text/html or plain text
                if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml+xml", "text/xml")):
                    return False, f"[UNSUPPORTED MEDIA TYPE: {content_type}]", {"url": url, "domain": domain}

                # Read response up to MAX_DOWNLOAD_SIZE_BYTES
                raw_bytes = response.read(MAX_DOWNLOAD_SIZE_BYTES + 1024)
                if len(raw_bytes) > MAX_DOWNLOAD_SIZE_BYTES:
                    return False, "[PAYLOAD EXCEEDED 5 MB LIMIT]", {"url": url, "domain": domain}

                # Decode HTML with fallbacks
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    html_str = raw_bytes.decode(charset, errors="replace")
                except Exception:
                    html_str = raw_bytes.decode("latin-1", errors="replace")

        except urllib.error.HTTPError as e:
            return False, f"[HTTP ERROR {e.code}: {e.reason}]", {"url": url, "domain": domain, "error": str(e)}
        except urllib.error.URLError as e:
            return False, f"[NETWORK CONNECTION FAILED: {e.reason}]", {"url": url, "domain": domain, "error": str(e)}
        except socket.timeout:
            return False, f"[REQUEST TIMED OUT ({WEB_REQUEST_TIMEOUT}s)]", {"url": url, "domain": domain, "error": "timeout"}
        except Exception as e:
            return False, f"[FETCH EXCEPTION: {e}]", {"url": url, "domain": domain, "error": str(e)}

        # 3. HTML Sanitization & Plain Text Extraction
        parser = HTMLSanitizingExtractor()
        try:
            parser.feed(html_str)
            title = parser.title or domain
            clean_text = parser.get_clean_text()
        except Exception as e:
            # Fallback regex strip
            title = domain
            clean_text = re.sub(r"<[^>]+>", " ", html_str)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

        if not clean_text:
            return False, "[NO READABLE TEXT EXTRACTED]", {"url": url, "domain": domain, "title": title}

        # 4. Context Clamping
        if len(clean_text) > MAX_TEXT_EXTRACT_CHARS:
            clean_text = clean_text[:MAX_TEXT_EXTRACT_CHARS] + "\n... [Content truncated at safe threshold]"

        # 5. Untrusted Boundary Enclosure
        isolated_content = (
            f"[UNTRUSTED_EXTERNAL_WEB_SOURCE domain=\"{domain}\" url=\"{url}\"]\n"
            f"Page Title: {title}\n\n"
            f"{clean_text}\n"
            f"[/UNTRUSTED_EXTERNAL_WEB_SOURCE]"
        )

        metadata = {
            "url": url,
            "domain": domain,
            "title": title,
            "char_count": len(clean_text),
            "status": "FETCHED"
        }
        return True, isolated_content, metadata

    def download_permitted_file(self, url: str, target_filename: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Downloads a permitted non-executable file directly into data/workspace/downloads/.
        Returns: (success, message, local_file_path)
        """
        self.enforcer.require_permission(Capability.WORKSPACE_DOWNLOAD, url)

        # Validate URL against SSRF
        is_safe, reason = self.enforcer.validate_network_target(url)
        if not is_safe:
            return False, f"SSRF Protection blocked download: {reason}", None

        parsed = urlparse(url)
        raw_name = target_filename or parsed.path.split("/")[-1] or "downloaded_file.txt"

        # Sanitize filename
        safe_name = re.sub(r'[^\w\.-]', '_', raw_name)

        # Validate file extension
        is_valid, reason, resolved = self.enforcer.validate_fs_path(
            self.workspace.SUBFOLDERS["downloads"] / safe_name,
            mode="download"
        )
        if not is_valid or not resolved:
            return False, f"File rejected by security policy: {reason}", None

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(req, timeout=WEB_REQUEST_TIMEOUT * 2) as resp:
                content = resp.read(MAX_DOWNLOAD_SIZE_BYTES + 1024)
                if len(content) > MAX_DOWNLOAD_SIZE_BYTES:
                    return False, f"Download aborted: file exceeds {MAX_DOWNLOAD_SIZE_BYTES // (1024*1024)} MB limit.", None

                saved_path = self.workspace.write_file("downloads", safe_name, content)
                return True, f"File downloaded safely: {saved_path.name}", str(saved_path)
        except Exception as e:
            return False, f"Download failed: {e}", None


_fetcher_instance: Optional[SafeFetcher] = None


def get_safe_fetcher() -> SafeFetcher:
    """Returns the singleton SafeFetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = SafeFetcher()
    return _fetcher_instance
