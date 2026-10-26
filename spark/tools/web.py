"""Web arama tool'u — DuckDuckGo ile."""

from __future__ import annotations

from spark.tools.registry import ToolDefinition, ToolParameter


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo ile web araması yap."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return (
            "Error: duckduckgo-search paketi yüklü değil. "
            "Yüklemek için: pip install duckduckgo-search"
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        output_parts: list[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            url = r.get("href", "")

            output_parts.append(
                f"{i}. {title}\n   {body}\n   URL: {url}"
            )

        return "\n\n".join(output_parts)

    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


WEB_SEARCH_TOOL = ToolDefinition(
    name="web_search",
    description="Search the web using DuckDuckGo. Returns titles, snippets and URLs.",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results. Default 5.",
            required=False,
        ),
    ],
    handler=web_search,
)
