import pytest

from app.ingestion.adapters import canonicalize_source_url


@pytest.mark.parametrize(
    ("source_type", "value", "expected"),
    [
        (
            "GITHUB",
            "https://WWW.GITHUB.com/rohit/?utm_source=demo#profile",
            "https://www.github.com/rohit",
        ),
        (
            "PORTFOLIO",
            "https://portfolio.example.org/about/",
            "https://portfolio.example.org/about",
        ),
    ],
)
def test_canonicalizes_permitted_source_urls(source_type: str, value: str, expected: str) -> None:
    assert canonicalize_source_url(source_type, value) == expected


@pytest.mark.parametrize(
    ("source_type", "value"),
    [
        ("GITHUB", "http://github.com/user"),
        ("GITHUB", "https://example.org/user"),
        ("PORTFOLIO", "https://localhost/private"),
        ("PORTFOLIO", "https://192.168.1.10/private"),
        ("PORTFOLIO", "https://storage.internal/private"),
        ("PORTFOLIO", "https://portfolio.example.org/a/../admin"),
        ("PORTFOLIO", "https://user:password@portfolio.example.org"),
        ("OTHER", "javascript:alert(1)"),
    ],
)
def test_rejects_untrusted_or_mismatched_source_urls(source_type: str, value: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_source_url(source_type, value)