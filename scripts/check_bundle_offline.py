"""Fail when the built frontend refers to another origin.

The UI must work with no network access: no CDN, no web fonts, no external API.
This reads the production bundle in ``frontend/dist`` and lists every host it
names in an absolute URL: a domain name, a single-label name, an IPv4 or IPv6
literal, with or without credentials and a port. A short allow-list covers
strings that libraries embed but never request: XML namespaces and the links
inside licence and error messages.

    python scripts/check_bundle_offline.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

#: Characters that end a URL inside source text.
_REST = r"""[^\s"'`)<>\\]*"""
#: An absolute URL with a scheme. Any host counts, also behind ``user:password@``.
SCHEME_URL = re.compile(
    r"""https?://(?:[^\s/"'`)<>\\@]*@)?(\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9][A-Za-z0-9.-]*)""" + _REST
)
#: A protocol-relative URL. Without a scheme, ``//`` is also a comment or part of
#: a path, so only a dotted host or an IPv4 literal is taken as a URL.
RELATIVE_URL = re.compile(
    r"""(?<![:\w/\\])//((?:\d{1,3}\.){3}\d{1,3}|[A-Za-z0-9][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)*"""
    r"""\.[A-Za-z]{2,})(?![\w.-])""" + _REST
)
TEXT_SUFFIXES = {".html", ".js", ".css", ".svg", ".json", ".map"}
#: Hosts that appear only as identifiers or documentation links, never as requests.
ALLOWED_HOSTS = {
    "www.w3.org",  # SVG, XLink and MathML namespace identifiers
    "react.dev",  # React's error-decoder link in its production messages
    "reactjs.org",
    "github.com",  # licence banners
    "tailwindcss.com",
}


def hosts_in(text: str) -> set[str]:
    """Every host that ``text`` names in an absolute or protocol-relative URL."""
    hosts = {match.group(1).lower() for match in SCHEME_URL.finditer(text)}
    hosts |= {match.group(1).lower() for match in RELATIVE_URL.finditer(text)}
    return hosts


def main() -> int:
    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if not dist.is_dir():
        print("frontend/dist not found. Run 'npm run build' in frontend/ first.")
        return 1

    found: dict[str, set[str]] = {}
    checked = 0
    for path in sorted(dist.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        checked += 1
        for host in hosts_in(path.read_text(encoding="utf-8", errors="replace")):
            found.setdefault(host, set()).add(path.relative_to(dist).as_posix())

    unexpected = {host: files for host, files in found.items() if host not in ALLOWED_HOSTS}
    if unexpected:
        print("The bundle refers to hosts outside the allow-list:")
        for host, files in sorted(unexpected.items()):
            print(f"  {host}  in {', '.join(sorted(files))}")
        return 1
    seen = ", ".join(sorted(found)) or "none"
    print(f"{checked} bundle files checked; no external origin. Identifier-only hosts: {seen}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
