import json
import urllib.parse
from io import BytesIO
from typing import Dict, List, Optional
import qrcode
from PIL import Image

from catalog import (
    ANDROID_DIRECT_PACKAGES,
    PROTECTED_PROXY_DOMAINS,
    RU_DIRECT_CATEGORIES,
    RU_DIRECT_TLDS
)


def build_vless_uri(node: Dict) -> str:
    """Reconstruct standard VLESS Reality link."""
    uuid = node["uuid"]
    server = node["server"]
    port = node["port"]
    name = urllib.parse.quote(node.get("name", "Smart Mobile VPN"))

    params = {
        "type": "tcp",
        "security": "reality",
        "pbk": node.get("public_key", ""),
        "fp": node.get("client_fingerprint", "chrome"),
        "sni": node.get("servername", "gateway.icloud.com"),
        "sid": node.get("short_id", ""),
        "spx": "/",
        "flow": node.get("flow", "xtls-rprx-vision")
    }
    query = urllib.parse.urlencode(params)
    return f"vless://{uuid}@{server}:{port}?{query}#{name}"


def generate_singbox_json(node: Dict,
                          enabled_categories: Optional[List[str]] = None,
                          custom_packages: Optional[List[str]] = None) -> str:
    """
    Generate Sing-box / Hiddify compatible JSON with full mobile split-tunneling.
    Includes Android package names, domain rules, and GeoIP rules.
    """
    if enabled_categories is None:
        enabled_categories = list(RU_DIRECT_CATEGORIES.keys())

    packages = list(ANDROID_DIRECT_PACKAGES)
    if custom_packages:
        packages.extend(custom_packages)

    # Collect Russian domains
    ru_domains = []
    for cat in enabled_categories:
        if cat in RU_DIRECT_CATEGORIES:
            for d in RU_DIRECT_CATEGORIES[cat]:
                ru_domains.append(d.split("/")[0].strip())

    config = {
        "log": {
            "level": "info",
            "timestamp": True
        },
        "dns": {
            "servers": [
                {
                    "tag": "remote-dns",
                    "address": "https://1.1.1.1/dns-query",
                    "detour": "proxy"
                },
                {
                    "tag": "direct-dns",
                    "address": "https://77.88.8.8/dns-query",
                    "detour": "direct"
                },
                {
                    "tag": "block-dns",
                    "address": "rcode://success"
                }
            ],
            "rules": [
                {
                    "outbound": ["any"],
                    "server": "direct-dns"
                },
                {
                    "domain_suffix": [".ru", ".su", ".xn--p1ai"] + ru_domains,
                    "server": "direct-dns"
                },
                {
                    "domain_suffix": PROTECTED_PROXY_DOMAINS,
                    "server": "remote-dns"
                }
            ],
            "strategy": "prefer_ipv4"
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": False,
                "stack": "system",
                "sniff": True,
                "sniff_override_destination": True
            }
        ],
        "outbounds": [
            {
                "type": "vless",
                "tag": "proxy",
                "server": node["server"],
                "server_port": int(node["port"]),
                "uuid": node["uuid"],
                "flow": node.get("flow", "xtls-rprx-vision"),
                "network": "tcp",
                "tls": {
                    "enabled": True,
                    "server_name": node.get("servername", "gateway.icloud.com"),
                    "utls": {
                        "enabled": True,
                        "fingerprint": node.get("client_fingerprint", "chrome")
                    },
                    "reality": {
                        "enabled": True,
                        "public_key": node.get("public_key", ""),
                        "short_id": node.get("short_id", "")
                    }
                }
            },
            {
                "type": "direct",
                "tag": "direct"
            },
            {
                "type": "block",
                "tag": "block"
            },
            {
                "type": "dns",
                "tag": "dns-out"
            }
        ],
        "route": {
            "rules": [
                {
                    "protocol": "dns",
                    "outbound": "dns-out"
                },
                # Android Apps Bypass (Banking, Gov, Russian Marketplaces)
                {
                    "package_name": packages,
                    "outbound": "direct"
                },
                # Protected Services -> strictly PROXY
                {
                    "domain_suffix": PROTECTED_PROXY_DOMAINS,
                    "outbound": "proxy"
                },
                {
                    "domain_keyword": ["google", "discord", "youtube"],
                    "outbound": "proxy"
                },
                # Russian Domains & TLDs -> DIRECT
                {
                    "domain_suffix": RU_DIRECT_TLDS + ru_domains,
                    "outbound": "direct"
                },
                # GeoIP Russia -> DIRECT
                {
                    "geoip": ["ru", "private"],
                    "outbound": "direct"
                },
                # GeoSite Russia -> DIRECT
                {
                    "geosite": ["category-ru"],
                    "outbound": "direct"
                }
            ],
            "auto_detect_interface": True,
            "final": "proxy"
        }
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def generate_qr_image(data: str, size: int = 350) -> Image.Image:
    """Generate high-quality PIL Image containing QR code."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="#ffffff").convert("RGBA")
    return img.resize((size, size), Image.Resampling.LANCZOS)
