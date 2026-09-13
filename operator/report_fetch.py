"""Bounded public HTML fetch with DNS pinned to the checked network address."""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import quote, urljoin, urlsplit

from public_url import normalized_public_url

MAX_HTML = 2 * 1024 * 1024


class FetchError(ValueError):
    """Safe failure category; never include response bodies or private URLs."""


def _request(url):
    parsed = urlsplit(url)
    host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0].split("%", 1)[0]).is_global for a in addresses):
        raise FetchError("Page address is not public.")
    family, kind, proto, _, address = addresses[0]
    connection = http.client.HTTPConnection(host, port, timeout=10)
    # Connect the validated address directly. Never resolve the hostname again.
    sock = socket.socket(family, kind, proto)
    response = None
    try:
        sock.settimeout(10)
        sock.connect(address)
        if parsed.scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        # Intake allows Unicode URLs; HTTP request targets must be ASCII.
        # Preserve existing percent escapes and URI separators, not raw spaces.
        target = quote(parsed.path or "/", safe="/:@!$&'()*+,;=-._~%")
        if parsed.query:
            target += "?" + quote(parsed.query, safe="/?:@!$&'()*+,;=-._~%[]")
        connection.request("GET", target, headers={"User-Agent": "CommerceLint/1.0 public-page-audit",
            "Accept": "text/html, application/xhtml+xml", "Accept-Encoding": "identity", "Connection": "close"})
        # Own the response lifecycle: HTTPConnection.getresponse() closes the
        # connection socket for Connection: close, preventing deadline updates.
        response = http.client.HTTPResponse(sock, method="GET")
        response.begin()
        deadline = time.monotonic() + 20
        if response.status in {301, 302, 303, 307, 308}:
            return response.status, response.getheader("Location", ""), ""
        if response.status != 200:
            raise FetchError("Page returned an unsuccessful HTTP status.")
        if response.headers.get_content_type() not in {"text/html", "application/xhtml+xml"}:
            raise FetchError("Page is not HTML.")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise FetchError("Compressed page response is unsupported.")
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FetchError("Page response timed out.")
            sock.settimeout(min(10, remaining))
            chunk = response.read1(min(65536, MAX_HTML + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_HTML:
                raise FetchError("Page exceeded the HTML size limit.")
        return response.status, "", body.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    finally:
        if response is not None:
            response.close()
        connection.close()
        sock.close()


def fetch_public_html(url: str) -> str:
    """No credentials, cookies, proxies or JavaScript. Recheck every redirect."""
    try:
        current = normalized_public_url(url, resolve_dns=False)
        for _ in range(4):
            status, redirect, html = _request(current)
            if status == 200:
                if not html.strip():
                    raise FetchError("Page HTML is empty.")
                return html
            target = normalized_public_url(urljoin(current, redirect), resolve_dns=False)
            if not redirect or (urlsplit(current).scheme == "https" and urlsplit(target).scheme != "https"):
                raise FetchError("Page redirect is unsupported.")
            current = target
        raise FetchError("Page exceeded the redirect limit.")
    except (OSError, ValueError, http.client.HTTPException, LookupError):
        raise FetchError("Public HTML could not be fetched safely; manual retry or support is required.") from None
