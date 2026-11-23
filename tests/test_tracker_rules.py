# SPDX-License-Identifier: GPL-2.0-only

import unittest

from scripts.tracker_rules import make_rule_set, parse_tracker_url


class ParseTrackerUrlTests(unittest.TestCase):
    def test_udp_domain_port(self):
        self.assertEqual(
            parse_tracker_url("udp://tracker.example.org:6969/announce"),
            ("udp", 6969, "domain", "tracker.example.org"),
        )

    def test_http_default_port(self):
        self.assertEqual(
            parse_tracker_url("http://tracker.example.org/announce"),
            ("tcp", 80, "domain", "tracker.example.org"),
        )

    def test_https_default_port(self):
        self.assertEqual(
            parse_tracker_url("https://tracker.example.org/announce"),
            ("tcp", 443, "domain", "tracker.example.org"),
        )

    def test_ipv4_host(self):
        self.assertEqual(
            parse_tracker_url("udp://93.158.213.92:1337/announce"),
            ("udp", 1337, "ip_cidr", "93.158.213.92/32"),
        )

    def test_ipv6_host(self):
        self.assertEqual(
            parse_tracker_url("udp://[2001:db8::1]:6969/announce"),
            ("udp", 6969, "ip_cidr", "2001:db8::1/128"),
        )

    def test_i2p_hostname(self):
        result = parse_tracker_url("http://tracker.i2p:80/announce")
        self.assertEqual(result, ("tcp", 80, "domain", "tracker.i2p"))

    def test_invalid_url_is_skipped(self):
        self.assertIsNone(parse_tracker_url("not a URL"))
        self.assertIsNone(parse_tracker_url("udp://tracker.example:99999/announce"))


class MakeRuleSetTests(unittest.TestCase):
    def test_grouping_preserves_domain_ip_transport_and_port(self):
        source = [
            "udp://tracker.example.org:6969/announce",
            "udp://other.example.org:6969/announce",
            "http://tracker.example.org:80/announce",
            "udp://93.158.213.92:6969/announce",
        ]
        result, counts = make_rule_set(source)
        self.assertEqual(result["version"], 1)
        self.assertEqual(counts["valid_announce_urls"], 4)
        self.assertEqual(counts["unique_domains"], 2)
        self.assertEqual(counts["unique_ip_addresses"], 1)
        self.assertEqual(counts["compiled_rules"], 2)

        udp_rule = next(rule for rule in result["rules"] if rule.get("network") == ["udp"])
        self.assertEqual(udp_rule["port"], [6969])
        self.assertEqual(sorted(udp_rule["domain"]), ["other.example.org", "tracker.example.org"])
        self.assertEqual(udp_rule["ip_cidr"], ["93.158.213.92/32"])

        tcp_rule = next(rule for rule in result["rules"] if rule.get("network") == ["tcp"])
        self.assertEqual(tcp_rule["port"], [80])
        self.assertEqual(tcp_rule["domain"], ["tracker.example.org"])

    def test_domain_and_ip_are_or_members_of_same_headless_rule(self):
        result, _ = make_rule_set([
            "udp://tracker.example.org:6969/announce",
            "udp://93.158.213.92:6969/announce",
        ])
        self.assertEqual(len(result["rules"]), 1)
        self.assertIn("domain", result["rules"][0])
        self.assertIn("ip_cidr", result["rules"][0])

    def test_empty_input_fails_closed(self):
        with self.assertRaises(ValueError):
            make_rule_set(["# comment", "invalid"])


if __name__ == "__main__":
    unittest.main()
