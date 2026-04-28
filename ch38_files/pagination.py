"""Link header builder for paginated endpoints (Chapter 31)."""
from fastapi import Request


def build_link_header(request: Request, page: int, per_page: int, total: int) -> str:
    """Return an RFC 5988 Link header value, or empty string if not needed."""
    total_pages = max(1, -(-total // per_page))  # ceiling division
    base = str(request.url.remove_query_params(["page", "per_page"]))

    def page_url(p: int) -> str:
        return f"{base}?page={p}&per_page={per_page}"

    parts = []
    if page > 1:
        parts.append(f'<{page_url(1)}>; rel="first"')
        parts.append(f'<{page_url(page - 1)}>; rel="prev"')
    if page < total_pages:
        parts.append(f'<{page_url(page + 1)}>; rel="next"')
        parts.append(f'<{page_url(total_pages)}>; rel="last"')
    return ", ".join(parts)
