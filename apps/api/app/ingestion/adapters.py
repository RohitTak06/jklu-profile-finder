from dataclasses import dataclass
from ipaddress import ip_address
from typing import Protocol
from urllib.parse import unquote, urlsplit, urlunsplit


@dataclass(frozen=True)
class NormalizedProfileSource:
    source_type: str
    source_url: str
    source_identifier: str | None = None


class ProfileSourceAdapter(Protocol):
    async def discover(self, cursor: str | None = None) -> list[str]: ...

    async def fetch(self, source_reference: str) -> object: ...

    async def normalize(self, source_record: object) -> NormalizedProfileSource: ...

    async def validate(self, normalized_record: NormalizedProfileSource) -> bool: ...


def canonicalize_source_url(source_type: str, value: str) -> str:
    parsed = urlsplit(value.strip())
    source_type = source_type.upper()
    allowed_hosts = {
        "GITHUB": {"github.com", "www.github.com"},
        "LINKEDIN": {"linkedin.com", "www.linkedin.com"},
        "INSTAGRAM": {"instagram.com", "www.instagram.com"},
        "JKLU": {"jklu.edu.in", "www.jklu.edu.in"},
    }

    try:
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as error:
        raise ValueError("Source URL is invalid") from error
    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("Source URL host must be a domain name")

    if parsed.scheme.lower() != "https" or not hostname or parsed.username or parsed.password or port:
        raise ValueError("Source URL must be an HTTPS URL without credentials or a custom port")
    if (
        hostname in {"localhost", "localhost.localdomain"}
        or hostname.endswith((".local", ".internal", ".localhost"))
        or "." not in hostname
    ):
        raise ValueError("Source URL host is invalid")
    if any(segment in {".", ".."} for segment in unquote(parsed.path).split("/")):
        raise ValueError("Source URL path is invalid")
    if source_type in allowed_hosts and hostname not in allowed_hosts[source_type]:
        raise ValueError("Source host does not match the declared source type")
    if source_type not in {*allowed_hosts, "PORTFOLIO", "OTHER"}:
        raise ValueError("Source type is not supported")

    path = parsed.path.rstrip("/")
    return urlunsplit(("https", hostname, path, "", ""))