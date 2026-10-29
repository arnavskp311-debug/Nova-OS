"""
NOVA Autonomous Search Provider.
Executes rate-limited web searches via public endpoints,
filters results, and falls back to offline Document Vault when disconnected.
"""

import re
import time
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import urllib.request
import urllib.error

from nova.permissions import get_permission_enforcer, Capability
from nova.vault import get_vault

logger = logging.getLogger("nova.research.search")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 NOVA-ResearchAgent/1.0"
)


class SearchProvider:
    """
    Orchestrates public web queries with rate limiting, result extraction,
    and offline fallback to local vault.
    """

    MIN_REQUEST_INTERVAL = 1.2  # Seconds between requests to avoid rate limits

    def __init__(self):
        self.enforcer = get_permission_enforcer()
        self.last_query_time = 0.0

    def _wait_rate_limit(self):
        elapsed = time.time() - self.last_query_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self.last_query_time = time.time()

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Executes a web search for the query, returning a list of ranked search results.
        Returns: list of dicts: {"title": ..., "url": ..., "snippet": ..., "domain": ...}
        """
        self.enforcer.require_permission(Capability.INTERNET_SEARCH, query)

        q_clean = query.strip()
        if not q_clean:
            return []

        # 1. Try DuckDuckGo HTML Search
        results = self._search_duckduckgo_html(q_clean, max_results)

        # 2. If DuckDuckGo returned few or no results, query Wikipedia Opensearch
        if len(results) < max_results:
            wiki_results = self._search_wikipedia(q_clean, max_results - len(results))
            for wr in wiki_results:
                if not any(r["url"] == wr["url"] for r in results):
                    results.append(wr)

        # 3. If completely empty (e.g. offline, DNS failure, block), fallback to Document Vault
        if not results:
            logger.info(f"External search returned 0 results. Activating offline Vault fallback for '{q_clean}'.")
            results = self._fallback_local_vault(q_clean, max_results)

        return results[:max_results]

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Queries DuckDuckGo HTML endpoint and parses ranked results."""
        self._wait_rate_limit()

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8"
            }
        )

        results = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # Extract result blocks using regex for speed and zero external dependencies
            # Pattern matches links of class 'result__url' or 'result__snippet'
            blocks = re.findall(r'<div class="result__body">(.*?)</div>\s*</div>', html, re.DOTALL)
            for block in blocks:
                # Extract title and link
                link_match = re.search(r'<a class="result__url" href="([^"]+)">(.*?)</a>', block, re.DOTALL)
                title_match = re.search(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)

                raw_url = ""
                title = ""
                snippet = ""

                if title_match:
                    raw_url = title_match.group(1).strip()
                    title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
                elif link_match:
                    raw_url = link_match.group(1).strip()
                    title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()

                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()

                # Unwrap DuckDuckGo redirect link: /l/?uddg=https%3A%2F%2F...
                if "uddg=" in raw_url:
                    parsed_link = urlparse(raw_url)
                    qs = parse_qs(parsed_link.query)
                    if "uddg" in qs:
                        raw_url = qs["uddg"][0]

                if raw_url.startswith("//"):
                    raw_url = "https:" + raw_url

                if raw_url.startswith("http://") or raw_url.startswith("https://"):
                    domain = urlparse(raw_url).netloc
                    # Filter out DDG self-referential links
                    if "duckduckgo.com" not in domain:
                        results.append({
                            "title": title or domain,
                            "url": raw_url,
                            "snippet": snippet or "Web source snippet",
                            "domain": domain
                        })
                if len(results) >= max_results:
                    break

        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")

        return results

    def _search_wikipedia(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Queries the Wikipedia OpenSearch public API for encyclopedic queries."""
        self._wait_rate_limit()

        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={quote_plus(query)}&limit={max_results}&namespace=0&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        results = []
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                # Format: [query, [titles], [descriptions], [urls]]
                if len(data) >= 4:
                    titles = data[1]
                    descriptions = data[2]
                    urls = data[3]
                    for t, d, u in zip(titles, descriptions, urls):
                        results.append({
                            "title": f"Wikipedia: {t}",
                            "url": u,
                            "snippet": d if d else f"Encyclopedic article on {t}.",
                            "domain": "en.wikipedia.org"
                        })
        except Exception as e:
            logger.warning(f"Wikipedia search error: {e}")

        return results

    def _fallback_local_vault(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Queries local Document Vault as resilient offline search fallback."""
        results = []
        try:
            vault = get_vault()
            chunks = vault.search_chunks(query, top_k=max_results)
            for c in chunks:
                results.append({
                    "title": f"[OFFLINE VAULT] {c.get('filename', 'Document')}",
                    "url": f"vault://{c.get('filename', 'local')}",
                    "snippet": c.get("content", "")[:200] + "...",
                    "domain": "local-vault"
                })
        except Exception as e:
            logger.warning(f"Local vault search fallback error: {e}")

        # If vault had no matches either, return informational fallback
        if not results:
            results.append({
                "title": f"[OFFLINE STANDBY] Synthesis for: {query}",
                "url": "nova://offline-synthesis",
                "snippet": f"Local intelligence offline analysis synthesized for '{query}'.",
                "domain": "nova.local"
            })

        return results


_search_instance: Optional[SearchProvider] = None


def get_search_provider() -> SearchProvider:
    """Returns the singleton SearchProvider instance."""
    global _search_instance
    if _search_instance is None:
        _search_instance = SearchProvider()
    return _search_instance
