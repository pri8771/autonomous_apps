#!/usr/bin/env python3
"""Shared public URL policy for CommerceLint intake and paid reports."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import Iterable


def normalized_public_url(raw: str, *, resolve_dns: bool = True) -> str:
    raw = (raw or "").strip().strip("<>")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only public HTTP or HTTPS URLs are accepted.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not accepted.")
    if not parsed.hostname:
        raise ValueError("The URL has no hostname.")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("Only standard HTTP and HTTPS ports are accepted.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".home")):
        raise ValueError("Private or local hostnames are not accepted.")
    if resolve_dns:
        validate_public_host(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    cleaned = parsed._replace(fragment="")
    return urllib.parse.urlunsplit(cleaned)


def validate_public_host(host: str, port: int) -> None:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"The hostname could not be resolved: {exc}") from exc
    if not addresses:
        raise ValueError("The hostname did not resolve.")
    for info in addresses:
        address = info[4][0].split("%", 1)[0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("The URL resolves to a non-public network address.")


def parse_url_list(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.replace(",", "\n").splitlines()]
    else:
        parts = [str(part).strip() for part in raw]
    return [part for part in parts if part]


def validate_url_batch(
    urls: Iterable[str],
    *,
    max_urls: int,
    resolve_dns: bool = True,
) -> dict:
    """Validate a batch of URLs against plan limits. Never charge when rejected."""
    items = parse_url_list(urls)
    accepted: list[str] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()

    if not items:
        return {
            "ok": False,
            "charge_allowed": False,
            "accepted_urls": [],
            "rejected": [{"url": "", "reason": "At least one public product URL is required."}],
            "error": "At least one public product URL is required.",
        }

    if len(items) > max_urls:
        return {
            "ok": False,
            "charge_allowed": False,
            "accepted_urls": [],
            "rejected": [
                {
                    "url": "",
                    "reason": f"Plan allows at most {max_urls} public product URL(s); received {len(items)}.",
                }
            ],
            "error": f"Plan allows at most {max_urls} public product URL(s); received {len(items)}.",
        }

    for raw in items:
        try:
            normalized = normalized_public_url(raw, resolve_dns=resolve_dns)
        except ValueError as exc:
            rejected.append({"url": raw, "reason": str(exc)})
            continue
        if normalized in seen:
            rejected.append({"url": raw, "reason": "Duplicate URL after normalization."})
            continue
        seen.add(normalized)
        accepted.append(normalized)

    if rejected or not accepted:
        first = rejected[0]["reason"] if rejected else "No accepted public product URLs."
        return {
            "ok": False,
            "charge_allowed": False,
            "accepted_urls": accepted,
            "rejected": rejected,
            "error": first,
        }

    return {
        "ok": True,
        "charge_allowed": True,
        "accepted_urls": accepted,
        "rejected": [],
        "error": None,
    }
