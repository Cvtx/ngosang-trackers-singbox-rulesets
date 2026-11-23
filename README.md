# BitTorrent Tracker Rule Sets for sing-box

This repository converts the public tracker lists from [ngosang/trackerslist](https://github.com/ngosang/trackerslist) into binary [sing-box](https://sing-box.sagernet.org/) rule sets (`.srs`). 

Each upstream `trackers_*.txt` file is converted into a matching `rulesets/<list-name>.srs` file. The workflow discovers list files dynamically, so newly added upstream lists are included automatically.

## Published rule sets

The raw URL pattern is:

```text
https://raw.githubusercontent.com/Cvtx/ngosang-trackers-singbox-rulesets/main/rulesets/<LIST>.srs
```

Replace `<LIST>` with one of the names below (without `.srs`).

| Upstream list | Binary rule set | Contents |
|---|---|---|
| `trackers_best.txt` | `trackers_best.srs` | Curated public tracker list |
| `trackers_all.txt` | `trackers_all.srs` | All regular public trackers |
| `trackers_all_udp.txt` | `trackers_all_udp.srs` | UDP trackers |
| `trackers_all_http.txt` | `trackers_all_http.srs` | HTTP trackers |
| `trackers_all_https.txt` | `trackers_all_https.srs` | HTTPS trackers |
| `trackers_all_ws.txt` | `trackers_all_ws.srs` | WebSocket trackers |
| `trackers_all_i2p.txt` | `trackers_all_i2p.srs` | I2P trackers |
| `trackers_all_yggdrasil.txt` | `trackers_all_yggdrasil.srs` | Yggdrasil trackers |
| `trackers_best_ip.txt` | `trackers_best_ip.srs` | Curated trackers represented by IP addresses |
| `trackers_all_ip.txt` | `trackers_all_ip.srs` | Trackers represented by IP addresses |
| `trackers_all_yggdrasil_ip.txt` | `trackers_all_yggdrasil_ip.srs` | Yggdrasil trackers represented by IP addresses |

The table reflects the upstream list set currently available. The workflow does not hard-code these names; it publishes every root-level file matching `trackers_*.txt`.

## Synchronization

The upstream lists are observed to refresh at approximately **23:09 UTC**. This repository checks at **23:20 UTC**, allowing time for the upstream update to finish. GitHub Actions may delay scheduled jobs, so this is not a strict real-time guarantee.

On each scheduled run, the workflow fetches the upstream `master` branch and compares the contents of all tracker lists with the previously published source snapshots. If nothing changed, it exits without compiling or committing. If any list changed, it regenerates every `.srs` file and updates the source snapshots, JSON source files, and `manifest.json`. A manual workflow dispatch is also supported.

## Matching behavior and scope

The converter extracts each announce endpoint's hostname/IP address, transport, and destination port. It preserves UDP versus TCP matching and groups entries by transport and port. URL paths, query parameters, and credentials are not part of sing-box routing rules.

These rule sets identify **tracker endpoints only**. They do not identify DHT nodes, Peer Exchange (PEX) peers, or arbitrary peer addresses used for torrent payload traffic. Routing tracker announcements through a proxy does not, by itself, route torrent downloads and uploads through that proxy.

## Attribution and license

The tracker data is sourced from [ngosang/trackerslist](https://github.com/ngosang/trackerslist). The upstream project is distributed under GNU GPL-2.0; its license is included in this repository. The conversion scripts are also licensed under GPL-2.0. See [NOTICE.md](NOTICE.md) for attribution.
