import os
import re
import json
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

from catalog import (
    PROTECTED_PROXY_DOMAINS,
    PROTECTED_PROXY_PROCESSES,
    RU_DIRECT_CATEGORIES,
    RU_DIRECT_TLDS
)


def parse_vless_link(link: str) -> Dict[str, str]:
    """Parse standard vless:// link into dictionary."""
    link = link.strip()
    if not link.startswith("vless://"):
        raise ValueError("Ссылка должна начинаться с vless://")

    # Format: vless://uuid@host:port?param1=val1&param2=val2#NodeName
    u = urllib.parse.urlparse(link)
    uuid = u.username
    host = u.hostname
    port = u.port or 443
    name = urllib.parse.unquote(u.fragment) if u.fragment else f"Smart VLESS ({host})"

    params = urllib.parse.parse_qs(u.query)
    def get_p(key: str, default: str = "") -> str:
        return params.get(key, [default])[0]

    return {
        "name": name,
        "server": host,
        "port": int(port),
        "uuid": uuid,
        "type": "vless",
        "flow": get_p("flow", "xtls-rprx-vision"),
        "tls": True,
        "udp": True,
        "servername": get_p("sni", "gateway.icloud.com"),
        "client_fingerprint": get_p("fp", "chrome"),
        "public_key": get_p("pbk", ""),
        "short_id": get_p("sid", "")
    }


def generate_clash_yaml(node: Dict,
                        selected_game_exes: List[str],
                        enabled_categories: Optional[List[str]] = None) -> str:
    """Generate complete Mihomo / Clash Verge profile YAML."""
    if enabled_categories is None:
        enabled_categories = list(RU_DIRECT_CATEGORIES.keys())

    # Build rules list
    rules = []

    # 1. Game executables -> DIRECT (or GAMES proxy group)
    for exe in selected_game_exes:
        clean_base = re.sub(r"\.exe$", "", exe, flags=re.IGNORECASE).strip()
        # Escaping special regex chars
        escaped = re.escape(clean_base)
        rules.append(f"PROCESS-NAME-REGEX,(?i).*{escaped}.*,DIRECT")

    # 2. Protected overseas processes -> PROXY
    for proc in PROTECTED_PROXY_PROCESSES:
        p_clean = re.sub(r"\.exe$", "", proc, flags=re.IGNORECASE).strip()
        rules.append(f"PROCESS-NAME-REGEX,(?i).*{p_clean}.*,PROXY")

    # 3. Protected AI and Google domains -> PROXY
    for d in PROTECTED_PROXY_DOMAINS:
        rules.append(f"DOMAIN-SUFFIX,{d},PROXY")
    rules.append("DOMAIN-KEYWORD,google,PROXY")
    rules.append("DOMAIN-KEYWORD,discord,PROXY")

    # 4. Russian service domains -> DIRECT
    for cat in enabled_categories:
        if cat in RU_DIRECT_CATEGORIES:
            for domain in RU_DIRECT_CATEGORIES[cat]:
                # strip paths if any
                pure_d = domain.split("/")[0].strip()
                rules.append(f"DOMAIN-SUFFIX,{pure_d},DIRECT")

    # 5. Russian and friendly TLDs -> DIRECT
    for tld in RU_DIRECT_TLDS:
        rules.append(f"DOMAIN-SUFFIX,{tld},DIRECT")

    # 6. GeoIP routing with no-resolve
    rules.append("GEOIP,RU,DIRECT,no-resolve")
    rules.append("GEOIP,private,DIRECT,no-resolve")

    # 7. Fallback match -> PROXY
    rules.append("MATCH,PROXY")

    # Construct complete dictionary
    clash_dict = {
        "mode": "rule",
        "mixed-port": 7897,
        "allow-lan": False,
        "log-level": "info",
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "tun": {
            "enable": True,
            "stack": "gvisor",
            "device": "Mihomo",
            "auto-route": True,
            "auto-detect-interface": True,
            "dns-hijack": ["any:53"],
            "mtu": 1500,
            "route-exclude-address": [f"{node['server']}/32"]
        },
        "dns": {
            "enable": True,
            "listen": "127.0.0.1:1053",
            "ipv6": False,
            "default-nameserver": ["1.1.1.1", "8.8.8.8", "77.88.8.8"],
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "use-hosts": True,
            "fake-ip-filter": [
                "*.ru", "*.su", "*.xn--p1ai",
                "*.steamserver.net", "*.valve.net",
                "*.battlenet.com", "*.blizzard.com"
            ],
            "nameserver": [
                "https://1.1.1.1/dns-query",
                "https://8.8.8.8/dns-query"
            ],
            "nameserver-policy": {
                "+.ru": ["77.88.8.8", "195.208.4.1"],
                "+.su": ["77.88.8.8", "195.208.4.1"],
                "+.xn--p1ai": ["77.88.8.8", "195.208.4.1"]
            }
        },
        "proxies": [
            {
                "name": node["name"],
                "type": "vless",
                "server": node["server"],
                "port": int(node["port"]),
                "uuid": node["uuid"],
                "network": "tcp",
                "tls": True,
                "udp": True,
                "flow": node.get("flow", "xtls-rprx-vision"),
                "servername": node.get("servername", "gateway.icloud.com"),
                "client-fingerprint": node.get("client_fingerprint", "chrome"),
                "reality-opts": {
                    "public-key": node.get("public_key", ""),
                    "short-id": node.get("short_id", "")
                }
            }
        ],
        "proxy-groups": [
            {
                "name": "PROXY",
                "type": "select",
                "proxies": [node["name"], "DIRECT"]
            },
            {
                "name": "GAMES",
                "type": "select",
                "proxies": ["DIRECT", "PROXY"]
            }
        ],
        "rules": rules
    }

    # Custom yaml dump with clean formatting
    output = yaml.dump(clash_dict, allow_unicode=True, sort_keys=False, width=120)
    return "# Generated by Smart Split-Tunneling Wizard\n\n" + output


def get_clash_verge_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """Return (app_dir, profiles_dir) if Clash Verge is installed."""
    user_appdata = Path(os.environ.get("APPDATA", ""))
    cv_dir = user_appdata / "io.github.clash-verge-rev.clash-verge-rev"
    profiles_dir = cv_dir / "profiles"

    # Search for install dir
    app_candidates = [
        Path("A:/Clash Verge"),
        Path("C:/Program Files/Clash Verge"),
        Path("C:/Program Files/Clash Verge Rev"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Clash Verge"
    ]
    app_dir = None
    for cand in app_candidates:
        if cand.is_dir() and (cand / "clash-verge.exe").exists():
            app_dir = cand
            break

    return app_dir, profiles_dir if cv_dir.is_dir() else None


def deploy_to_clash_verge(yaml_content: str, profile_name: str = "Smart Split-Tunneling") -> Dict[str, str]:
    """Save profile into Clash Verge and reload running core via IPC."""
    app_dir, profiles_dir = get_clash_verge_paths()
    if not profiles_dir or not profiles_dir.parent.is_dir():
        return {"status": "error", "message": "Папка Clash Verge не найдена в AppData"}

    try:
        profiles_dir.mkdir(parents=True, exist_ok=True)
        filename = "smart_split_tunnel.yaml"
        target_path = profiles_dir / filename
        target_path.write_text(yaml_content, encoding="utf-8")

        # Update profiles.yaml
        profiles_yaml_path = profiles_dir.parent / "profiles.yaml"
        prof_data = {"items": [], "current": "smart_split_tunnel"}
        if profiles_yaml_path.exists():
            try:
                loaded = yaml.safe_load(profiles_yaml_path.read_text(encoding="utf-8")) or {}
                if isinstance(loaded, dict):
                    prof_data = loaded
            except Exception:
                pass

        items = prof_data.get("items", [])
        # Find or create entry
        found = False
        for it in items:
            if it.get("uid") == "smart_split_tunnel" or it.get("file") == filename:
                it["file"] = filename
                it["name"] = profile_name
                it["updated"] = int(Path().stat().st_mtime) if Path().exists() else 0
                found = True
                break
        if not found:
            items.insert(0, {
                "uid": "smart_split_tunnel",
                "type": "local",
                "name": profile_name,
                "file": filename
            })

        prof_data["items"] = items
        prof_data["current"] = "smart_split_tunnel"
        profiles_yaml_path.write_text(yaml.dump(prof_data, allow_unicode=True), encoding="utf-8")

        # Also overwrite clash-verge.yaml so active config matches immediately
        clash_verge_yaml = profiles_dir.parent / "clash-verge.yaml"
        clash_verge_yaml.write_text(yaml_content, encoding="utf-8")

        # Hot reload via named pipe
        reloaded = _reload_named_pipe(clash_verge_yaml)

        return {
            "status": "success",
            "path": str(target_path),
            "reloaded": "Да (без перезапуска Clash Verge)" if reloaded else "Профиль сохранен, переключите в Clash Verge"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _reload_named_pipe(config_path: Path) -> bool:
    """Send reload IPC message to running verge-mihomo named pipe."""
    try:
        pipe_path = r"\\.\pipe\verge-mihomo"
        if not Path(pipe_path).exists():
            return False

        with open(pipe_path, "r+b", buffering=0) as pipe:
            body = json.dumps({"path": str(config_path)}).encode("utf-8")
            header = (
                f"PUT /configs?force=true HTTP/1.1\r\n"
                f"Host: localhost\r\n"
                f"Authorization: Bearer set-your-secret\r\n"
                f"Content-Type: application/json; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n\r\n"
            ).encode("ascii")
            pipe.write(header + body)

        # Flush connections
        with open(pipe_path, "r+b", buffering=0) as pipe:
            flush_req = (
                "DELETE /connections HTTP/1.1\r\n"
                "Host: localhost\r\n"
                "Authorization: Bearer set-your-secret\r\n"
                "Content-Length: 0\r\n\r\n"
            ).encode("ascii")
            pipe.write(flush_req)
        return True
    except Exception:
        return False
