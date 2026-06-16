"""Bureau Search MCP server backed by a local SearXNG instance.

# Design rationale
#
# Bureau needs agents to choose search intent semantically rather than memorize
# raw SearXNG engine strings.  This module exposes a tiny stdio MCP server with
# four tools (web, code, packages, research), then maps each tool to a configured
# SearXNG engine profile.  The MCP transport is intentionally implemented with
# standard-library JSON-RPC so Bureau does not need to add a runtime dependency
# just to bridge one local HTTP endpoint.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

JsonObject = dict[str, Any]
UrlOpener = Callable[..., Any]

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "bureau-search"
SERVER_VERSION = "0.1.0"

TOOL_PROFILES = {
    "bureau_search_web": "web",
    "bureau_search_code": "code",
    "bureau_search_packages": "packages",
    "bureau_search_research": "research",
}

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "web": {
        "description": "General web search through Bureau's managed local SearXNG.",
        "engines": ["duckduckgo", "wikipedia"],
    },
    "code": {
        "description": "Developer Q&A and repository discovery.",
        "engines": ["stackoverflow", "github", "gitlab", "superuser", "askubuntu"],
    },
    "packages": {
        "description": "Package, container, and model registry discovery.",
        "engines": ["pypi", "npm", "crates.io", "docker hub", "pkg.go.dev", "huggingface"],
    },
    "research": {
        "description": "Papers, biomedical literature, and scholarly metadata.",
        "engines": ["arxiv", "pubmed", "semantic scholar", "openalex", "crossref"],
    },
}


@dataclass(frozen=True)
class SearchProfile:
    """SearXNG routing profile for one semantic Bureau search tool.

    Args:
        engines: SearXNG engine names to request for this profile.
        categories: Optional SearXNG categories to request.
        description: Human-readable MCP tool description.
    """

    engines: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_mapping(cls, payload: Any) -> "SearchProfile":
        """Build a profile from JSON/YAML-like settings."""
        if not isinstance(payload, dict):
            return cls()
        return cls(
            engines=[str(engine) for engine in payload.get("engines", [])],
            categories=[str(category) for category in payload.get("categories", [])],
            description=str(payload.get("description", "")),
        )


@dataclass(frozen=True)
class RouterConfig:
    """Runtime settings for the bureau-search MCP server.

    Args:
        searxng_url: Base URL for the local or BYO SearXNG instance.
        profiles: Mapping from profile id to SearXNG profile settings.
        default_max_results: Number of results returned when caller omits `max_results`.
        max_results_limit: Hard cap that prevents accidental huge responses.
        timeout_seconds: HTTP timeout for each SearXNG request.
    """

    searxng_url: str
    profiles: dict[str, SearchProfile] = field(default_factory=dict)
    default_max_results: int = 8
    max_results_limit: int = 20
    timeout_seconds: float = 20.0

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RouterConfig":
        """Build router config from rendered JSON settings."""
        raw_profiles = payload.get("profiles", DEFAULT_PROFILES)
        profiles = {
            str(name): SearchProfile.from_mapping(profile)
            for name, profile in raw_profiles.items()
            if isinstance(name, str)
        }
        for name, default_profile in DEFAULT_PROFILES.items():
            profiles.setdefault(name, SearchProfile.from_mapping(default_profile))

        return cls(
            searxng_url=str(payload.get("searxng_url", "http://127.0.0.1:8786")),
            profiles=profiles,
            default_max_results=int(payload.get("default_max_results", 8)),
            max_results_limit=int(payload.get("max_results_limit", 20)),
            timeout_seconds=float(payload.get("timeout_seconds", 20.0)),
        )


def _as_positive_int(value: Any, default: int) -> int:
    """Parse a user input as a positive integer, falling back to `default`."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def load_router_config() -> RouterConfig:
    """Load bureau-search runtime configuration from the generated JSON file.

    Returns:
        RouterConfig resolved from `BUREAU_SEARCH_ROUTER_CONFIG`, with a
        localhost SearXNG fallback for direct manual invocation.
    """
    config_path = os.environ.get("BUREAU_SEARCH_ROUTER_CONFIG")
    if config_path:
        path = Path(os.path.expandvars(os.path.expanduser(config_path)))
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                return RouterConfig.from_mapping(payload)

    return RouterConfig.from_mapping({
        "searxng_url": os.environ.get("BUREAU_SEARCH_SEARXNG_URL", "http://127.0.0.1:8786"),
        "profiles": DEFAULT_PROFILES,
    })


class SearchRouter:
    """Semantic Bureau search tool router.

    Args:
        config: Runtime router settings.
        opener: Injectable URL opener used by tests; defaults to urllib.request.urlopen.
    """

    def __init__(self, config: RouterConfig, opener: UrlOpener = urlopen) -> None:
        self.config = config
        self._opener = opener

    def tools(self) -> list[JsonObject]:
        """Return MCP tool metadata for the four semantic profiles."""
        return [
            self._tool_schema(
                "bureau_search_web",
                self.config.profiles.get("web"),
                "Search the general web through Bureau's local SearXNG.",
            ),
            self._tool_schema(
                "bureau_search_code",
                self.config.profiles.get("code"),
                "Search developer Q&A and repository discovery engines.",
            ),
            self._tool_schema(
                "bureau_search_packages",
                self.config.profiles.get("packages"),
                "Search package, registry, container, and model indexes.",
            ),
            self._tool_schema(
                "bureau_search_research",
                self.config.profiles.get("research"),
                "Search research-paper and scholarly metadata engines.",
            ),
        ]

    def _tool_schema(
        self,
        name: str,
        profile: SearchProfile | None,
        fallback_description: str,
    ) -> JsonObject:
        """Build one MCP tool schema."""
        description = profile.description if profile and profile.description else fallback_description
        return {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "pageno": {"type": "integer", "minimum": 1},
                    "time_range": {"type": "string"},
                    "language": {"type": "string"},
                    "safesearch": {"type": "integer", "minimum": 0, "maximum": 2},
                    "max_results": {"type": "integer", "minimum": 1},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        }

    def call_tool(self, tool_name: str, arguments: JsonObject) -> JsonObject:
        """Call one Bureau search MCP tool.

        Args:
            tool_name: MCP tool name.
            arguments: Tool-call arguments.

        Returns:
            MCP tools/call result object.
        """
        profile_name = TOOL_PROFILES.get(tool_name)
        if profile_name is None:
            return self._error_result(f"Unknown bureau-search tool: {tool_name}")

        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return self._error_result("`query` must be a non-empty string.")

        profile = self.config.profiles.get(profile_name, SearchProfile())
        max_results = min(
            _as_positive_int(arguments.get("max_results"), self.config.default_max_results),
            self.config.max_results_limit,
        )

        try:
            results = self._search(profile, query.strip(), arguments, max_results)
        except HTTPError as exc:
            if exc.code == 403:
                return self._error_result(
                    "SearXNG rejected the JSON search request. Ensure search.formats includes json."
                )
            return self._error_result(f"SearXNG search failed with HTTP {exc.code}.")
        except (OSError, URLError) as exc:
            return self._error_result(
                f"SearXNG is unreachable at {self.config.searxng_url}: {exc}"
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return self._error_result(f"SearXNG returned an invalid JSON payload: {exc}")

        return {
            "content": [{"type": "text", "text": self._format_results(profile_name, results)}],
            "isError": False,
        }

    def _search(
        self,
        profile: SearchProfile,
        query: str,
        arguments: JsonObject,
        max_results: int,
    ) -> list[JsonObject]:
        """Run one SearXNG JSON search for a semantic profile."""
        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "pageno": _as_positive_int(arguments.get("pageno"), 1),
        }
        if profile.engines:
            params["engines"] = ",".join(profile.engines)
        if profile.categories:
            params["categories"] = ",".join(profile.categories)
        for optional in ("time_range", "language", "safesearch"):
            value = arguments.get(optional)
            if value not in (None, ""):
                params[optional] = str(value)

        url = f"{self.config.searxng_url.rstrip('/')}/search?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": f"{SERVER_NAME}/{SERVER_VERSION} (local MCP)",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            },
        )
        with self._opener(request, timeout=self.config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TypeError("results must be a list")
        return [item for item in raw_results[:max_results] if isinstance(item, dict)]

    def _format_results(self, profile_name: str, results: list[JsonObject]) -> str:
        """Format SearXNG results as compact Markdown."""
        if not results:
            return f"No results from the {profile_name} search profile."

        lines = [f"Bureau {profile_name} search results:", ""]
        for index, item in enumerate(results, start=1):
            title = str(item.get("title") or "Untitled")
            url = str(item.get("url") or "")
            snippet = str(item.get("content") or item.get("description") or "").strip()
            engine = item.get("engine") or item.get("engines") or ""
            if isinstance(engine, list):
                engine_text = ", ".join(str(value) for value in engine)
            else:
                engine_text = str(engine)

            lines.append(f"{index}. [{title}]({url})" if url else f"{index}. {title}")
            if snippet:
                lines.append(f"   {snippet}")
            if engine_text:
                lines.append(f"   Engine: {engine_text}")
        return "\n".join(lines)

    def _error_result(self, message: str) -> JsonObject:
        """Return an MCP tool error payload with a human-readable message."""
        return {"content": [{"type": "text", "text": message}], "isError": True}


def _jsonrpc_result(message_id: Any, result: JsonObject) -> JsonObject:
    """Build a JSON-RPC success response."""
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _jsonrpc_error(message_id: Any, code: int, message: str) -> JsonObject:
    """Build a JSON-RPC error response."""
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def handle_jsonrpc_message(router: SearchRouter, message: JsonObject) -> JsonObject | None:
    """Handle one MCP JSON-RPC message.

    Args:
        router: Search router used for tool operations.
        message: Decoded JSON-RPC request or notification.

    Returns:
        Response object, or None for notifications.
    """
    message_id = message.get("id")
    method = message.get("method")

    # MCP notifications do not expect a JSON-RPC response.
    if message_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _jsonrpc_result(message_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    if method == "ping":
        return _jsonrpc_result(message_id, {})
    if method == "tools/list":
        return _jsonrpc_result(message_id, {"tools": router.tools()})
    if method == "tools/call":
        params = message.get("params", {})
        if not isinstance(params, dict):
            return _jsonrpc_error(message_id, -32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _jsonrpc_error(message_id, -32602, "tools/call requires name and arguments")
        return _jsonrpc_result(message_id, router.call_tool(name, arguments))

    return _jsonrpc_error(message_id, -32601, f"Method not found: {method}")


def serve_stdio(router: SearchRouter) -> None:
    """Run the stdio JSON-RPC server loop."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                response = _jsonrpc_error(None, -32600, "JSON-RPC message must be an object")
            else:
                response = handle_jsonrpc_message(router, message)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_error(None, -32700, f"Parse error: {exc}")
        except Exception as exc:  # pragma: no cover - last-resort server guard
            # keep the MCP process alive after a bad request so agents can retry
            response = _jsonrpc_error(None, -32603, f"Internal error: {exc}")

        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


def main() -> None:
    """Load router config and run the Bureau Search MCP server."""
    serve_stdio(SearchRouter(load_router_config()))


if __name__ == "__main__":
    main()
