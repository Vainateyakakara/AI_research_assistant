"""
tools/arxiv_search.py - Arxiv paper search utility
"""

import arxiv
from typing import Dict
import time


def search_arxiv(query: str, max_results: int = 5) -> str:
    """
    Search arxiv for papers and return formatted summaries
    """
    try:
        query = query[:100]
        max_results = min(3, max_results)

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        client = arxiv.Client(page_size=max_results)

        def safe_results():
            last_error = None
            for attempt in range(3):
                try:
                    return list(client.results(search))
                except Exception as e:
                    last_error = e
                    wait = 3 * (attempt + 1)
                    print(f"arXiv request failed (attempt {attempt + 1}/3): {e}")
                    print(f"Retrying in {wait}s...")
                    time.sleep(wait)
            raise last_error

        results = safe_results()

        papers = []
        for result in results:
            time.sleep(1)
            papers.append(f"""
Title: {result.title}
Authors: {', '.join([a.name for a in result.authors][:3])}{'...' if len(result.authors) > 3 else ''}
Published: {result.published.strftime('%Y-%m-%d')}
Summary: {result.summary}
URL: {result.entry_id}
""")

        if not papers:
            return "No papers found for this query."

        return "\n".join(papers)

    except Exception as e:
        return f"Error searching arxiv: {e}"


def get_paper_details(paper_id: str) -> Dict:
    """
    Get detailed information about a specific paper
    """
    try:
        search = arxiv.Search(id_list=[paper_id])
        client = arxiv.Client()

        paper = next(client.results(search), None)
        if paper is None:
            return {"error": "Paper not found"}

        return {
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "abstract": paper.summary,
            "published": paper.published,
            "pdf_url": paper.pdf_url,
            "categories": paper.categories
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    results = search_arxiv("attention mechanism transformers", max_results=3)
    print(results)