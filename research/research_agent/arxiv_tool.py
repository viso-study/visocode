import xml.etree.ElementTree as ET

import requests
from smolagents import Tool


class ArxivTool(Tool):
    name = "arxiv_search"
    description = (
        "Search arXiv for the latest research papers matching a technical query. "
        "Returns up to a specified number of recent papers with title, authors, and summary."
    )

    def __init__(self, model=None):
        super().__init__()
        self.model = (
            model  # Store the model adapter (though not used in current implementation)
        )

    inputs = {
        "query": {
            "type": "string",
            "description": "Search terms to query arXiv (e.g., 'graph neural networks').",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of papers to return (default 5).",
            "default": 5,
            "nullable": True,
        },
        "debug": {
            "type": "boolean",
            "description": "If true, include the raw XML response for inspection.",
            "default": True,
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, query: str, max_results: int = 5, debug: bool = True) -> str:
        """
        Perform an arXiv API search and return formatted paper details.
        If debug=True, include the raw ATOM XML at the end.

        NOTE: Current date is July 26, 2025. Results are sorted by submission date (newest first)
        to prioritize the most recent research.
        """
        # Smart sorting and query enhancement based on intent
        enhanced_query = query
        query_lower = query.lower()

        # Define keyword categories
        time_keywords = [
            "latest",
            "recent",
            "current",
            "new",
            "state-of-the-art",
            "cutting-edge",
            "emerging",
        ]
        quality_keywords = [
            "best",
            "most important",
            "seminal",
            "influential",
            "foundational",
            "top",
            "highly cited",
            "landmark",
            "groundbreaking",
            "classic",
        ]

        # Determine search intent and sorting strategy
        is_time_focused = any(keyword in query_lower for keyword in time_keywords)
        is_quality_focused = any(keyword in query_lower for keyword in quality_keywords)

        # Smart sorting selection
        if is_quality_focused and not is_time_focused:
            # Prioritize high-citation, influential papers
            sort_by = "relevance"
            sort_order = "descending"
            sort_reason = "relevance/citations (quality-focused query)"
        elif is_time_focused:
            # Prioritize newest papers and enhance with recent years
            sort_by = "submittedDate"
            sort_order = "descending"
            sort_reason = "newest submissions (time-focused query)"
            if "2025" not in query and "2024" not in query:
                enhanced_query = f"{query} 2025 2024"
        else:
            # Default to relevance for general queries
            sort_by = "relevance"
            sort_order = "descending"
            sort_reason = "relevance (general query)"

        base_url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{enhanced_query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        raw_xml = response.text

        # Track query modifications and sorting strategy
        query_enhanced = enhanced_query != query
        sorting_info = f"Sorted by: {sort_reason}"

        root = ET.fromstring(raw_xml)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            authors = [
                author.find("atom:name", ns).text
                for author in entry.findall("atom:author", ns)
            ]
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            link = entry.find("atom:id", ns).text.strip()
            entries.append(
                {"title": title, "authors": authors, "summary": summary, "link": link}
            )

        if not entries:
            result = "No results found on arXiv for your query."
        else:
            lines = []

            # Add search strategy info
            lines.append(f"📊 Search Strategy: {sorting_info}")

            # Add query enhancement info if applicable
            if query_enhanced:
                lines.append(f"🔍 Enhanced query: '{enhanced_query}'")

            lines.append("")  # Empty line for spacing

            for i, paper in enumerate(entries, start=1):
                authors_str = ", ".join(paper["authors"])
                lines.append(
                    f"{i}. {paper['title']}\n"
                    f"   Authors: {authors_str}\n"
                    f"   Link: {paper['link']}\n"
                    f"   Summary: {paper['summary']}\n"
                )
            result = "\n".join(lines)

        if debug:
            result += "\n\n--- RAW XML RESPONSE (truncated to 500 chars) ---\n"
            result += raw_xml[:500] + "..."

        return result


# Example usage:
# <tool name="arxiv_search">query="graph neural networks"; max_results=3; debug=True</tool>
