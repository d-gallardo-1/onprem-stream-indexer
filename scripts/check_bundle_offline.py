"""Fail when the built frontend refers to another origin.

The UI must work with no network access: no CDN, no web fonts, no external API.
This reads the production bundle in ``frontend/dist`` and lists every absolute
URL in it. A short allow-list covers strings that libraries embed but never
request: XML namespaces and the links inside licence and error messages.

    python scripts/check_bundle_offline.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

URL = re.compile(r"""(?:https?:)?//[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}[^\s"'`)<>\\]*""")
TEXT_SUFFIXES = {".html", ".js", ".css", ".svg", ".json", ".map"}
#: Hosts that appear only as identifiers or documentation links, never as requests.
ALLOWED_HOSTS = {
    "www.w3.org",  # SVG, XLink and MathML namespace identifiers
    "react.dev",  # React's error-decoder link in its production messages
    "reactjs.org",
    "github.com",  # licence banners
    "tailwindcss.com",
}


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
        for match in URL.findall(path.read_text(encoding="utf-8", errors="replace")):
            host = match.split("//", 1)[1].split("/", 1)[0].lower()
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
