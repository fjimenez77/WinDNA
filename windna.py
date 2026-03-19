#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║          🧬  W i n D N A   v 1               ║
║    Capture  -  Deploy  -  Clone Your PC      ║
╠══════════════════════════════════════════════╣
║  Author:   cyberspartan77                    ║
║  Version:  1.0 (Interactive Menu)            ║
║  Date:     March 2026                        ║
╠══════════════════════════════════════════════╣
║  Captures your Windows PC's full config DNA  ║
║  and deploys it to any new machine.          ║
║                                              ║
║  Just run: python windna.py                  ║
╚══════════════════════════════════════════════╝
"""

import subprocess
import json
import os
import sys
import shutil
import platform
import datetime
import glob as globmod
import re
import getpass
import hashlib
from pathlib import Path

try:
    import securityaudit_win
except ImportError:
    securityaudit_win = None

# ═══════════════════════════════════════════════
#  TERMINAL UI
# ═══════════════════════════════════════════════

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_BLUE = "\033[44m"
BG_RESET = "\033[49m"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(APP_DIR, "profiles")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

# ═══════════════════════════════════════════════
#  ARCHITECTURE DETECTION
# ═══════════════════════════════════════════════

def detect_architecture():
    """Detect Windows CPU architecture."""
    machine = platform.machine().lower()
    arch_env = os.environ.get("PROCESSOR_ARCHITECTURE", "").lower()
    arch_w6432 = os.environ.get("PROCESSOR_ARCHITEW6432", "").lower()

    if "arm" in machine or "aarch64" in machine or "arm" in arch_env:
        return "ARM64"
    elif "amd64" in machine or "x86_64" in machine or "amd64" in arch_env or "amd64" in arch_w6432:
        return "x64"
    else:
        return "x86"


def get_system32_path():
    """Return the appropriate System32 path based on architecture."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    arch = detect_architecture()
    if arch == "x86":
        syswow = os.path.join(windir, "SysWOW64")
        if os.path.isdir(syswow):
            return syswow
    return os.path.join(windir, "System32")


ARCH = detect_architecture()

# ═══════════════════════════════════════════════
#  SETTINGS ENGINE
# ═══════════════════════════════════════════════

DEFAULT_SETTINGS = {
    "profile_save_location": "",           # blank = ./profiles/
    "auto_backup_before_deploy": True,
    "dry_run_by_default": False,
    "compact_json": False,
    "color_output": True,
    "confirm_before_apply": True,
    "auto_name_profiles": False,
    "backup_directory": "",                # blank = ~/.windna_backup/
    "default_capture_categories": "all",   # "all" or comma-separated keys
    "security_audit_with_capture": False,
    "threat_alert_level": "medium",        # low, medium, high
}


def load_settings():
    """Load settings from disk, merging with defaults for any missing keys."""
    settings = dict(DEFAULT_SETTINGS)
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    return settings


def save_settings(settings):
    """Write settings to disk."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_profiles_dir(settings):
    """Return the effective profiles directory."""
    custom = settings.get("profile_save_location", "").strip()
    return custom if custom else PROFILES_DIR


def get_backup_dir(settings):
    """Return the effective backup directory."""
    custom = settings.get("backup_directory", "").strip()
    return custom if custom else os.path.expanduser("~/.windna_backup")


# ═══════════════════════════════════════════════
#  TERMINAL HELPERS
# ═══════════════════════════════════════════════

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    w = 46  # inner width between the box walls
    top    = "  \u2554" + "\u2550" * w + "\u2557"
    bottom = "  \u255a" + "\u2550" * w + "\u255d"
    mid    = "  \u2560" + "\u2550" * w + "\u2563"

    l1_text = "\U0001f9ec  W i n D N A   v 1"
    l2_text = "Capture  -  Deploy  -  Clone Your PC"
    l3_text = "Author: cyberspartan77  |  v1.0  |  2026"

    # Pad accounting for emoji (2 display cols but 1 char)
    line1 = "  \u2551" + l1_text.center(w)[:-1] + "\u2551"
    line2 = "  \u2551" + l2_text.center(w) + "\u2551"
    line3 = "  \u2551" + l3_text.center(w) + "\u2551"

    print(f"""
{CYAN}{BOLD}{top}
{line1}
{line2}
{mid}
{line3}
{bottom}{RESET}
""")


def divider(title=""):
    dash = "\u2500"
    if title:
        trail = dash * (40 - len(title))
        print(f"\n  {CYAN}{dash*3} {BOLD}{title} {trail}{RESET}")
    else:
        print(f"  {DIM}{dash*48}{RESET}")


def status(icon, msg, detail=""):
    d = f" {DIM}{detail}{RESET}" if detail else ""
    print(f"  {icon}  {msg}{d}")


def success(msg, detail=""):
    status(f"{GREEN}\u2713{RESET}", msg, detail)


def fail(msg, detail=""):
    status(f"{RED}\u2717{RESET}", msg, detail)


def warn(msg, detail=""):
    status(f"{YELLOW}!{RESET}", msg, detail)


def info(msg, detail=""):
    status(f"{CYAN}i{RESET}", msg, detail)


def spinner_line(msg):
    sys.stdout.write(f"\r  {YELLOW}\u23f3{RESET} {msg}...")
    sys.stdout.flush()


def spinner_done(msg):
    print(f"\r  {GREEN}\u2713{RESET}  {msg}        ")


def spinner_fail(msg, err=""):
    e = f" \u2014 {err}" if err else ""
    print(f"\r  {RED}\u2717{RESET}  {msg}{e}        ")


def prompt(msg, default=""):
    d = f" [{default}]" if default else ""
    try:
        val = input(f"\n  {CYAN}>{RESET} {msg}{d}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
    return val or default


def pause():
    try:
        input(f"\n  {DIM}Press Enter to continue...{RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


def show_menu(title, options, show_back=True):
    """Display a numbered menu and return the user's choice (1-based) or 0 for back/quit."""
    clear_screen()
    banner()
    divider(title)
    print()
    for i, (label, desc) in enumerate(options, 1):
        print(f"    {BOLD}{CYAN}{i}{RESET}  {label}")
        if desc:
            print(f"       {DIM}{desc}{RESET}")
    if show_back:
        print(f"\n    {BOLD}{CYAN}0{RESET}  {DIM}{'Back' if show_back else 'Quit'}{RESET}")
    print()

    choice = prompt("Choose an option")
    try:
        return int(choice)
    except (ValueError, TypeError):
        return -1


def show_checklist(title, items, preselect_all=True):
    """
    Interactive checklist. User toggles items by number, then confirms.
    items: list of (key, label) tuples
    Returns list of selected keys.
    """
    selected = set(range(len(items))) if preselect_all else set()

    while True:
        clear_screen()
        banner()
        divider(title)
        print(f"  {DIM}Toggle items by number. Press A=all, N=none, Enter=confirm.{RESET}\n")

        for i, (key, label) in enumerate(items):
            mark = f"{GREEN}[x]{RESET}" if i in selected else f"{DIM}[ ]{RESET}"
            print(f"    {mark} {BOLD}{i + 1}{RESET}  {label}")

        print(f"\n  {DIM}Selected: {len(selected)}/{len(items)}{RESET}")
        choice = prompt("Toggle # / A=all / N=none / Enter=GO")

        if choice == "":
            break
        elif choice.upper() == "A":
            selected = set(range(len(items)))
        elif choice.upper() == "N":
            selected.clear()
        else:
            try:
                nums = [int(x.strip()) - 1 for x in choice.replace(",", " ").split()]
                for n in nums:
                    if 0 <= n < len(items):
                        selected.symmetric_difference_update({n})
            except ValueError:
                pass

    return [items[i][0] for i in sorted(selected)]


# ═══════════════════════════════════════════════
#  SHELL HELPERS
# ═══════════════════════════════════════════════

def _run(cmd, timeout=30):
    """Run a shell command and return stdout. Uses shell=True for cmd commands."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""


def _run_ps(cmd, timeout=30):
    """Run a PowerShell command and return stdout."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""


def _reg_query(key, value=None):
    """Query a Windows registry key. Returns the value data as a string, or empty string on error."""
    try:
        if value:
            cmd = f'reg query "{key}" /v "{value}" 2>nul'
        else:
            cmd = f'reg query "{key}" 2>nul'
        result = _run(cmd)
        if not result:
            return ""
        if value:
            # Parse the output: look for the line containing the value name
            for line in result.splitlines():
                line = line.strip()
                if value.lower() in line.lower():
                    parts = line.split(None, 2)
                    if len(parts) >= 3:
                        return parts[2]
            return ""
        return result
    except Exception:
        return ""


def _reg_add(key, value_name, value_data, reg_type="REG_DWORD"):
    """Write a registry value. Returns True on success."""
    try:
        cmd = f'reg add "{key}" /v "{value_name}" /t {reg_type} /d "{value_data}" /f 2>nul'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


# ═══════════════════════════════════════════════
#  CAPTURE MODULES
# ═══════════════════════════════════════════════

def capture_machine_identity():
    """Capture hostname, Windows version/build, architecture, domain, serial."""
    hostname = platform.node()
    win_ver = platform.version()
    win_release = platform.release()
    win_edition = _run_ps("(Get-WmiObject Win32_OperatingSystem).Caption")
    build = _run('ver')

    # Serial number
    serial = _run('wmic bios get serialnumber /format:value')
    serial = serial.replace("SerialNumber=", "").strip() if serial else ""

    # Domain info
    domain = os.environ.get("USERDOMAIN", "")
    dns_domain = os.environ.get("USERDNSDOMAIN", "")

    # System info details
    system_model = _run_ps("(Get-WmiObject Win32_ComputerSystem).Model")
    manufacturer = _run_ps("(Get-WmiObject Win32_ComputerSystem).Manufacturer")

    # Total RAM
    total_ram = _run_ps("[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)")

    return {
        "captured_at": datetime.datetime.now().isoformat(),
        "hostname": hostname,
        "windows_edition": win_edition,
        "windows_version": win_release,
        "windows_build": win_ver,
        "architecture": ARCH,
        "domain": domain,
        "dns_domain": dns_domain,
        "serial_number": serial,
        "manufacturer": manufacturer,
        "model": system_model,
        "total_ram_gb": total_ram,
        "username": getpass.getuser(),
        "python_version": platform.python_version(),
    }


def capture_desktop_appearance():
    """Capture wallpaper, theme, colors, DPI, taskbar position."""
    wallpaper = _reg_query(r"HKCU\Control Panel\Desktop", "Wallpaper")
    wallpaper_style = _reg_query(r"HKCU\Control Panel\Desktop", "WallpaperStyle")
    tile_wallpaper = _reg_query(r"HKCU\Control Panel\Desktop", "TileWallpaper")

    # Theme / dark mode
    apps_use_light = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme")
    system_uses_light = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme")
    color_prevalence = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "ColorPrevalence")
    transparency = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency")

    # Accent color
    accent_color = _reg_query(r"HKCU\Software\Microsoft\Windows\DWM", "AccentColor")
    colorization = _reg_query(r"HKCU\Software\Microsoft\Windows\DWM", "ColorizationColor")

    # DPI scaling
    dpi = _reg_query(r"HKCU\Control Panel\Desktop", "LogPixels")
    dpi_scaling = _reg_query(r"HKCU\Control Panel\Desktop", "Win8DpiScaling")

    # Current theme file
    current_theme = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes", "CurrentTheme")

    return {
        "wallpaper": wallpaper,
        "wallpaper_style": wallpaper_style,
        "tile_wallpaper": tile_wallpaper,
        "dark_mode_apps": apps_use_light == "0x0" if apps_use_light else None,
        "dark_mode_system": system_uses_light == "0x0" if system_uses_light else None,
        "color_on_titlebar": color_prevalence,
        "transparency_effects": transparency,
        "accent_color": accent_color,
        "colorization": colorization,
        "dpi": dpi,
        "dpi_scaling": dpi_scaling,
        "current_theme": current_theme,
    }


def capture_taskbar_start():
    """Capture taskbar alignment, size, auto-hide, system tray settings."""
    adv_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

    taskbar_al = _reg_query(adv_key, "TaskbarAl")           # 0=left, 1=center (Win11)
    taskbar_da = _reg_query(adv_key, "TaskbarDa")           # 0=hide widgets
    taskbar_mn = _reg_query(adv_key, "TaskbarMn")           # 0=hide chat
    taskbar_si = _reg_query(adv_key, "TaskbarSi")           # taskbar size
    show_task_view = _reg_query(adv_key, "ShowTaskViewButton")
    search_mode = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search", "SearchboxTaskbarMode")

    # Auto-hide
    stuckplace_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
    # Auto-hide is stored in binary Settings value; we'll just note whether it's configured
    autohide_raw = _reg_query(stuckplace_key, "Settings")
    # Quick heuristic: if the raw data exists we capture it but note it's binary
    autohide = None
    if autohide_raw:
        autohide = "(binary data captured)"

    # System tray icons
    show_seconds = _reg_query(adv_key, "ShowSecondsInSystemClock")
    hide_sca = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer", "EnableAutoTray")

    return {
        "taskbar_alignment": "center" if taskbar_al == "0x1" else "left" if taskbar_al == "0x0" else taskbar_al,
        "taskbar_size": taskbar_si,
        "taskbar_widgets": taskbar_da,
        "taskbar_chat": taskbar_mn,
        "show_task_view": show_task_view,
        "search_mode": search_mode,
        "autohide": autohide,
        "show_seconds_in_clock": show_seconds,
        "auto_hide_tray_icons": hide_sca,
    }


def capture_file_explorer():
    """Capture File Explorer preferences."""
    adv_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

    hidden = _reg_query(adv_key, "Hidden")                   # 1=show, 2=hide
    hide_ext = _reg_query(adv_key, "HideFileExt")            # 0=show, 1=hide
    hide_drives = _reg_query(adv_key, "HideDrivesWithNoMedia")
    launch_to = _reg_query(adv_key, "LaunchTo")              # 1=This PC, 2=Quick Access
    show_compact = _reg_query(adv_key, "UseCompactMode")
    sep_process = _reg_query(adv_key, "SeparateProcess")
    show_merge = _reg_query(adv_key, "TaskbarGlomLevel")
    show_full_path = _reg_query(adv_key, "FullPath")
    show_status_bar = _reg_query(adv_key, "ShowStatusBar")

    # Recent files / frequent folders
    show_recent = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer", "ShowRecent")
    show_frequent = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer", "ShowFrequent")

    # Ribbon minimized
    ribbon_minimized = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Ribbon", "MinimizedStateTabletModeOff")

    return {
        "show_hidden_files": hidden == "0x1" if hidden else None,
        "show_file_extensions": hide_ext == "0x0" if hide_ext else None,
        "hide_drives_no_media": hide_drives,
        "launch_to": "This PC" if launch_to == "0x1" else "Quick Access" if launch_to == "0x2" else launch_to,
        "use_compact_mode": show_compact,
        "separate_process": sep_process,
        "show_full_path": show_full_path,
        "show_status_bar": show_status_bar,
        "show_recent_files": show_recent,
        "show_frequent_folders": show_frequent,
        "ribbon_minimized": ribbon_minimized,
    }


def capture_mouse_keyboard():
    """Capture mouse and keyboard settings."""
    # Mouse
    mouse_speed = _reg_query(r"HKCU\Control Panel\Mouse", "MouseSpeed")
    mouse_threshold1 = _reg_query(r"HKCU\Control Panel\Mouse", "MouseThreshold1")
    mouse_threshold2 = _reg_query(r"HKCU\Control Panel\Mouse", "MouseThreshold2")
    mouse_sensitivity = _reg_query(r"HKCU\Control Panel\Mouse", "MouseSensitivity")
    swap_buttons = _reg_query(r"HKCU\Control Panel\Mouse", "SwapMouseButtons")
    scroll_lines = _reg_query(r"HKCU\Control Panel\Desktop", "WheelScrollLines")
    double_click_speed = _reg_query(r"HKCU\Control Panel\Mouse", "DoubleClickSpeed")

    # Keyboard
    key_repeat_speed = _reg_query(r"HKCU\Control Panel\Keyboard", "KeyboardSpeed")
    key_repeat_delay = _reg_query(r"HKCU\Control Panel\Keyboard", "KeyboardDelay")

    # Cursor blink rate
    cursor_blink = _reg_query(r"HKCU\Control Panel\Desktop", "CursorBlinkRate")

    return {
        "mouse": {
            "speed": mouse_speed,
            "threshold1": mouse_threshold1,
            "threshold2": mouse_threshold2,
            "sensitivity": mouse_sensitivity,
            "swap_buttons": swap_buttons == "1" if swap_buttons else False,
            "scroll_lines": scroll_lines,
            "double_click_speed": double_click_speed,
        },
        "keyboard": {
            "repeat_speed": key_repeat_speed,
            "repeat_delay": key_repeat_delay,
            "cursor_blink_rate": cursor_blink,
        },
    }


def capture_sound_notifications():
    """Capture system sounds scheme and notification settings."""
    # Sound scheme
    sound_scheme = _reg_query(r"HKCU\AppEvents\Schemes", "")
    # The default value line from reg query
    if sound_scheme:
        # Try to extract the (Default) value
        for line in sound_scheme.splitlines():
            if "(Default)" in line:
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    sound_scheme = parts[2]
                    break

    # Focus assist / quiet hours
    focus_assist = _reg_query(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.notifications.quiethourssettings",
        "Data"
    )

    # Notifications enabled
    notifications_enabled = _reg_query(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications",
        "ToastEnabled"
    )

    # Sound on notifications
    sounds_on_notify = _reg_query(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings",
        "NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND"
    )

    return {
        "sound_scheme": sound_scheme,
        "focus_assist": "(binary)" if focus_assist else "not configured",
        "notifications_enabled": notifications_enabled,
        "notification_sounds": sounds_on_notify,
    }


def capture_power_sleep():
    """Capture power plan, sleep timeouts, hibernate, lid close action."""
    # Active power plan
    active_plan = _run("powercfg /getactivescheme")
    plan_guid = ""
    plan_name = ""
    if active_plan:
        # Format: "Power Scheme GUID: 381b4222-... (Balanced)"
        match = re.search(r"GUID:\s*(\S+)\s*\((.+?)\)", active_plan)
        if match:
            plan_guid = match.group(1)
            plan_name = match.group(2)

    # List all plans
    all_plans_raw = _run("powercfg /list")
    all_plans = []
    if all_plans_raw:
        for line in all_plans_raw.splitlines():
            m = re.search(r"GUID:\s*(\S+)\s*\((.+?)\)", line)
            if m:
                active = "*" in line
                all_plans.append({"guid": m.group(1), "name": m.group(2), "active": active})

    # Hibernate status
    hibernate_raw = _run("powercfg /hibernate")
    hibernate_enabled = _run_ps("(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power' -Name HibernateEnabled -ErrorAction SilentlyContinue).HibernateEnabled")

    # Sleep timeouts (AC and DC)
    sleep_ac = _run_ps("(powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'Current AC').ToString()")
    sleep_dc = _run_ps("(powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'Current DC').ToString()")

    # Screen timeout
    screen_ac = _run_ps("(powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String 'Current AC').ToString()")
    screen_dc = _run_ps("(powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String 'Current DC').ToString()")

    # Lid close action
    lid_ac = _run_ps("(powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION | Select-String 'Current AC').ToString()")
    lid_dc = _run_ps("(powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION | Select-String 'Current DC').ToString()")

    return {
        "active_plan": plan_name,
        "active_plan_guid": plan_guid,
        "all_plans": all_plans,
        "hibernate_enabled": hibernate_enabled == "1" if hibernate_enabled else None,
        "sleep_timeout_ac": sleep_ac,
        "sleep_timeout_dc": sleep_dc,
        "screen_timeout_ac": screen_ac,
        "screen_timeout_dc": screen_dc,
        "lid_close_ac": lid_ac,
        "lid_close_dc": lid_dc,
    }


def capture_network():
    """Capture Wi-Fi profiles, DNS, proxy settings."""
    # Wi-Fi profiles
    wifi_profiles = []
    profiles_raw = _run("netsh wlan show profiles")
    if profiles_raw:
        for line in profiles_raw.splitlines():
            match = re.search(r":\s*(.+)$", line)
            if match and "All User Profile" in line:
                wifi_profiles.append(match.group(1).strip())

    # Current Wi-Fi connection
    current_wifi = ""
    wlan_raw = _run("netsh wlan show interfaces")
    if wlan_raw:
        for line in wlan_raw.splitlines():
            if "SSID" in line and "BSSID" not in line:
                match = re.search(r":\s*(.+)$", line)
                if match:
                    current_wifi = match.group(1).strip()
                    break

    # DNS servers
    dns_raw = _run("netsh interface ip show dns")
    dns_servers = []
    if dns_raw:
        for line in dns_raw.splitlines():
            line = line.strip()
            # Match IP addresses in dns output
            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if ip_match:
                dns_servers.append(ip_match.group(1))

    # Proxy settings
    proxy_enable = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyEnable")
    proxy_server = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyServer")
    proxy_override = _reg_query(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings", "ProxyOverride")

    # IP configuration summary
    ipconfig = _run("ipconfig /all")
    ip_addresses = []
    if ipconfig:
        for line in ipconfig.splitlines():
            if "IPv4 Address" in line or "IPv4" in line:
                match = re.search(r":\s*([\d.]+)", line)
                if match:
                    ip_addresses.append(match.group(1))

    return {
        "wifi_profiles": wifi_profiles,
        "current_wifi": current_wifi,
        "dns_servers": list(set(dns_servers)),
        "proxy_enabled": proxy_enable == "0x1" if proxy_enable else False,
        "proxy_server": proxy_server,
        "proxy_bypass": proxy_override,
        "ip_addresses": ip_addresses,
    }


def capture_privacy_security():
    """Capture location, camera, microphone permission settings."""
    consent_base = r"HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"

    categories = {
        "location": "location",
        "camera": "webcam",
        "microphone": "microphone",
        "notifications": "userNotificationListener",
        "contacts": "contacts",
        "calendar": "appointments",
        "call_history": "phoneCallHistory",
        "email": "email",
        "documents": "documentsLibrary",
        "pictures": "picturesLibrary",
        "videos": "videosLibrary",
        "file_system": "broadFileSystemAccess",
    }

    permissions = {}
    for friendly, reg_name in categories.items():
        val = _reg_query(f"{consent_base}\\{reg_name}", "Value")
        permissions[friendly] = val if val else "not configured"

    # Windows Defender status
    defender = _run_ps("Get-MpComputerStatus | Select-Object -Property AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | ConvertTo-Json")
    defender_data = {}
    if defender:
        try:
            defender_data = json.loads(defender)
        except Exception:
            defender_data = {"raw": defender}

    # Firewall status
    fw_domain = _run_ps("(Get-NetFirewallProfile -Name Domain).Enabled")
    fw_private = _run_ps("(Get-NetFirewallProfile -Name Private).Enabled")
    fw_public = _run_ps("(Get-NetFirewallProfile -Name Public).Enabled")

    # UAC level
    uac_level = _reg_query(r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "ConsentPromptBehaviorAdmin")

    return {
        "permissions": permissions,
        "defender": defender_data,
        "firewall": {
            "domain": fw_domain,
            "private": fw_private,
            "public": fw_public,
        },
        "uac_level": uac_level,
    }


def capture_installed_apps():
    """Capture installed applications from multiple sources."""
    # Windows Store apps (AppX)
    store_apps = []
    appx_raw = _run_ps("Get-AppxPackage | Select-Object Name,Version,PackageFamilyName | ConvertTo-Json")
    if appx_raw:
        try:
            appx_list = json.loads(appx_raw)
            if isinstance(appx_list, dict):
                appx_list = [appx_list]
            for app in appx_list:
                store_apps.append({
                    "name": app.get("Name", ""),
                    "version": app.get("Version", ""),
                })
        except Exception:
            pass

    # Traditional programs (Win32)
    traditional_apps = []
    # Try the registry approach (faster and more reliable than wmic)
    for reg_path in [
        r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    ]:
        raw = _run_ps(
            f"Get-ItemProperty 'Registry::{reg_path}\\*' -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.DisplayName }} | "
            f"Select-Object DisplayName,DisplayVersion,Publisher | "
            f"ConvertTo-Json"
        )
        if raw:
            try:
                items = json.loads(raw)
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    name = item.get("DisplayName", "")
                    if name and name not in [a.get("name") for a in traditional_apps]:
                        traditional_apps.append({
                            "name": name,
                            "version": item.get("DisplayVersion", ""),
                            "publisher": item.get("Publisher", ""),
                        })
            except Exception:
                pass

    # Winget list (if available)
    winget_apps = []
    if shutil.which("winget"):
        winget_raw = _run("winget list --disable-interactivity 2>nul", timeout=60)
        if winget_raw:
            lines = winget_raw.splitlines()
            # Skip header lines (usually first 2-3 lines with dashes)
            data_started = False
            for line in lines:
                if "---" in line:
                    data_started = True
                    continue
                if data_started and line.strip():
                    winget_apps.append(line.strip())

    return {
        "store_apps": store_apps,
        "traditional_apps": sorted(traditional_apps, key=lambda x: x.get("name", "").lower()),
        "winget_list": winget_apps[:100],  # Cap at 100 to avoid huge profiles
        "total_store_apps": len(store_apps),
        "total_traditional_apps": len(traditional_apps),
    }


# All capture modules
CAPTURE_MODULES = [
    ("machine_identity",      "Machine Identity",        capture_machine_identity),
    ("desktop_appearance",    "Desktop & Appearance",     capture_desktop_appearance),
    ("taskbar_start",         "Taskbar & Start Menu",     capture_taskbar_start),
    ("file_explorer",         "File Explorer",            capture_file_explorer),
    ("mouse_keyboard",        "Mouse & Keyboard",         capture_mouse_keyboard),
    ("sound_notifications",   "Sound & Notifications",    capture_sound_notifications),
    ("power_sleep",           "Power & Sleep",            capture_power_sleep),
    ("network",               "Network",                  capture_network),
    ("privacy_security",      "Privacy & Security",       capture_privacy_security),
    ("installed_apps",        "Installed Apps",            capture_installed_apps),
]


# ═══════════════════════════════════════════════
#  DEPLOY MODULES
# ═══════════════════════════════════════════════

def deploy_desktop_appearance(data, dry_run=False):
    """Deploy wallpaper, theme, colors, dark mode."""
    results = []
    actions = []

    if data.get("wallpaper"):
        actions.append((
            f"Wallpaper -> {data['wallpaper']}",
            r"HKCU\Control Panel\Desktop", "Wallpaper", data["wallpaper"], "REG_SZ"
        ))
    if data.get("wallpaper_style"):
        actions.append((
            f"Wallpaper Style -> {data['wallpaper_style']}",
            r"HKCU\Control Panel\Desktop", "WallpaperStyle", data["wallpaper_style"], "REG_SZ"
        ))

    dark_apps = data.get("dark_mode_apps")
    if dark_apps is not None:
        val = "0" if dark_apps else "1"
        actions.append((
            f"Dark Mode (Apps) -> {'ON' if dark_apps else 'OFF'}",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "AppsUseLightTheme", val, "REG_DWORD"
        ))

    dark_sys = data.get("dark_mode_system")
    if dark_sys is not None:
        val = "0" if dark_sys else "1"
        actions.append((
            f"Dark Mode (System) -> {'ON' if dark_sys else 'OFF'}",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "SystemUsesLightTheme", val, "REG_DWORD"
        ))

    if data.get("transparency_effects"):
        actions.append((
            f"Transparency -> {data['transparency_effects']}",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "EnableTransparency", data["transparency_effects"], "REG_DWORD"
        ))

    for label, key, vname, vdata, rtype in actions:
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            ok = _reg_add(key, vname, vdata, rtype)
            if ok:
                success(label)
            else:
                fail(label)
        results.append(label)

    if not dry_run and results:
        # Refresh the desktop
        _run_ps("RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True")
        info("Desktop refreshed")

    return results


def deploy_file_explorer(data, dry_run=False):
    """Deploy File Explorer settings."""
    results = []
    adv_key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    actions = []

    if data.get("show_hidden_files") is not None:
        val = "1" if data["show_hidden_files"] else "2"
        actions.append((f"Show Hidden Files -> {'ON' if data['show_hidden_files'] else 'OFF'}", adv_key, "Hidden", val, "REG_DWORD"))

    if data.get("show_file_extensions") is not None:
        val = "0" if data["show_file_extensions"] else "1"
        actions.append((f"Show File Extensions -> {'ON' if data['show_file_extensions'] else 'OFF'}", adv_key, "HideFileExt", val, "REG_DWORD"))

    if data.get("launch_to"):
        val = "1" if data["launch_to"] == "This PC" else "2"
        actions.append((f"Open Explorer to -> {data['launch_to']}", adv_key, "LaunchTo", val, "REG_DWORD"))

    if data.get("use_compact_mode"):
        actions.append((f"Compact Mode -> {data['use_compact_mode']}", adv_key, "UseCompactMode", data["use_compact_mode"], "REG_DWORD"))

    if data.get("show_status_bar"):
        actions.append((f"Status Bar -> {data['show_status_bar']}", adv_key, "ShowStatusBar", data["show_status_bar"], "REG_DWORD"))

    for label, key, vname, vdata, rtype in actions:
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            ok = _reg_add(key, vname, vdata, rtype)
            if ok:
                success(label)
            else:
                fail(label)
        results.append(label)

    if not dry_run and results:
        # Restart Explorer to apply changes
        info("Restarting Explorer to apply changes...")
        _run("taskkill /f /im explorer.exe >nul 2>&1 && start explorer.exe")

    return results


def deploy_mouse_keyboard(data, dry_run=False):
    """Deploy mouse and keyboard settings."""
    results = []
    actions = []

    mouse = data.get("mouse", {})
    keyboard = data.get("keyboard", {})

    if mouse.get("sensitivity"):
        actions.append(("Mouse Sensitivity -> " + mouse["sensitivity"],
                        r"HKCU\Control Panel\Mouse", "MouseSensitivity", mouse["sensitivity"], "REG_SZ"))
    if mouse.get("speed"):
        actions.append(("Mouse Speed -> " + mouse["speed"],
                        r"HKCU\Control Panel\Mouse", "MouseSpeed", mouse["speed"], "REG_SZ"))
    if mouse.get("scroll_lines"):
        actions.append(("Scroll Lines -> " + mouse["scroll_lines"],
                        r"HKCU\Control Panel\Desktop", "WheelScrollLines", mouse["scroll_lines"], "REG_SZ"))
    if mouse.get("swap_buttons") is not None:
        val = "1" if mouse["swap_buttons"] else "0"
        actions.append(("Swap Mouse Buttons -> " + ("ON" if mouse["swap_buttons"] else "OFF"),
                        r"HKCU\Control Panel\Mouse", "SwapMouseButtons", val, "REG_SZ"))
    if mouse.get("double_click_speed"):
        actions.append(("Double Click Speed -> " + mouse["double_click_speed"],
                        r"HKCU\Control Panel\Mouse", "DoubleClickSpeed", mouse["double_click_speed"], "REG_SZ"))

    if keyboard.get("repeat_speed"):
        actions.append(("Key Repeat Speed -> " + keyboard["repeat_speed"],
                        r"HKCU\Control Panel\Keyboard", "KeyboardSpeed", keyboard["repeat_speed"], "REG_SZ"))
    if keyboard.get("repeat_delay"):
        actions.append(("Key Repeat Delay -> " + keyboard["repeat_delay"],
                        r"HKCU\Control Panel\Keyboard", "KeyboardDelay", keyboard["repeat_delay"], "REG_SZ"))
    if keyboard.get("cursor_blink_rate"):
        actions.append(("Cursor Blink Rate -> " + keyboard["cursor_blink_rate"],
                        r"HKCU\Control Panel\Desktop", "CursorBlinkRate", keyboard["cursor_blink_rate"], "REG_SZ"))

    for label, key, vname, vdata, rtype in actions:
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            ok = _reg_add(key, vname, vdata, rtype)
            if ok:
                success(label)
            else:
                fail(label)
        results.append(label)

    return results


def deploy_power_sleep(data, dry_run=False):
    """Deploy power plan settings."""
    results = []

    # Set active power plan
    guid = data.get("active_plan_guid")
    name = data.get("active_plan")
    if guid:
        label = f"Set power plan -> {name} ({guid})"
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            result = _run(f'powercfg /setactive {guid}')
            success(label)
        results.append(label)

    # Hibernate
    hib = data.get("hibernate_enabled")
    if hib is not None:
        label = f"Hibernate -> {'ON' if hib else 'OFF'}"
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            _run(f'powercfg /hibernate {"on" if hib else "off"}')
            success(label)
        results.append(label)

    return results


def deploy_network(data, dry_run=False):
    """Deploy network settings (proxy, DNS)."""
    results = []

    # Proxy settings
    proxy_enabled = data.get("proxy_enabled")
    if proxy_enabled is not None:
        val = "1" if proxy_enabled else "0"
        label = f"Proxy -> {'Enabled' if proxy_enabled else 'Disabled'}"
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            _reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                     "ProxyEnable", val, "REG_DWORD")
            success(label)
        results.append(label)

    proxy_server = data.get("proxy_server")
    if proxy_server:
        label = f"Proxy Server -> {proxy_server}"
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            _reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                     "ProxyServer", proxy_server, "REG_SZ")
            success(label)
        results.append(label)

    # DNS - note: changing DNS typically requires admin rights
    dns = data.get("dns_servers", [])
    if dns:
        label = f"DNS Servers -> {', '.join(dns)}"
        if dry_run:
            info(label, "[DRY RUN]")
        else:
            warn(f"DNS settings ({', '.join(dns)}) require admin privileges to change")
            warn("Run: netsh interface ip set dns \"Ethernet\" static <dns> to apply manually")
        results.append(label)

    # Wi-Fi profiles note
    wifi = data.get("wifi_profiles", [])
    if wifi:
        warn(f"{len(wifi)} Wi-Fi profiles captured (import via netsh wlan add profile)")

    return results


def deploy_privacy_security(data, dry_run=False):
    """Deploy privacy permissions via registry."""
    results = []
    consent_base = r"HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"

    permissions = data.get("permissions", {})
    reg_name_map = {
        "location": "location",
        "camera": "webcam",
        "microphone": "microphone",
        "notifications": "userNotificationListener",
        "contacts": "contacts",
        "calendar": "appointments",
        "call_history": "phoneCallHistory",
        "email": "email",
        "documents": "documentsLibrary",
        "pictures": "picturesLibrary",
        "videos": "videosLibrary",
        "file_system": "broadFileSystemAccess",
    }

    for friendly, value in permissions.items():
        if value and value != "not configured":
            reg_name = reg_name_map.get(friendly)
            if reg_name:
                label = f"{friendly} -> {value}"
                if dry_run:
                    info(label, "[DRY RUN]")
                else:
                    ok = _reg_add(f"{consent_base}\\{reg_name}", "Value", value, "REG_SZ")
                    if ok:
                        success(label)
                    else:
                        fail(label)
                results.append(label)

    # Firewall note
    fw = data.get("firewall", {})
    if fw:
        warn("Firewall settings require admin privileges to change")
        for profile, val in fw.items():
            if val:
                info(f"  Firewall {profile}: {val}")

    return results


DEPLOY_MODULES = [
    ("desktop_appearance",  "Desktop & Appearance",   deploy_desktop_appearance),
    ("file_explorer",       "File Explorer",          deploy_file_explorer),
    ("mouse_keyboard",      "Mouse & Keyboard",       deploy_mouse_keyboard),
    ("power_sleep",         "Power & Sleep",           deploy_power_sleep),
    ("network",             "Network",                deploy_network),
    ("privacy_security",    "Privacy & Security",     deploy_privacy_security),
]


# ═══════════════════════════════════════════════
#  HTML REPORT GENERATOR
# ═══════════════════════════════════════════════

def generate_html_report(profile, filepath):
    """Generate an interactive HTML viewer for the captured profile."""
    meta = profile.get("machine_identity", {})
    hostname = meta.get("hostname", "Unknown PC")
    captured = meta.get("captured_at", "")
    win_edition = meta.get("windows_edition", "")
    arch = meta.get("architecture", "")
    serial = meta.get("serial_number", "N/A")

    section_map = {
        "machine_identity":    ("\U0001f4bb", "Machine Identity"),
        "desktop_appearance":  ("\u2699\ufe0f", "Desktop & Appearance"),
        "taskbar_start":       ("\U0001f4cc", "Taskbar & Start Menu"),
        "file_explorer":       ("\U0001f4c2", "File Explorer"),
        "mouse_keyboard":      ("\u2328\ufe0f", "Mouse & Keyboard"),
        "sound_notifications": ("\U0001f50a", "Sound & Notifications"),
        "power_sleep":         ("\u26a1", "Power & Sleep"),
        "network":             ("\U0001f310", "Network"),
        "privacy_security":    ("\U0001f512", "Privacy & Security"),
        "installed_apps":      ("\U0001f4e6", "Installed Apps"),
    }

    section_order = [
        "machine_identity", "desktop_appearance", "taskbar_start",
        "file_explorer", "mouse_keyboard", "sound_notifications",
        "power_sleep", "network", "privacy_security", "installed_apps",
    ]

    section_cards = ""
    for key in section_order:
        data = profile.get(key)
        if not data:
            continue
        icon, title = section_map.get(key, ("\U0001f4c4", key.replace("_", " ").title()))
        section_cards += _build_section_card(key, icon, title, data)

    # Stats
    n_store = len(profile.get("installed_apps", {}).get("store_apps", []))
    n_trad = len(profile.get("installed_apps", {}).get("traditional_apps", []))
    n_wifi = len(profile.get("network", {}).get("wifi_profiles", []))
    dark_apps = profile.get("desktop_appearance", {}).get("dark_mode_apps", False)
    plan = profile.get("power_sleep", {}).get("active_plan", "N/A")

    profile_json_escaped = json.dumps(profile, indent=2, default=str).replace("</", "<\\/").replace("'", "\\'")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>\U0001f9ec WinDNA \u2014 {hostname}</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --dim: #8b949e;
    --cyan: #58a6ff;
    --green: #3fb950;
    --yellow: #d29922;
    --red: #f85149;
    --purple: #bc8cff;
    --font: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 0;
  }}
  .header {{
    background: linear-gradient(135deg, #161b22 0%, #1a2332 100%);
    border-bottom: 1px solid var(--border);
    padding: 2rem 2rem 1.5rem;
    text-align: center;
  }}
  .header h1 {{
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }}
  .header h1 span {{ color: var(--cyan); }}
  .header .subtitle {{
    color: var(--dim);
    font-size: 0.95rem;
  }}
  .header .meta-row {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1rem;
    flex-wrap: wrap;
  }}
  .header .meta-item {{
    font-size: 0.85rem;
    color: var(--dim);
  }}
  .header .meta-item strong {{
    color: var(--text);
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    padding: 1rem 2rem;
    background: var(--card);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }}
  .stat {{
    text-align: center;
    min-width: 80px;
  }}
  .stat .num {{
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--cyan);
  }}
  .stat .label {{
    font-size: 0.75rem;
    color: var(--dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .search-bar {{
    padding: 1rem 2rem;
    background: var(--bg);
    position: sticky;
    top: 0;
    z-index: 10;
    border-bottom: 1px solid var(--border);
  }}
  .search-bar input {{
    width: 100%;
    max-width: 500px;
    display: block;
    margin: 0 auto;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    font-size: 0.95rem;
    font-family: var(--font);
    outline: none;
  }}
  .search-bar input:focus {{
    border-color: var(--cyan);
    box-shadow: 0 0 0 2px rgba(88,166,255,0.2);
  }}
  .container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 1.5rem;
  }}
  .section {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 1rem;
    overflow: hidden;
    transition: border-color 0.2s;
  }}
  .section:hover {{
    border-color: var(--cyan);
  }}
  .section-header {{
    display: flex;
    align-items: center;
    padding: 0.9rem 1.2rem;
    cursor: pointer;
    user-select: none;
    gap: 0.75rem;
    background: transparent;
    transition: background 0.15s;
  }}
  .section-header:hover {{
    background: rgba(88,166,255,0.05);
  }}
  .section-icon {{
    font-size: 1.3rem;
    width: 2rem;
    text-align: center;
    flex-shrink: 0;
  }}
  .section-title {{
    font-weight: 600;
    font-size: 1rem;
    flex: 1;
  }}
  .section-badge {{
    font-size: 0.75rem;
    padding: 0.15rem 0.6rem;
    border-radius: 10px;
    background: rgba(88,166,255,0.15);
    color: var(--cyan);
    font-weight: 500;
  }}
  .section-arrow {{
    color: var(--dim);
    transition: transform 0.2s;
    font-size: 0.8rem;
  }}
  .section.open .section-arrow {{
    transform: rotate(90deg);
  }}
  .section-body {{
    display: none;
    padding: 0 1.2rem 1.2rem;
    border-top: 1px solid var(--border);
  }}
  .section.open .section-body {{
    display: block;
    padding-top: 1rem;
  }}
  .data-table {{
    width: 100%;
    border-collapse: collapse;
  }}
  .data-table tr {{
    border-bottom: 1px solid rgba(48,54,61,0.5);
  }}
  .data-table tr:last-child {{
    border-bottom: none;
  }}
  .data-table td {{
    padding: 0.45rem 0;
    vertical-align: top;
  }}
  .data-table td:first-child {{
    color: var(--dim);
    font-size: 0.85rem;
    width: 40%;
    padding-right: 1rem;
  }}
  .data-table td:last-child {{
    font-family: var(--mono);
    font-size: 0.85rem;
    word-break: break-word;
  }}
  .val-true {{ color: var(--green); }}
  .val-false {{ color: var(--red); }}
  .val-empty {{ color: var(--dim); font-style: italic; }}
  .val-string {{ color: var(--text); }}
  .val-number {{ color: var(--purple); }}
  .item-list {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.3rem;
  }}
  .item-tag {{
    font-size: 0.8rem;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    background: rgba(88,166,255,0.1);
    color: var(--cyan);
    font-family: var(--mono);
    border: 1px solid rgba(88,166,255,0.15);
  }}
  .item-tag.app {{ background: rgba(63,185,80,0.1); color: var(--green); border-color: rgba(63,185,80,0.15); }}
  .item-tag.store {{ background: rgba(188,140,255,0.1); color: var(--purple); border-color: rgba(188,140,255,0.15); }}
  .item-tag.wifi {{ background: rgba(210,153,34,0.1); color: var(--yellow); border-color: rgba(210,153,34,0.15); }}
  .subsection {{
    margin-top: 1rem;
  }}
  .subsection-title {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--dim);
    margin-bottom: 0.5rem;
    font-weight: 600;
  }}
  .code-block {{
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.8rem;
    font-family: var(--mono);
    font-size: 0.8rem;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow-y: auto;
    color: var(--text);
    margin-top: 0.3rem;
  }}
  .footer {{
    text-align: center;
    padding: 2rem;
    color: var(--dim);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: 2rem;
  }}
  .raw-toggle {{
    text-align: center;
    margin: 1.5rem 0;
  }}
  .raw-toggle button {{
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--dim);
    padding: 0.5rem 1.5rem;
    border-radius: 8px;
    font-size: 0.85rem;
    cursor: pointer;
    font-family: var(--font);
    transition: all 0.2s;
  }}
  .raw-toggle button:hover {{
    border-color: var(--cyan);
    color: var(--cyan);
  }}
  .raw-json {{
    display: none;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem;
    margin-top: 1rem;
    max-height: 600px;
    overflow: auto;
  }}
  .raw-json pre {{
    font-family: var(--mono);
    font-size: 0.8rem;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-all;
  }}
  .hidden {{ display: none !important; }}
</style>
</head>
<body>

<div class="header">
  <h1>\U0001f9ec <span>WinDNA</span> Profile</h1>
  <div class="subtitle">{hostname} \u2014 captured {captured[:10] if captured else 'N/A'}</div>
  <div class="meta-row">
    <div class="meta-item">Windows <strong>{win_edition}</strong></div>
    <div class="meta-item">Arch <strong>{arch}</strong></div>
    <div class="meta-item">Dark Mode <strong>{'Yes' if dark_apps else 'No'}</strong></div>
    <div class="meta-item">Serial <strong>{serial}</strong></div>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="num">{n_trad}</div><div class="label">Programs</div></div>
  <div class="stat"><div class="num">{n_store}</div><div class="label">Store Apps</div></div>
  <div class="stat"><div class="num">{n_wifi}</div><div class="label">Wi-Fi</div></div>
  <div class="stat"><div class="num">{plan}</div><div class="label">Power Plan</div></div>
</div>

<div class="search-bar">
  <input type="text" id="search" placeholder="Search settings, apps, values..." autocomplete="off">
</div>

<div class="container">
{section_cards}

  <div class="raw-toggle">
    <button onclick="toggleRaw()">Show Raw JSON</button>
  </div>
  <div class="raw-json" id="rawJson">
    <pre>{json.dumps(profile, indent=2, default=str).replace('<', '&lt;').replace('>', '&gt;')}</pre>
  </div>
</div>

<div class="footer">
  \U0001f9ec WinDNA v1.0 \u2014 Author: cyberspartan77 \u2014 Generated {captured[:10] if captured else 'N/A'}
</div>

<script>
document.querySelectorAll('.section-header').forEach(h => {{
  h.addEventListener('click', () => {{
    h.parentElement.classList.toggle('open');
  }});
}});

document.getElementById('search').addEventListener('input', function() {{
  const q = this.value.toLowerCase();
  document.querySelectorAll('.section').forEach(s => {{
    if (!q) {{
      s.classList.remove('hidden');
      return;
    }}
    const text = s.textContent.toLowerCase();
    if (text.includes(q)) {{
      s.classList.remove('hidden');
      s.classList.add('open');
    }} else {{
      s.classList.add('hidden');
    }}
  }});
}});

function toggleRaw() {{
  const el = document.getElementById('rawJson');
  el.style.display = el.style.display === 'block' ? 'none' : 'block';
}}

document.querySelectorAll('.section').forEach(s => s.classList.add('open'));
</script>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def _format_value(val):
    """Format a value for HTML display."""
    if val is True:
        return '<span class="val-true">true \u2713</span>'
    elif val is False:
        return '<span class="val-false">false \u2717</span>'
    elif val is None or val == "":
        return '<span class="val-empty">(default)</span>'
    elif isinstance(val, (int, float)):
        return f'<span class="val-number">{val}</span>'
    else:
        s = str(val).replace('<', '&lt;').replace('>', '&gt;')
        return f'<span class="val-string">{s}</span>'


def _build_section_card(key, icon, title, data):
    """Build an HTML card for a profile section."""
    badge = ""
    if isinstance(data, dict):
        badge = f'{len(data)} items'
    elif isinstance(data, list):
        badge = f'{len(data)} items'

    body_html = _render_data(key, data)

    return f"""
  <div class="section" data-key="{key}">
    <div class="section-header">
      <div class="section-icon">{icon}</div>
      <div class="section-title">{title}</div>
      <div class="section-badge">{badge}</div>
      <div class="section-arrow">\u25b6</div>
    </div>
    <div class="section-body">{body_html}</div>
  </div>
"""


def _render_data(key, data, depth=0):
    """Recursively render data into HTML tables, lists, and code blocks."""
    if isinstance(data, dict):
        rows = ""
        for k, v in data.items():
            # Special handling for installed_apps
            if key == "installed_apps" and k == "traditional_apps" and isinstance(v, list):
                tags = "".join(
                    f'<span class="item-tag app">{item.get("name", "")} ({item.get("version", "")})</span>'
                    for item in v[:80]
                )
                extra = f" (+{len(v)-80} more)" if len(v) > 80 else ""
                rows += f'<div class="subsection"><div class="subsection-title">Traditional Programs ({len(v)}){extra}</div><div class="item-list">{tags}</div></div>'
            elif key == "installed_apps" and k == "store_apps" and isinstance(v, list):
                tags = "".join(
                    f'<span class="item-tag store">{item.get("name", "")}</span>'
                    for item in v[:60]
                )
                extra = f" (+{len(v)-60} more)" if len(v) > 60 else ""
                rows += f'<div class="subsection"><div class="subsection-title">Store Apps ({len(v)}){extra}</div><div class="item-list">{tags}</div></div>'
            elif key == "installed_apps" and k == "winget_list" and isinstance(v, list):
                if v:
                    content = "\\n".join(str(x) for x in v[:50])
                    safe = content.replace('<', '&lt;').replace('>', '&gt;')
                    rows += f'<div class="subsection"><div class="subsection-title">Winget List (first {min(len(v), 50)})</div><div class="code-block">{safe}</div></div>'
            elif key == "network" and k == "wifi_profiles" and isinstance(v, list):
                tags = "".join(f'<span class="item-tag wifi">{item}</span>' for item in v)
                rows += f'<div class="subsection"><div class="subsection-title">Wi-Fi Profiles ({len(v)})</div><div class="item-list">{tags}</div></div>'
            elif key == "network" and k == "dns_servers" and isinstance(v, list):
                tags = "".join(f'<span class="item-tag">{item}</span>' for item in v)
                rows += f'<div class="subsection"><div class="subsection-title">DNS Servers</div><div class="item-list">{tags}</div></div>'
            elif key == "network" and k == "ip_addresses" and isinstance(v, list):
                tags = "".join(f'<span class="item-tag">{item}</span>' for item in v)
                rows += f'<div class="subsection"><div class="subsection-title">IP Addresses</div><div class="item-list">{tags}</div></div>'
            elif key == "power_sleep" and k == "all_plans" and isinstance(v, list):
                tags = "".join(
                    f'<span class="item-tag {"app" if item.get("active") else ""}">'
                    f'{item.get("name", "")} {"*" if item.get("active") else ""}</span>'
                    for item in v
                )
                rows += f'<div class="subsection"><div class="subsection-title">Power Plans</div><div class="item-list">{tags}</div></div>'
            elif isinstance(v, dict):
                sub_rows = ""
                for sk, sv in v.items():
                    if isinstance(sv, dict):
                        # Nested dict inside nested dict
                        inner = ""
                        for ik, iv in sv.items():
                            inner += f'<tr><td>{ik}</td><td>{_format_value(iv)}</td></tr>'
                        friendly_inner = sk.replace("_", " ").title()
                        sub_rows += f'<tr><td colspan="2"><div class="subsection"><div class="subsection-title">{friendly_inner}</div><table class="data-table">{inner}</table></div></td></tr>'
                    else:
                        sub_rows += f'<tr><td>{sk}</td><td>{_format_value(sv)}</td></tr>'
                friendly = k.replace("_", " ").title()
                rows += f'<div class="subsection"><div class="subsection-title">{friendly}</div><table class="data-table">{sub_rows}</table></div>'
            elif isinstance(v, list):
                if v:
                    tags = "".join(f'<span class="item-tag">{item}</span>' for item in v)
                    friendly = k.replace("_", " ").title()
                    rows += f'<div class="subsection"><div class="subsection-title">{friendly} ({len(v)})</div><div class="item-list">{tags}</div></div>'
            else:
                rows += f'<table class="data-table"><tr><td>{k}</td><td>{_format_value(v)}</td></tr></table>'
        return rows
    elif isinstance(data, list):
        tags = "".join(f'<span class="item-tag">{item}</span>' for item in data)
        return f'<div class="item-list">{tags}</div>'
    else:
        return f'<p>{_format_value(data)}</p>'


# ═══════════════════════════════════════════════
#  MENU FLOWS
# ═══════════════════════════════════════════════

def profile_display_name(filepath):
    """Get a friendly display name from a profile path."""
    parent = os.path.basename(os.path.dirname(filepath))
    filename = os.path.basename(filepath)
    if filename == "profile.json":
        return parent
    return filename


def get_saved_profiles():
    """Find all profile.json files in profile subdirectories, plus legacy top-level .json files."""
    settings = load_settings()
    pdir = get_profiles_dir(settings)
    os.makedirs(pdir, exist_ok=True)
    folder_profiles = sorted(globmod.glob(os.path.join(pdir, "*", "profile.json")), key=os.path.getmtime, reverse=True)
    flat_profiles = sorted(globmod.glob(os.path.join(pdir, "*.json")), key=os.path.getmtime, reverse=True)
    return folder_profiles + flat_profiles


def flow_capture():
    """Full capture flow with category selection."""
    settings = load_settings()

    clear_screen()
    banner()
    divider("CAPTURE \u2014 Select Categories")

    default_cats = settings.get("default_capture_categories", "all")
    if default_cats == "all":
        preselect = True
    else:
        preselect = False

    checklist_items = [(key, label) for key, label, _ in CAPTURE_MODULES]

    if default_cats != "all" and not preselect:
        selected_keys = show_checklist("Select categories to capture", checklist_items, preselect_all=False)
    else:
        selected_keys = show_checklist("Select categories to capture", checklist_items, preselect_all=True)

    if not selected_keys:
        warn("Nothing selected")
        pause()
        return

    # Run capture
    clear_screen()
    banner()
    divider("CAPTURING")
    print()

    profile = {}
    for key, label, func in CAPTURE_MODULES:
        if key not in selected_keys:
            continue
        spinner_line(label)
        try:
            profile[key] = func()
            spinner_done(label)
        except Exception as e:
            profile[key] = {"error": str(e)}
            spinner_fail(label, str(e))

    # Save -- create a folder per capture with JSON + HTML
    pdir = get_profiles_dir(settings)
    hostname_clean = profile.get("machine_identity", {}).get("hostname", "PC").replace(" ", "_").replace("'", "")
    date_str = datetime.date.today().isoformat()
    folder_name = f"{hostname_clean}_{date_str}"

    if not settings.get("auto_name_profiles", False):
        print()
        folder_name = prompt("Profile folder name", folder_name)

    folder_path = os.path.join(pdir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # Write JSON
    json_path = os.path.join(folder_path, "profile.json")
    indent = None if settings.get("compact_json", False) else 2
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=indent, default=str)

    # Write HTML viewer
    spinner_line("Generating HTML report")
    html_path = os.path.join(folder_path, "profile.html")
    generate_html_report(profile, html_path)
    spinner_done("HTML report generated")

    print()
    divider("CAPTURE COMPLETE")
    success(f"Folder: {folder_path}")
    info(f"JSON:   {os.path.getsize(json_path) / 1024:.1f} KB")
    info(f"HTML:   {os.path.getsize(html_path) / 1024:.1f} KB")

    # Quick stats
    trad = profile.get("installed_apps", {}).get("traditional_apps", [])
    store = profile.get("installed_apps", {}).get("store_apps", [])
    wifi = profile.get("network", {}).get("wifi_profiles", [])
    if trad:
        info(f"Traditional programs: {len(trad)}")
    if store:
        info(f"Store apps: {len(store)}")
    if wifi:
        info(f"Wi-Fi profiles: {len(wifi)}")

    # Auto security audit if enabled
    if settings.get("security_audit_with_capture", False) and securityaudit_win:
        print()
        divider("AUTO SECURITY AUDIT")
        alert_level = settings.get("threat_alert_level", "medium")
        audit_data = securityaudit_win.run_full_audit(alert_level=alert_level)
        audit_json = os.path.join(folder_path, "audit.json")
        audit_html = os.path.join(folder_path, "audit.html")
        with open(audit_json, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, indent=indent, default=str)
        securityaudit_win.generate_audit_html(audit_data, audit_html)
        success("Security audit saved alongside profile")
        info(f"Audit JSON: {os.path.getsize(audit_json) / 1024:.1f} KB")
        info(f"Audit HTML: {os.path.getsize(audit_html) / 1024:.1f} KB")

    # Offer to open HTML
    open_it = prompt("Open HTML report in browser? (y/N)")
    if open_it.lower() == "y":
        if os.name == "nt":
            os.startfile(html_path)
        else:
            _run(f'start "" "{html_path}"')

    pause()


def flow_deploy():
    """Deploy flow: pick a profile, pick categories, apply."""
    settings = load_settings()
    profiles = get_saved_profiles()

    if not profiles:
        clear_screen()
        banner()
        warn("No saved profiles found.")
        pdir = get_profiles_dir(settings)
        info(f"Capture a profile first, or place .json files in:\n       {pdir}")
        pause()
        return

    # Pick a profile
    options = []
    for p in profiles:
        name = profile_display_name(p)
        size = os.path.getsize(p) / 1024
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
        options.append((name, f"{size:.1f} KB \u2014 {mtime}"))

    choice = show_menu("DEPLOY \u2014 Select a Profile", options)
    if choice <= 0 or choice > len(profiles):
        return

    profile_path = profiles[choice - 1]

    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)

    hostname = profile.get("machine_identity", {}).get("hostname", "Unknown")
    captured = profile.get("machine_identity", {}).get("captured_at", "?")

    # Show profile summary
    clear_screen()
    banner()
    divider(f"Profile: {hostname}")
    info(f"Captured: {captured}")
    info(f"Windows: {profile.get('machine_identity', {}).get('windows_edition', '?')}")
    info(f"Architecture: {profile.get('machine_identity', {}).get('architecture', '?')}")
    print()

    # Build checklist of available deploy categories
    available = []
    for key, label, func in DEPLOY_MODULES:
        if key in profile and profile[key]:
            count = ""
            if key == "installed_apps":
                n = len(profile[key].get("traditional_apps", []))
                count = f" ({n} programs)"
            available.append((key, f"{label}{count}"))

    if not available:
        warn("This profile has no deployable data")
        pause()
        return

    selected_keys = show_checklist("Select categories to deploy", available, preselect_all=True)
    if not selected_keys:
        warn("Nothing selected")
        pause()
        return

    # Dry run or live?
    if settings.get("dry_run_by_default", False):
        clear_screen()
        banner()
        divider("Deploy Mode")
        print()
        warn("Dry-Run is ON by default (change in Settings)")
        print()
        print(f"    {BOLD}{CYAN}1{RESET}  Dry Run   {DIM}(preview changes, touch nothing){RESET}")
        print(f"    {BOLD}{CYAN}2{RESET}  Apply     {DIM}(override \u2014 make changes to this PC){RESET}")
        print(f"    {BOLD}{CYAN}0{RESET}  {DIM}Cancel{RESET}")
        mode = prompt("Choose mode", "1")
    else:
        clear_screen()
        banner()
        divider("Deploy Mode")
        print()
        print(f"    {BOLD}{CYAN}1{RESET}  Dry Run   {DIM}(preview changes, touch nothing){RESET}")
        print(f"    {BOLD}{CYAN}2{RESET}  Apply     {DIM}(make changes to this PC){RESET}")
        print(f"    {BOLD}{CYAN}0{RESET}  {DIM}Cancel{RESET}")
        mode = prompt("Choose mode")

    if mode == "0" or mode == "":
        return

    dry_run = mode != "2"

    if not dry_run and settings.get("confirm_before_apply", True):
        clear_screen()
        banner()
        divider("CONFIRM DEPLOYMENT")
        print()
        warn("This will modify settings on THIS PC.")
        info(f"Source profile: {hostname}")
        info(f"Categories: {len(selected_keys)}")
        if settings.get("auto_backup_before_deploy", True):
            info(f"Auto-backup: {GREEN}ON{RESET} \u2014 current values will be backed up first")
        print()
        confirm = prompt("Type YES to proceed")
        if confirm != "YES":
            info("Cancelled.")
            pause()
            return
    elif not dry_run and not settings.get("confirm_before_apply", True):
        info("Confirm is OFF \u2014 applying immediately...")

    # Auto-backup current values before deploy
    if not dry_run and settings.get("auto_backup_before_deploy", True):
        backup_dir = get_backup_dir(settings)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, ts)
        os.makedirs(backup_path, exist_ok=True)

        # Quick capture of current state for categories being deployed
        backup_profile = {}
        for key, label, _ in CAPTURE_MODULES:
            if key in selected_keys:
                # Find the matching capture function
                for ckey, _, cfunc in CAPTURE_MODULES:
                    if ckey == key:
                        try:
                            backup_profile[key] = cfunc()
                        except Exception:
                            backup_profile[key] = {"error": "backup capture failed"}
                        break

        backup_json = os.path.join(backup_path, "pre_deploy_backup.json")
        with open(backup_json, "w", encoding="utf-8") as f:
            json.dump(backup_profile, f, indent=2, default=str)
        info(f"Pre-deploy backup saved: {backup_path}")

    # Execute deployment
    clear_screen()
    banner()
    mode_label = "DRY RUN" if dry_run else "APPLYING"
    divider(f"DEPLOYING \u2014 {mode_label}")

    all_results = {"applied": [], "skipped": [], "errors": []}

    for key, label, func in DEPLOY_MODULES:
        if key not in selected_keys:
            continue
        data = profile.get(key, {})
        if not data:
            all_results["skipped"].append(label)
            continue
        print()
        divider(label)
        try:
            results = func(data, dry_run=dry_run)
            all_results["applied"].append(label)
        except Exception as e:
            fail(f"{label}: {e}")
            all_results["errors"].append(f"{label}: {e}")

    # Report
    print()
    dbl_line = "\u2550" * 48
    print(f"\n  {BOLD}{CYAN}{dbl_line}{RESET}")
    print(f"  {BOLD}  DEPLOYMENT REPORT{RESET}")
    print(f"  {BOLD}{CYAN}{dbl_line}{RESET}")
    print()
    if all_results["applied"]:
        for a in all_results["applied"]:
            success(a)
    if all_results["skipped"]:
        for s in all_results["skipped"]:
            warn(f"{s} (skipped \u2014 no data)")
    if all_results["errors"]:
        for e in all_results["errors"]:
            fail(e)

    if not dry_run:
        print()
        warn("Some changes may require a logoff/restart to take effect.")

    pause()


def flow_view_profile():
    """Browse and inspect a saved profile."""
    profiles = get_saved_profiles()
    if not profiles:
        clear_screen()
        banner()
        warn("No saved profiles.")
        pause()
        return

    options = []
    for p in profiles:
        name = profile_display_name(p)
        size = os.path.getsize(p) / 1024
        options.append((name, f"{size:.1f} KB"))

    choice = show_menu("VIEW \u2014 Select a Profile", options)
    if choice <= 0 or choice > len(profiles):
        return

    with open(profiles[choice - 1], encoding="utf-8") as f:
        profile = json.load(f)

    # Show sections menu
    while True:
        sections = [(k, f"{len(str(v))} chars") for k, v in profile.items()]
        sec_choice = show_menu(f"Profile Sections \u2014 {profile_display_name(profiles[choice-1])}", sections)
        if sec_choice <= 0 or sec_choice > len(sections):
            break

        key = sections[sec_choice - 1][0]
        data = profile[key]

        clear_screen()
        banner()
        divider(f"Section: {key}")
        print()
        print(json.dumps(data, indent=2, default=str))
        pause()


def flow_diff():
    """Compare two profiles side by side."""
    profiles = get_saved_profiles()
    if len(profiles) < 2:
        clear_screen()
        banner()
        warn("Need at least 2 saved profiles to compare.")
        pause()
        return

    options = [(profile_display_name(p), "") for p in profiles]

    clear_screen()
    banner()
    divider("DIFF \u2014 Select FIRST profile")
    for i, (label, _) in enumerate(options, 1):
        print(f"    {BOLD}{CYAN}{i}{RESET}  {label}")
    c1 = prompt("First profile #")
    try:
        idx1 = int(c1) - 1
    except (ValueError, TypeError):
        return

    clear_screen()
    banner()
    divider("DIFF \u2014 Select SECOND profile")
    for i, (label, _) in enumerate(options, 1):
        marker = f" {YELLOW}<- first{RESET}" if i - 1 == idx1 else ""
        print(f"    {BOLD}{CYAN}{i}{RESET}  {label}{marker}")
    c2 = prompt("Second profile #")
    try:
        idx2 = int(c2) - 1
    except (ValueError, TypeError):
        return

    if idx1 == idx2:
        warn("Same profile selected twice")
        pause()
        return

    with open(profiles[idx1], encoding="utf-8") as f:
        p1 = json.load(f)
    with open(profiles[idx2], encoding="utf-8") as f:
        p2 = json.load(f)

    clear_screen()
    banner()
    name1 = profile_display_name(profiles[idx1])
    name2 = profile_display_name(profiles[idx2])
    divider(f"DIFF: {name1} vs {name2}")
    print()

    all_keys = sorted(set(list(p1.keys()) + list(p2.keys())))
    diffs_found = 0

    for section in all_keys:
        d1 = p1.get(section)
        d2 = p2.get(section)
        if d1 == d2:
            success(f"{section}: identical")
            continue

        if d1 is None:
            warn(f"{section}: only in {name2}")
            diffs_found += 1
            continue
        if d2 is None:
            warn(f"{section}: only in {name1}")
            diffs_found += 1
            continue

        if isinstance(d1, dict) and isinstance(d2, dict):
            changed = []
            for k in sorted(set(list(d1.keys()) + list(d2.keys()))):
                v1, v2 = d1.get(k), d2.get(k)
                if v1 != v2:
                    changed.append(k)
            if changed:
                fail(f"{section}: {len(changed)} differences")
                for k in changed[:5]:
                    print(f"       {DIM}{k}: {str(d1.get(k))[:40]} -> {str(d2.get(k))[:40]}{RESET}")
                if len(changed) > 5:
                    print(f"       {DIM}...and {len(changed) - 5} more{RESET}")
                diffs_found += len(changed)
        else:
            fail(f"{section}: different")
            diffs_found += 1

    print()
    if diffs_found == 0:
        success("Profiles are identical!")
    else:
        info(f"Total differences: {diffs_found}")

    pause()


def flow_delete_profile():
    """Delete a saved profile."""
    profiles = get_saved_profiles()
    if not profiles:
        clear_screen()
        banner()
        warn("No saved profiles.")
        pause()
        return

    options = [(profile_display_name(p), f"{os.path.getsize(p)/1024:.1f} KB") for p in profiles]
    choice = show_menu("DELETE \u2014 Select a Profile", options)
    if choice <= 0 or choice > len(profiles):
        return

    target = profiles[choice - 1]
    name = profile_display_name(target)
    confirm = prompt(f"Delete {name}? Type DELETE to confirm")
    if confirm == "DELETE":
        parent_dir = os.path.dirname(target)
        if os.path.basename(target) == "profile.json" and parent_dir != get_profiles_dir(load_settings()):
            shutil.rmtree(parent_dir)
            success(f"Deleted folder: {name}")
        else:
            os.remove(target)
            success(f"Deleted {name}")
    else:
        info("Cancelled")
    pause()


# ═══════════════════════════════════════════════
#  SETTINGS MENU
# ═══════════════════════════════════════════════

SETTINGS_DEFS = [
    ("profile_save_location",       "Profile Save Location",        "Where captured profiles are saved (blank = ./profiles/)",   "path"),
    ("backup_directory",            "Backup Directory",             "Where pre-deploy backups go (blank = ~/.windna_backup/)",   "path"),
    ("auto_backup_before_deploy",   "Auto-Backup Before Deploy",    "Backup current values before overwriting",                 "bool"),
    ("dry_run_by_default",          "Dry-Run by Default",           "Always preview before applying changes",                   "bool"),
    ("confirm_before_apply",        "Confirm Before Apply",         "Require typing YES before deploy",                         "bool"),
    ("auto_name_profiles",          "Auto-Name Profiles",           "Skip 'save as' prompt, auto-generate filename",            "bool"),
    ("compact_json",                "Compact JSON",                 "Save profiles as compact (smaller) vs pretty-printed",     "bool"),
    ("color_output",                "Color Output",                 "Enable/disable terminal colors",                           "bool"),
    ("default_capture_categories",  "Default Capture Categories",   "Pre-selected categories (all or comma-separated keys)",    "text"),
    ("security_audit_with_capture", "Security Audit with Capture",  "Auto-run security audit when capturing a profile",         "bool"),
    ("threat_alert_level",          "Threat Alert Level",           "Sensitivity for threat detection (low/medium/high)",        "choice"),
]


def flow_settings():
    """Settings menu \u2014 view and toggle all app settings."""
    settings = load_settings()

    while True:
        clear_screen()
        banner()
        divider("SETTINGS")
        print()

        for i, (key, label, desc, stype) in enumerate(SETTINGS_DEFS, 1):
            val = settings.get(key, DEFAULT_SETTINGS.get(key))

            if stype == "bool":
                if val:
                    display = f"{GREEN}ON{RESET}"
                else:
                    display = f"{RED}OFF{RESET}"
            elif stype == "path":
                if val:
                    display = f"{CYAN}{val}{RESET}"
                else:
                    default_hint = "./profiles/" if "profile" in key else "~/.windna_backup/"
                    display = f"{DIM}{default_hint} (default){RESET}"
            elif stype == "choice":
                color = {
                    "low": GREEN, "medium": YELLOW, "high": RED
                }.get(val, CYAN)
                display = f"{color}{val}{RESET}"
            else:
                display = f"{CYAN}{val}{RESET}"

            print(f"    {BOLD}{CYAN}{i:>2}{RESET}  {label}")
            print(f"        {DIM}{desc}{RESET}")
            print(f"        Current: {display}")
            print()

        print(f"    {BOLD}{CYAN} R{RESET}  {YELLOW}Reset All to Defaults{RESET}")
        print(f"    {BOLD}{CYAN} 0{RESET}  {DIM}Back to Main Menu{RESET}")
        print()

        choice = prompt("Setting # to change / R=reset / 0=back")

        if choice == "0" or choice == "":
            break
        elif choice.upper() == "R":
            confirm = prompt("Reset ALL settings to defaults? (y/N)")
            if confirm.lower() == "y":
                settings = dict(DEFAULT_SETTINGS)
                save_settings(settings)
                success("All settings reset to defaults")
                pause()
            continue

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(SETTINGS_DEFS):
                continue
        except ValueError:
            continue

        key, label, desc, stype = SETTINGS_DEFS[idx]

        if stype == "bool":
            current = settings.get(key, DEFAULT_SETTINGS.get(key))
            settings[key] = not current
            save_settings(settings)

        elif stype == "path":
            current = settings.get(key, "")
            print()
            info(f"Current: {current or '(default)'}")
            new_val = prompt("New path (blank = use default)")
            if new_val:
                expanded = os.path.expanduser(new_val)
                if not os.path.isdir(expanded):
                    create = prompt("Directory doesn't exist. Create it? (y/N)")
                    if create.lower() == "y":
                        try:
                            os.makedirs(expanded, exist_ok=True)
                            settings[key] = expanded
                            save_settings(settings)
                            success(f"Created and set: {expanded}")
                        except Exception as e:
                            fail(f"Could not create: {e}")
                        pause()
                    else:
                        settings[key] = expanded
                        save_settings(settings)
                else:
                    settings[key] = expanded
                    save_settings(settings)
            else:
                settings[key] = ""
                save_settings(settings)

        elif stype == "choice":
            current = settings.get(key, "")
            print()
            info(f"Current: {current}")
            print(f"    {BOLD}{CYAN}1{RESET}  low    {DIM}(fewer alerts, only critical){RESET}")
            print(f"    {BOLD}{CYAN}2{RESET}  medium {DIM}(balanced \u2014 recommended){RESET}")
            print(f"    {BOLD}{CYAN}3{RESET}  high   {DIM}(verbose, flags everything){RESET}")
            pick = prompt("Choose 1/2/3", "2")
            choice_map = {"1": "low", "2": "medium", "3": "high"}
            settings[key] = choice_map.get(pick, "medium")
            save_settings(settings)

        elif stype == "text":
            current = settings.get(key, "")
            print()
            info(f"Current: {current}")
            info("Enter 'all' for all categories, or comma-separated keys:")
            info("  Available: machine_identity, desktop_appearance, taskbar_start,")
            info("  file_explorer, mouse_keyboard, sound_notifications, power_sleep,")
            info("  network, privacy_security, installed_apps")
            new_val = prompt("New value", current)
            settings[key] = new_val.strip()
            save_settings(settings)


# ═══════════════════════════════════════════════
#  SECURITY AUDIT FLOW
# ═══════════════════════════════════════════════

def flow_security_audit():
    """Run the Security & Asset Audit engine (placeholder for securityaudit_win module)."""
    if securityaudit_win is None:
        clear_screen()
        banner()
        divider("SECURITY & ASSET AUDIT")
        print()
        warn("The securityaudit_win module is not yet installed.")
        info("This feature will be available when securityaudit_win.py is placed")
        info("in the same directory as windna.py.")
        print()
        info("The module will provide:")
        print(f"       {DIM}- Asset Intelligence (hardware, storage, TPM){RESET}")
        print(f"       {DIM}- User Accounts & Access (local users, admin groups){RESET}")
        print(f"       {DIM}- Network & Connections (open ports, shares){RESET}")
        print(f"       {DIM}- Threat Detection & IOCs (suspicious tasks, services){RESET}")
        print(f"       {DIM}- Compliance Posture (BitLocker, Defender, UAC){RESET}")
        print(f"       {DIM}- Windows Event Log Forensics{RESET}")
        pause()
        return

    settings = load_settings()
    alert_level = settings.get("threat_alert_level", "medium")

    # Check for admin
    is_admin = False
    try:
        is_admin = _run_ps("[bool](([System.Security.Principal.WindowsIdentity]::GetCurrent()).groups -match 'S-1-5-32-544')") == "True"
    except Exception:
        pass

    if not is_admin:
        print(f"\n  {YELLOW}!{RESET} For full results, run as Administrator")
        print(f"  {DIM}Some checks need elevated access.{RESET}\n")

    audit_items = [
        ("asset_intelligence",  "Asset Intelligence (hardware, TPM, storage)"),
        ("user_accounts",       "User Accounts & Access (local users, admin)"),
        ("network",             "Network & Connections (ports, shares, firewall)"),
        ("threat_detection",    "Threat Detection & IOCs (services, tasks, startup)"),
        ("compliance",          "Compliance Posture (BitLocker, Defender, UAC)"),
        ("logs_forensics",      "Event Log Forensics (logins, audit events)"),
    ]

    selected = show_checklist("Security Audit \u2014 Select Sections", audit_items, preselect_all=True)
    if not selected:
        warn("Nothing selected")
        pause()
        return

    clear_screen()
    banner()
    divider(f"SECURITY AUDIT \u2014 Alert Level: {alert_level.upper()}")
    print()

    audit_data = securityaudit_win.run_full_audit(selected_sections=selected, alert_level=alert_level)

    pdir = get_profiles_dir(settings)
    hostname_clean = audit_data.get("audit_meta", {}).get("hostname", "PC").replace(" ", "_").replace("'", "")
    date_str = datetime.date.today().isoformat()
    folder_name = f"{hostname_clean}_{date_str}"

    if not settings.get("auto_name_profiles", False):
        print()
        folder_name = prompt("Audit folder name", folder_name)

    folder_path = os.path.join(pdir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    json_path = os.path.join(folder_path, "audit.json")
    indent = None if settings.get("compact_json", False) else 2
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=indent, default=str)

    spinner_line("Generating Audit HTML report")
    html_path = os.path.join(folder_path, "audit.html")
    securityaudit_win.generate_audit_html(audit_data, html_path)
    spinner_done("Audit HTML report generated")

    print()
    divider("AUDIT COMPLETE")
    success(f"Folder: {folder_path}")
    info(f"JSON:   {os.path.getsize(json_path) / 1024:.1f} KB")
    info(f"HTML:   {os.path.getsize(html_path) / 1024:.1f} KB")

    threats = audit_data.get("threat_detection", {})
    sev = threats.get("severity_counts", {})
    n_crit = sev.get("critical", 0)
    n_warn = sev.get("warning", 0)
    n_info = sev.get("info", 0)
    if n_crit:
        print(f"\n  {RED}{BOLD}  !!! {n_crit} CRITICAL FINDINGS !!!{RESET}")
    if n_warn:
        print(f"  {YELLOW}  {n_warn} warnings{RESET}")
    if n_info:
        print(f"  {CYAN}  {n_info} informational items{RESET}")

    compliance = audit_data.get("compliance", {})
    passed = compliance.get("passed", 0)
    failed_count = compliance.get("failed", 0)
    total = compliance.get("total", 0)
    if total:
        pct = int((passed / total) * 100) if total else 0
        color = GREEN if pct >= 80 else YELLOW if pct >= 60 else RED
        print(f"\n  {color}  Compliance: {passed}/{total} checks passed ({pct}%){RESET}")

    open_it = prompt("Open HTML audit report in browser? (y/N)")
    if open_it.lower() == "y":
        if os.name == "nt":
            os.startfile(html_path)
        else:
            _run(f'start "" "{html_path}"')

    pause()


# ═══════════════════════════════════════════════
#  MAIN MENU LOOP
# ═══════════════════════════════════════════════

def main():
    # Enable ANSI escape sequences on Windows 10+
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    while True:
        n_profiles = len(get_saved_profiles())
        profile_info = f"{n_profiles} saved" if n_profiles else "none yet"

        choice = show_menu("MAIN MENU", [
            ("Capture This PC",       "Scan and save all Windows settings to a profile"),
            ("Deploy to This PC",     "Apply a saved profile to this machine"),
            ("View Profile",          "Browse the contents of a saved profile"),
            ("Compare Profiles",      "Diff two profiles side by side"),
            ("Delete Profile",        f"Remove a saved profile ({profile_info})"),
            (f"{MAGENTA}Security & Asset Audit{RESET}", "Full security audit with threat detection"),
            (f"{YELLOW}Settings{RESET}",  "Configure WinDNA preferences"),
            (f"{RED}Exit WinDNA{RESET}",  "Quit the application"),
        ], show_back=False)

        if choice == 1:
            flow_capture()
        elif choice == 2:
            flow_deploy()
        elif choice == 3:
            flow_view_profile()
        elif choice == 4:
            flow_diff()
        elif choice == 5:
            flow_delete_profile()
        elif choice == 6:
            flow_security_audit()
        elif choice == 7:
            flow_settings()
        elif choice == 8 or choice == 0:
            clear_screen()
            print(f"\n  {CYAN}\U0001f9ec Thanks for using WinDNA. Your PC's DNA is safe.{RESET}\n")
            sys.exit(0)
        elif choice == -1:
            pass


if __name__ == "__main__":
    main()
