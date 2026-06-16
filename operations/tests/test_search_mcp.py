import json
from urllib.parse import parse_qs, urlparse

from operations.search_mcp.server import RouterConfig, SearchProfile, SearchRouter


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def getcode(self) -> int:
        return 200


def test_code_tool_queries_searxng_with_code_profile_engines():
    captured_urls: list[str] = []

    def opener(request, *, timeout):
        captured_urls.append(request.full_url)
        assert timeout == 20.0
        assert request.headers["Accept"] == "application/json"
        assert request.headers["X-forwarded-for"] == "127.0.0.1"
        return FakeResponse({
            "results": [
                {
                    "title": "Python dataclasses",
                    "url": "https://stackoverflow.com/questions/1",
                    "content": "Use dataclasses for compact value objects.",
                    "engine": "stackoverflow",
                }
            ]
        })

    router = SearchRouter(
        RouterConfig(
            searxng_url="http://127.0.0.1:8786",
            profiles={
                "code": SearchProfile(engines=["stackoverflow", "github"]),
            },
            default_max_results=5,
        ),
        opener=opener,
    )

    result = router.call_tool(
        "bureau_search_code",
        {"query": "python dataclass", "max_results": 3, "pageno": 2},
    )

    params = parse_qs(urlparse(captured_urls[0]).query)
    assert params["q"] == ["python dataclass"]
    assert params["format"] == ["json"]
    assert params["engines"] == ["stackoverflow,github"]
    assert params["pageno"] == ["2"]
    text = result["content"][0]["text"]
    assert "Python dataclasses" in text
    assert "https://stackoverflow.com/questions/1" in text
    assert "stackoverflow" in text


def test_tool_result_is_loud_when_searxng_is_unreachable():
    def opener(_request, *, timeout):
        assert timeout == 20.0
        raise OSError("connection refused")

    router = SearchRouter(
        RouterConfig(
            searxng_url="http://127.0.0.1:8786",
            profiles={"web": SearchProfile(engines=["duckduckgo"])},
        ),
        opener=opener,
    )

    result = router.call_tool("bureau_search_web", {"query": "bureau"})

    assert result["isError"] is True
    assert "SearXNG is unreachable" in result["content"][0]["text"]


def test_tools_list_exposes_semantic_profiles():
    router = SearchRouter(
        RouterConfig(
            searxng_url="http://127.0.0.1:8786",
            profiles={
                "web": SearchProfile(engines=["duckduckgo"]),
                "code": SearchProfile(engines=["stackoverflow"]),
                "packages": SearchProfile(engines=["pypi"]),
                "research": SearchProfile(engines=["arxiv"]),
            },
        )
    )

    names = {tool["name"] for tool in router.tools()}

    assert names == {
        "bureau_search_web",
        "bureau_search_code",
        "bureau_search_packages",
        "bureau_search_research",
    }
