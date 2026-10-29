"""
NOVA OS Autonomous Internet Research Subsystem.
Provides bounded web search, safe HTML text extraction, multi-source synthesis,
contradiction detection, and sandboxed workspace reporting.
"""

from nova.research.search_provider import SearchProvider, get_search_provider
from nova.research.safe_fetcher import SafeFetcher, get_safe_fetcher
from nova.research.research_orchestrator import ResearchOrchestrator, ResearchState

__all__ = [
    "SearchProvider",
    "get_search_provider",
    "SafeFetcher",
    "get_safe_fetcher",
    "ResearchOrchestrator",
    "ResearchState",
]
