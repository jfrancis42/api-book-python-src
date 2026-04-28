import re

LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


def parse_link_header(header):
    """Parse an HTTP Link header into {rel: url}.

    Example input:
      <https://api.github.com/user/repos?page=2>; rel="next",
      <https://api.github.com/user/repos?page=9>; rel="last"

    Returns: {"next": "https://...", "last": "https://..."}
    """
    if not header:
        return {}
    return {rel: url for url, rel in LINK_RE.findall(header)}
