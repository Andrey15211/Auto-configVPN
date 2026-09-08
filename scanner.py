import os
import re
import sys
import winreg
from pathlib import Path
from typing import List, Dict, Set

IGNORE_EXE_NAMES = {
    "unitycrashhandler64.exe", "unitycrashhandler32.exe", "crashpad_handler.exe",
    "crashreport.exe", "dxsetup.exe", "vcredist_x64.exe", "vcredist_x86.exe",
    "unins000.exe", "uninstall.exe", "steamerrorreporter.exe", "steam.exe",
    "epicgameslauncher.exe", "easyanticheat.exe", "easyanticheat_eos.exe",
    "battlenet.exe", "riotclientservices.exe", "launcher.exe"
}

def _clean_name(name: str) -> str:
    name = re.sub(r"[\xa0\t\r\n]+", " ", name)
    return name.strip()

def find_steam_libraries() -> List[Path]:
    libraries = []
    steam_root = None
    for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root_key, r"Software\Valve\Steam") as key:
                val, _ = winreg.QueryValueEx(key, "SteamPath")
                if val:
                    steam_root = Path(val)
                    break
        except OSError:
            pass

    candidates = [
        steam_root,
        Path("A:/Steam"),
        Path("C:/Program Files (x86)/Steam"),
        Path("C:/Steam"),
        Path("D:/Steam"),
        Path("E:/Steam")
    ]

    for cand in candidates:
        if cand and cand.is_dir() and (cand / "steam.exe").exists():
            vdf_path = cand / "steamapps" / "libraryfolders.vdf"
            if vdf_path.exists():
                libraries.append(cand)
                try:
                    content = vdf_path.read_text(encoding="utf-8", errors="ignore")
                    matches = re.findall(r'"path"\s+"([^"]+)"', content)
                    for m in matches:
                        p = Path(m.replace("\\\\", "/"))
                        if p.is_dir() and p not in libraries:
                            libraries.append(p)
                except Exception:
                    pass
            break

    for drive in ["C", "D", "E", "A", "B"]:
        p = Path(f"{drive}:/SteamLibrary")
        if p.is_dir() and p not in libraries:
            libraries.append(p)

    return libraries

def scan_steam_games() -> List[Dict[str, str]]:
    games = []
    seen_exes = set()
    libraries = find_steam_libraries()

    for lib in libraries:
        steamapps = lib / "steamapps"
        if not steamapps.is_dir():
            continue

        manifests = list(steamapps.glob("appmanifest_*.acf"))
        for manifest in manifests:
            try:
                text = manifest.read_text(encoding="utf-8", errors="ignore")
                name_match = re.search(r'"name"\s+"([^"]+)"', text)
                dir_match = re.search(r'"installdir"\s+"([^"]+)"', text)

                if not name_match or not dir_match:
                    continue

                game_name = _clean_name(name_match.group(1))
                install_dir = dir_match.group(1)

                if "Steamworks Common" in game_name or "SteamVR" in game_name:
                    continue

                game_path = steamapps / "common" / install_dir
                if not game_path.is_dir():
                    continue

                exe_candidates = []
                for root, _, files in os.walk(str(game_path)):
                    rel = os.path.relpath(root, str(game_path))
                    if rel.count(os.sep) > 3:
                        continue
                    for f in files:
                        if f.lower().endswith(".exe"):
                            fl = f.lower()
                            if fl not in IGNORE_EXE_NAMES and not fl.startswith("crash"):
                                exe_candidates.append((Path(root) / f, f))

                if not exe_candidates:
                    continue

                best_exe = None
                clean_dir = re.sub(r"[^a-zA-Z0-9]", "", install_dir.lower())
                for full_p, fname in exe_candidates:
                    fn_clean = re.sub(r"[^a-zA-Z0-9]", "", fname.lower().replace(".exe", ""))
                    if fn_clean in clean_dir or clean_dir in fn_clean:
                        best_exe = (full_p, fname)
                        break

                if not best_exe:
                    exe_candidates.sort(key=lambda x: x[0].stat().st_size if x[0].exists() else 0, reverse=True)
                    best_exe = exe_candidates[0]

                exe_name = best_exe[1]
                if exe_name.lower() not in seen_exes:
                    seen_exes.add(exe_name.lower())
                    games.append({
                        "name": game_name,
                        "exe": exe_name,
                        "path": str(best_exe[0]),
                        "source": "Steam"
                    })
            except Exception:
                continue

    return games

def scan_epic_games() -> List[Dict[str, str]]:
    games = []
    manifest_dir = Path("C:/ProgramData/Epic/EpicGamesLauncher/Data/Manifests")
    if not manifest_dir.is_dir():
        return games

    for item in manifest_dir.glob("*.item"):
        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
            title = re.search(r'"DisplayName":\s*"([^"]+)"', text)
            exe = re.search(r'"LaunchExecutable":\s*"([^"]+)"', text)
            install_loc = re.search(r'"InstallLocation":\s*"([^"]+)"', text)
            if title and exe:
                name = _clean_name(title.group(1))
                exe_name = Path(exe.group(1)).name
                loc = install_loc.group(1) if install_loc else ""
                games.append({
                    "name": name,
                    "exe": exe_name,
                    "path": os.path.join(loc, exe.group(1)) if loc else exe_name,
                    "source": "Epic Games"
                })
        except Exception:
            continue
    return games

def scan_standalone_and_registry_games() -> List[Dict[str, str]]:
    games = []
    seen_names = set()

    known_paths = [
        Path("C:/Games"),
        Path("D:/Games"),
        Path("A:/Games"),
        Path("A:/Battle.net"),
        Path("C:/Program Files (x86)/Battle.net"),
        Path("C:/Riot Games"),
        Path("A:/PrismLauncher")
    ]

    for base in known_paths:
        if not base.is_dir():
            continue
        if base.name.lower() in ("battle.net", "prismlauncher"):
            for f in base.glob("*.exe"):
                fl = f.name.lower()
                if fl not in IGNORE_EXE_NAMES:
                    games.append({
                        "name": base.name,
                        "exe": f.name,
                        "path": str(f),
                        "source": "Launcher"
                    })
            continue

        for sub in base.iterdir():
            if not sub.is_dir():
                continue
            exes = [f for f in sub.glob("*.exe") if f.name.lower() not in IGNORE_EXE_NAMES]
            if exes:
                exes.sort(key=lambda x: x.stat().st_size if x.exists() else 0, reverse=True)
                best = exes[0]
                games.append({
                    "name": sub.name,
                    "exe": best.name,
                    "path": str(best),
                    "source": "Standalone"
                })

    game_keywords = ["game", "play", "soul", "hearthstone", "craft", "warfare", "overwatch",
                     "roblox", "strike", "dota", "valve", "blizzard", "ubisoft", "ea games"]
    reg_locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for root_k, sub_k in reg_locations:
        try:
            with winreg.OpenKey(root_k, sub_k) as parent:
                num_subkeys = winreg.QueryInfoKey(parent)[0]
                for i in range(num_subkeys):
                    try:
                        k_name = winreg.EnumKey(parent, i)
                        with winreg.OpenKey(parent, k_name) as child:
                            try:
                                d_name, _ = winreg.QueryValueEx(child, "DisplayName")
                            except OSError:
                                continue
                            if not d_name or len(d_name) < 3:
                                continue
                            dl = d_name.lower()
                            if any(w in dl for w in game_keywords):
                                try:
                                    loc, _ = winreg.QueryValueEx(child, "InstallLocation")
                                except OSError:
                                    loc = None
                                try:
                                    icon, _ = winreg.QueryValueEx(child, "DisplayIcon")
                                except OSError:
                                    icon = None

                                target_exe = None
                                if icon and icon.lower().endswith(".exe") and Path(icon).exists():
                                    target_exe = Path(icon)
                                elif loc and Path(loc).is_dir():
                                    exes = [f for f in Path(loc).glob("*.exe") if f.name.lower() not in IGNORE_EXE_NAMES]
                                    if exes:
                                        exes.sort(key=lambda x: x.stat().st_size if x.exists() else 0, reverse=True)
                                        target_exe = exes[0]

                                if target_exe and target_exe.name.lower() not in IGNORE_EXE_NAMES:
                                    g_name = _clean_name(d_name)
                                    if g_name.lower() not in seen_names:
                                        seen_names.add(g_name.lower())
                                        games.append({
                                            "name": g_name,
                                            "exe": target_exe.name,
                                            "path": str(target_exe),
                                            "source": "Registry"
                                        })
                    except OSError:
                        continue
        except OSError:
            pass

    return games

def scan_all_games() -> List[Dict[str, str]]:
    results = []
    seen_exes: Set[str] = set()

    for g in scan_steam_games():
        ex = g["exe"].lower()
        if ex not in seen_exes:
            seen_exes.add(ex)
            results.append(g)

    for g in scan_epic_games():
        ex = g["exe"].lower()
        if ex not in seen_exes:
            seen_exes.add(ex)
            results.append(g)

    for g in scan_standalone_and_registry_games():
        ex = g["exe"].lower()
        if ex not in seen_exes:
            seen_exes.add(ex)
            results.append(g)

    results.sort(key=lambda x: x["name"].lower())
    return results

if __name__ == "__main__":
    found = scan_all_games()
    print(f"Total games detected: {len(found)}")
    for item in found:
        print(f"[{item['source']:<10}] {item['name']:<35} -> {item['exe']}")
