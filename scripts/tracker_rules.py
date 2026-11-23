# SPDX-License-Identifier: GPL-2.0-only
"""Convert ngosang/trackerslist announce URLs into Sing-box rule-set source JSON."""

from __future__ import annotations

import ipaddress
import re
from collections import defaultdict
from urllib.parse import urlsplit

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "ws": 80,
    "wss": 443,
}
NETWORKS = {
    "udp": "udp",
    "http": "tcp",
    "https": "tcp",
    "ws": "tcp",
    "wss": "tcp",
}
DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def normalize_host(host: str) -> tuple[str, str]:
    """Return (kind, value), where kind is 'domain' or 'ip_cidr'."""
    host = host.strip().rstrip(".").lower()
    if not host:
        raise ValueError("empty hostname")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # An all-numeric dotted host that failed IP parsing is not a DNS name.
        if re.fullmatch(r"[0-9.]+", host):
            raise ValueError(f"invalid IP-like hostname: {host}")
        try:
            host = host.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError(f"invalid IDN hostname: {host}") from exc

        if len(host) > 253:
            raise ValueError(f"hostname too long: {host}")
        labels = host.split(".")
        if any(not label or len(label) > 63 or not DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
            raise ValueError(f"invalid DNS hostname: {host}")
        return "domain", host

    prefix = address.max_prefixlen
    return "ip_cidr", f"{address.compressed}/{prefix}"


def parse_tracker_url(line: str) -> tuple[str, int | None, str, str] | None:
    """Parse one announce URL into (network, port, address_kind, address)."""
    value = line.strip().lstrip("\ufeff")
    if not value or value.startswith("#"):
        return None

    try:
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            return None
        host = parsed.hostname
        if not host:
            return None
        port = parsed.port
    except ValueError:
        # Bad IPv6 brackets or an invalid port; don't emit a malformed rule.
        return None

    scheme = parsed.scheme.lower()
    if port is None:
        port = DEFAULT_PORTS.get(scheme)

    if port is not None and not (1 <= port <= 65535):
        return None

    try:
        kind, address = normalize_host(host)
    except ValueError:
        return None

    # HTTP(S) and WS(S) trackers use TCP; UDP trackers use UDP.
    # An unknown future scheme is still represented by host/port without
    # asserting a transport that this converter cannot safely infer.
    network = NETWORKS.get(scheme)
    return network or "", port, kind, address


def make_rule_set(lines: list[str]) -> dict:
    """Build compact OR rules grouped by transport and destination port."""
    groups: dict[tuple[str, int | None], dict[str, set[str]]] = defaultdict(
        lambda: {"domain": set(), "ip_cidr": set()}
    )
    valid_entries = 0

    for line in lines:
        parsed = parse_tracker_url(line)
        if parsed is None:
            continue
        network, port, kind, address = parsed
        groups[(network, port)][kind].add(address)
        valid_entries += 1

    if not valid_entries:
        raise ValueError("source list contains no valid tracker announce URLs")

    rules = []
    for (network, port), addresses in sorted(
        groups.items(), key=lambda item: (item[0][0], -1 if item[0][1] is None else item[0][1])
    ):
        rule: dict = {}
        if addresses["domain"]:
            rule["domain"] = sorted(addresses["domain"])
        if addresses["ip_cidr"]:
            rule["ip_cidr"] = sorted(addresses["ip_cidr"])
        if network:
            rule["network"] = [network]
        if port is not None:
            rule["port"] = [port]
        if rule:
            rules.append(rule)

    domain_count = len({
        value
        for group in groups.values()
        for value in group["domain"]
    })
    ip_count = len({
        value
        for group in groups.values()
        for value in group["ip_cidr"]
    })

    return {
        "version": 1,
        "rules": rules,
    }, {
        "valid_announce_urls": valid_entries,
        "unique_domains": domain_count,
        "unique_ip_addresses": ip_count,
        "compiled_rules": len(rules),
    }
