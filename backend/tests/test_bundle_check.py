"""The offline bundle check must see every kind of absolute URL."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_bundle_offline.py"
spec = importlib.util.spec_from_file_location("check_bundle_offline", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


@pytest.mark.parametrize(
    ("text", "host"),
    [
        ('fetch("https://cdn.example.com/lib.js")', "cdn.example.com"),
        ("url(//fonts.example.net/a.woff2)", "fonts.example.net"),
        ('new EventSource("http://203.0.113.7:9000/stream")', "203.0.113.7"),
        ('fetch("http://intranet/api")', "intranet"),
        ('"https://user:secret@evil.example.org/x"', "evil.example.org"),
        ('"https://[2001:db8::1]/x"', "[2001:db8::1]"),
        ('"//198.51.100.20/pixel.gif"', "198.51.100.20"),
    ],
)
def test_every_form_of_external_url_is_reported(text, host):
    assert check.hosts_in(text) == {host}


@pytest.mark.parametrize(
    "text",
    [
        "const a = 1; // a comment about example",
        r"const re = /a\/\/b/;",
        'fetch("/api/v1/health")',
        "a//b",
        'const path = "//not a host";',
    ],
)
def test_comments_paths_and_same_origin_requests_are_not_urls(text):
    assert check.hosts_in(text) == set()


def test_only_identifier_hosts_are_allowed():
    text = 'xmlns="http://www.w3.org/2000/svg" see https://reactjs.org/docs fetch("http://10.0.0.5/x")'

    hosts = check.hosts_in(text)

    assert hosts == {"www.w3.org", "reactjs.org", "10.0.0.5"}
    assert hosts - check.ALLOWED_HOSTS == {"10.0.0.5"}
