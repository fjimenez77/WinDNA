#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║   WinDNA Security Audit Engine v1.0          ║
║   Windows Security & Asset Assessment        ║
╠══════════════════════════════════════════════╣
║   Author: cyberspartan77                     ║
╚══════════════════════════════════════════════╝
"""

import subprocess
import json
import os
import re
import sys
import platform
import datetime
import html as html_mod
from pathlib import Path

# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

def spinner_line(msg):
    sys.stdout.write(f"\r  {YELLOW}~{RESET} {msg}...  ")
    sys.stdout.flush()

def done_line(msg):
    sys.stdout.write(f"\r  {GREEN}+{RESET}  {msg}        \n")
    sys.stdout.flush()

def _run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def _run_ps(cmd, timeout=30):
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""

def _run_lines(cmd, timeout=30):
    out = _run(cmd, timeout)
    return [l for l in out.splitlines() if l.strip()] if out else []

def _run_ps_lines(cmd, timeout=30):
    out = _run_ps(cmd, timeout)
    return [l for l in out.splitlines() if l.strip()] if out else []

def _ps_json(cmd, timeout=30):
    """Run PowerShell command and parse JSON output."""
    out = _run_ps(f"{cmd} | ConvertTo-Json -Depth 5 -Compress", timeout)
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None

def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# ═══════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════

SUSPICIOUS_PORTS = [4444, 5555, 6666, 1337, 31337, 8888, 9999, 12345, 54321, 6667, 6697]

KNOWN_MALWARE_NAMES = [
    "mimikatz", "lazagne", "procdump", "psexec", "cobaltstrike",
    "meterpreter", "empire", "rubeus", "sharphound", "bloodhound",
    "netcat", "ncat", "powercat", "invoke-obfuscation", "certutil",
]

CRYPTO_MINER_NAMES = [
    "xmrig", "minerd", "ethminer", "cgminer", "bfgminer",
    "cpuminer", "nicehash", "phoenixminer", "t-rex", "nbminer",
]


# ═══════════════════════════════════════════════
#  SECTION 1: ASSET INTELLIGENCE
# ═══════════════════════════════════════════════

def audit_asset_intelligence():
    spinner_line("Asset Intelligence — Hardware")
    data = {}

    # CPU
    cpu = _ps_json("Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed")
    if isinstance(cpu, list):
        cpu = cpu[0] if cpu else {}
    data["cpu"] = cpu or {"Name": "Unknown", "NumberOfCores": 0, "NumberOfLogicalProcessors": 0}

    # RAM
    ram_raw = _run_ps("(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum")
    try:
        data["ram_gb"] = round(int(ram_raw) / (1024**3), 1)
    except (ValueError, TypeError):
        data["ram_gb"] = 0

    # GPU
    spinner_line("Asset Intelligence — GPU")
    gpu = _ps_json("Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM")
    if isinstance(gpu, dict):
        gpu = [gpu]
    data["gpu"] = gpu or []

    # Storage
    spinner_line("Asset Intelligence — Storage")
    volumes = _ps_json("Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter, FileSystemType, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,1)}}")
    if isinstance(volumes, dict):
        volumes = [volumes]
    data["storage"] = {"volumes": volumes or []}

    disks = _ps_json("Get-PhysicalDisk | Select-Object FriendlyName, MediaType, @{N='SizeGB';E={[math]::Round($_.Size/1GB,1)}}, HealthStatus")
    if isinstance(disks, dict):
        disks = [disks]
    data["storage"]["physical_disks"] = disks or []

    # Battery
    spinner_line("Asset Intelligence — Battery")
    batt = _ps_json("Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, DesignCapacity, FullChargeCapacity")
    data["battery"] = batt if batt else {"present": False}

    # Display
    spinner_line("Asset Intelligence — Display")
    display = _ps_json("Get-CimInstance Win32_VideoController | Select-Object Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate")
    if isinstance(display, dict):
        display = [display]
    data["displays"] = display or []

    # USB
    spinner_line("Asset Intelligence — Peripherals")
    usb = _ps_json("Get-PnpDevice -Class USB -Status OK -ErrorAction SilentlyContinue | Select-Object FriendlyName, InstanceId")
    if isinstance(usb, dict):
        usb = [usb]
    data["usb_devices"] = usb or []

    # Bluetooth
    bt = _ps_json("Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | Select-Object FriendlyName")
    if isinstance(bt, dict):
        bt = [bt]
    data["bluetooth_devices"] = bt or []

    # Printers
    printers = _ps_json("Get-Printer -ErrorAction SilentlyContinue | Select-Object Name, DriverName, PortName")
    if isinstance(printers, dict):
        printers = [printers]
    data["printers"] = printers or []

    # BIOS / System
    spinner_line("Asset Intelligence — System Identity")
    bios = _ps_json("Get-CimInstance Win32_BIOS | Select-Object SerialNumber, SMBIOSBIOSVersion, Manufacturer")
    data["bios"] = bios or {}

    system = _ps_json("Get-CimInstance Win32_ComputerSystem | Select-Object Model, Manufacturer, TotalPhysicalMemory, Domain, PartOfDomain")
    data["system"] = system or {}

    # Architecture
    data["architecture"] = platform.machine()
    data["os_version"] = platform.platform()

    done_line("Asset Intelligence")
    return data


# ═══════════════════════════════════════════════
#  SECTION 2: USER ACCOUNTS & ACCESS
# ═══════════════════════════════════════════════

def audit_user_accounts():
    spinner_line("User Accounts & Access")
    data = {}

    # Local users
    users = _ps_json("Get-LocalUser | Select-Object Name, Enabled, LastLogon, PasswordRequired, PasswordLastSet, Description")
    if isinstance(users, dict):
        users = [users]
    data["local_users"] = users or []

    # Admins
    spinner_line("User Accounts — Admin Group")
    admins = _ps_json("Get-LocalGroupMember -Group Administrators -ErrorAction SilentlyContinue | Select-Object Name, ObjectClass, PrincipalSource")
    if isinstance(admins, dict):
        admins = [admins]
    data["admin_group"] = admins or []

    # RDP users
    rdp = _ps_json("Get-LocalGroupMember -Group 'Remote Desktop Users' -ErrorAction SilentlyContinue | Select-Object Name, ObjectClass")
    if isinstance(rdp, dict):
        rdp = [rdp]
    data["rdp_users"] = rdp or []

    # Scheduled tasks (persistence check)
    spinner_line("User Accounts — Scheduled Tasks")
    tasks = _ps_json("Get-ScheduledTask | Where-Object {$_.State -eq 'Ready' -and $_.TaskPath -notlike '\\Microsoft\\*'} | Select-Object TaskName, TaskPath, State -First 50")
    if isinstance(tasks, dict):
        tasks = [tasks]
    data["scheduled_tasks_non_microsoft"] = tasks or []

    done_line("User Accounts & Access")
    return data


# ═══════════════════════════════════════════════
#  SECTION 3: CERTIFICATES
# ═══════════════════════════════════════════════

def audit_certificates():
    spinner_line("Certificates — Scanning Stores")
    data = {"machine_certs": [], "user_certs": [], "expired": [], "expiring_30d": [], "expiring_90d": [], "self_signed": [], "root_cert_count": 0}

    now = datetime.datetime.now()
    d30 = now + datetime.timedelta(days=30)
    d90 = now + datetime.timedelta(days=90)

    # Machine certs
    mcerts = _ps_json("Get-ChildItem Cert:\\LocalMachine\\My -ErrorAction SilentlyContinue | Select-Object Subject, Issuer, NotAfter, NotBefore, Thumbprint")
    if isinstance(mcerts, dict):
        mcerts = [mcerts]
    data["machine_certs"] = mcerts or []

    # User certs
    ucerts = _ps_json("Get-ChildItem Cert:\\CurrentUser\\My -ErrorAction SilentlyContinue | Select-Object Subject, Issuer, NotAfter, NotBefore, Thumbprint")
    if isinstance(ucerts, dict):
        ucerts = [ucerts]
    data["user_certs"] = ucerts or []

    # Root cert count
    root_count = _run_ps("(Get-ChildItem Cert:\\LocalMachine\\Root -ErrorAction SilentlyContinue).Count")
    try:
        data["root_cert_count"] = int(root_count)
    except (ValueError, TypeError):
        data["root_cert_count"] = 0

    # Analyze all certs
    all_certs = (data["machine_certs"] or []) + (data["user_certs"] or [])
    for cert in all_certs:
        if not isinstance(cert, dict):
            continue
        not_after = cert.get("NotAfter", "")
        subject = cert.get("Subject", "")
        issuer = cert.get("Issuer", "")

        # Parse date - PowerShell JSON dates can be various formats
        exp_date = None
        if not_after:
            # Try /Date(timestamp)/ format
            m = re.search(r'/Date\((\d+)\)', str(not_after))
            if m:
                exp_date = datetime.datetime.fromtimestamp(int(m.group(1)) / 1000)
            else:
                for fmt in ["%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        exp_date = datetime.datetime.strptime(str(not_after)[:19], fmt)
                        break
                    except ValueError:
                        continue

        if exp_date:
            if exp_date < now:
                data["expired"].append({"subject": subject, "expired": str(exp_date)})
            elif exp_date < d30:
                data["expiring_30d"].append({"subject": subject, "expires": str(exp_date)})
            elif exp_date < d90:
                data["expiring_90d"].append({"subject": subject, "expires": str(exp_date)})

        # Self-signed check
        if subject and issuer and subject == issuer:
            data["self_signed"].append({"subject": subject})

    data["total_certs"] = len(all_certs)
    done_line(f"Certificates — {data['total_certs']} found")
    return data


# ═══════════════════════════════════════════════
#  SECTION 4: NETWORK & CONNECTIONS
# ═══════════════════════════════════════════════

def audit_network():
    spinner_line("Network — Listening Ports")
    data = {}

    # Listening TCP
    listen = _ps_json("""
        Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Select-Object LocalAddress, LocalPort, OwningProcess,
        @{N='ProcessName';E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} |
        Sort-Object LocalPort
    """)
    if isinstance(listen, dict):
        listen = [listen]
    data["listening_tcp"] = listen or []

    # Established TCP
    spinner_line("Network — Active Connections")
    established = _ps_json("""
        Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue |
        Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, OwningProcess,
        @{N='ProcessName';E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} |
        Sort-Object RemoteAddress
    """)
    if isinstance(established, dict):
        established = [established]
    data["established_tcp"] = established or []

    # UDP
    spinner_line("Network — UDP Endpoints")
    udp = _ps_json("""
        Get-NetUDPEndpoint -ErrorAction SilentlyContinue |
        Select-Object LocalAddress, LocalPort, OwningProcess,
        @{N='ProcessName';E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} -First 50
    """)
    if isinstance(udp, dict):
        udp = [udp]
    data["udp_endpoints"] = udp or []

    # Network Adapters
    spinner_line("Network — Adapters")
    adapters = _ps_json("Get-NetAdapter -ErrorAction SilentlyContinue | Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed")
    if isinstance(adapters, dict):
        adapters = [adapters]
    data["adapters"] = adapters or []

    # IP Addresses
    ips = _ps_json("Get-NetIPAddress -ErrorAction SilentlyContinue | Where-Object {$_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1'} | Select-Object InterfaceAlias, IPAddress, PrefixLength")
    if isinstance(ips, dict):
        ips = [ips]
    data["ip_addresses"] = ips or []

    # VPN
    spinner_line("Network — VPN")
    vpn = _ps_json("Get-VpnConnection -ErrorAction SilentlyContinue | Select-Object Name, ServerAddress, ConnectionStatus, TunnelType")
    if isinstance(vpn, dict):
        vpn = [vpn]
    data["vpn_connections"] = vpn or []

    # Routes
    routes = _ps_json("Get-NetRoute -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.DestinationPrefix -ne '255.255.255.255/32'} | Select-Object DestinationPrefix, NextHop, InterfaceAlias, RouteMetric -First 30")
    if isinstance(routes, dict):
        routes = [routes]
    data["routes"] = routes or []

    # SMB Shares
    spinner_line("Network — Shares")
    shares = _ps_json("Get-SmbShare -ErrorAction SilentlyContinue | Select-Object Name, Path, Description")
    if isinstance(shares, dict):
        shares = [shares]
    data["smb_shares"] = shares or []

    # Firewall profiles
    fw = _ps_json("Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction")
    if isinstance(fw, dict):
        fw = [fw]
    data["firewall_profiles"] = fw or []

    done_line("Network & Connections")
    return data


# ═══════════════════════════════════════════════
#  SECTION 5: DOMAIN & MANAGEMENT
# ═══════════════════════════════════════════════

def audit_domain_management():
    spinner_line("Domain & Management")
    data = {}

    # Domain status
    cs = _ps_json("Get-CimInstance Win32_ComputerSystem | Select-Object Domain, PartOfDomain, DomainRole")
    data["computer_system"] = cs or {}

    # dsregcmd
    spinner_line("Domain & Management — Azure/MDM")
    dsreg = _run("dsregcmd /status 2>nul", timeout=15)
    parsed = {}
    if dsreg:
        for line in dsreg.splitlines():
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if key in ["AzureAdJoined", "DomainJoined", "EnterpriseJoined", "DeviceId", "TenantName", "MdmUrl"]:
                    parsed[key] = val
    data["dsregcmd"] = parsed

    # Group Policy
    spinner_line("Domain & Management — Group Policy")
    if is_admin():
        gp = _run("gpresult /r 2>nul", timeout=20)
        data["group_policy"] = gp.splitlines()[:30] if gp else ["Requires elevation or domain membership"]
    else:
        data["group_policy"] = ["Requires administrator privileges"]

    done_line("Domain & Management")
    return data


# ═══════════════════════════════════════════════
#  SECTION 6: THREAT DETECTION & IOCs
# ═══════════════════════════════════════════════

def audit_threat_detection(alert_level="medium"):
    spinner_line("Threat Detection — Process Analysis")
    data = {
        "findings": [],
        "severity_counts": {"critical": 0, "warning": 0, "info": 0},
        "browser_extensions": {"chrome": [], "firefox": [], "edge": []},
        "startup_items": [],
        "scheduled_tasks_suspicious": [],
        "cron_jobs": [],
        "environment_anomalies": [],
        "recent_system_modifications": [],
        "powershell_policy": "",
    }

    def add_finding(severity, category, detail):
        data["findings"].append({"severity": severity, "category": category, "detail": detail})
        data["severity_counts"][severity] += 1

    # Get running processes
    ps_out = _run_ps("Get-Process | Select-Object ProcessName, Id, Path, CPU | ConvertTo-Csv -NoTypeInformation")
    ps_lines = ps_out.splitlines()[1:] if ps_out else []

    # 6.1 Reverse shell patterns
    wmi_cmdlines = _run_ps_lines("Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -ne $null} | Select-Object -ExpandProperty CommandLine")
    rev_shell_patterns = [
        r"powershell.*-e\s+[A-Za-z0-9+/=]{20,}",  # encoded commands
        r"nc\.exe.*-e",
        r"ncat.*-e",
        r"cmd\.exe.*/c.*powershell.*IEX",
        r"Invoke-Expression.*Net\.WebClient",
        r"DownloadString\(",
        r"System\.Net\.Sockets",
        r"TCPClient",
        r"bash\s+-i.*>/dev/tcp",
    ]
    for cmdline in wmi_cmdlines:
        for pat in rev_shell_patterns:
            if re.search(pat, cmdline, re.IGNORECASE):
                add_finding("critical", "Reverse Shell", f"Suspicious command line: {cmdline[:120]}")
                break

    # 6.2 Processes from suspicious paths
    spinner_line("Threat Detection — Suspicious Paths")
    suspicious_paths = [
        os.environ.get("TEMP", "C:\\Temp"),
        os.environ.get("TMP", "C:\\Temp"),
        "C:\\Users\\Public",
        os.path.join(os.environ.get("APPDATA", ""), "..\\Local\\Temp"),
    ]
    for line in ps_lines:
        parts = line.replace('"', '').split(',')
        if len(parts) >= 3:
            proc_path = parts[2]
            if proc_path:
                for sp in suspicious_paths:
                    if sp and sp.lower() in proc_path.lower():
                        add_finding("warning", "Suspicious Process Path", f"{parts[0]} running from {proc_path[:80]}")
                        break

    # 6.3 Unsigned executables with network connections
    spinner_line("Threat Detection — Unsigned Network Binaries")
    net_procs = _run_ps_lines("""
        Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { (Get-Process -Id $_ -ErrorAction SilentlyContinue).Path } |
        Where-Object { $_ -ne $null } |
        Select-Object -Unique -First 20
    """)
    for proc_path in net_procs:
        if proc_path and os.path.isfile(proc_path):
            sig = _run_ps(f"(Get-AuthenticodeSignature '{proc_path}').Status", timeout=10)
            if sig and "Valid" not in sig:
                add_finding("warning", "Unsigned Network Binary", f"{os.path.basename(proc_path)}: Signature={sig}")

    # 6.4 Crypto miner indicators
    spinner_line("Threat Detection — Crypto Miners")
    for line in ps_lines:
        lower = line.lower()
        for miner in CRYPTO_MINER_NAMES:
            if miner in lower:
                add_finding("critical", "Crypto Miner", f"Process matching miner pattern: {line[:100]}")
                break

    # 6.5 Known malware process names
    for line in ps_lines:
        lower = line.lower()
        for mal in KNOWN_MALWARE_NAMES:
            if mal in lower:
                add_finding("critical", "Known Malware", f"Process matching malware name: {line[:100]}")
                break

    # 6.6 Non-standard listening ports
    spinner_line("Threat Detection — Suspicious Ports")
    listen_ports = _run_ps_lines("Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty LocalPort")
    for port_str in listen_ports:
        try:
            port = int(port_str.strip())
            if port in SUSPICIOUS_PORTS:
                proc = _run_ps(f"(Get-Process -Id (Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess) -ErrorAction SilentlyContinue).ProcessName")
                add_finding("warning", "Suspicious Port", f"Listening on port {port} — process: {proc or 'unknown'}")
        except (ValueError, TypeError):
            continue

    # 6.7 Connections to unusual port ranges
    est_ports = _run_ps_lines("Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Select-Object -ExpandProperty RemotePort")
    for port_str in est_ports:
        try:
            port = int(port_str.strip())
            if port > 10000 and port not in [443, 8443, 10443] and alert_level != "low":
                data["severity_counts"]["info"] += 1
        except (ValueError, TypeError):
            continue

    # 6.8 Recently created user accounts
    spinner_line("Threat Detection — Recent Accounts")
    recent_users = _run_ps_lines("""
        Get-LocalUser | Where-Object {
            $_.Enabled -eq $true -and
            $_.PasswordLastSet -gt (Get-Date).AddDays(-30)
        } | Select-Object -ExpandProperty Name
    """)
    for u in recent_users:
        add_finding("info", "Recent Account", f"Account '{u}' created/modified in last 30 days")

    # 6.9 Suspicious scheduled tasks
    spinner_line("Threat Detection — Scheduled Tasks")
    sus_tasks = _run_ps_lines("""
        Get-ScheduledTask | Where-Object {
            $_.State -eq 'Ready' -and $_.TaskPath -notlike '\\Microsoft\\*'
        } | ForEach-Object {
            $action = ($_ | Get-ScheduledTaskInfo -ErrorAction SilentlyContinue)
            $acts = $_.Actions | Select-Object -First 1
            "$($_.TaskName)|$($acts.Execute)|$($acts.Arguments)"
        } | Select-Object -First 30
    """)
    for task in sus_tasks:
        parts = task.split("|")
        if len(parts) >= 2:
            exe = parts[1] if len(parts) > 1 else ""
            args = parts[2] if len(parts) > 2 else ""
            lower_exe = (exe + args).lower()
            if any(s in lower_exe for s in ["temp", "appdata", "encoded", "hidden", "bypass", "-e ", "downloadstring"]):
                add_finding("warning", "Suspicious Task", f"Task '{parts[0]}' runs: {exe[:60]} {args[:40]}")
            data["scheduled_tasks_suspicious"].append({"name": parts[0], "execute": exe, "args": args})

    # 6.10 Startup items
    spinner_line("Threat Detection — Startup Items")
    startups = _ps_json("Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue | Select-Object Name, Command, Location, User")
    if isinstance(startups, dict):
        startups = [startups]
    data["startup_items"] = startups or []

    # 6.11 Browser extensions
    spinner_line("Threat Detection — Browser Extensions")
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
    roaming = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))

    # Chrome
    chrome_ext_dir = os.path.join(local, "Google", "Chrome", "User Data", "Default", "Extensions")
    if os.path.isdir(chrome_ext_dir):
        for ext_id in os.listdir(chrome_ext_dir):
            ext_path = os.path.join(chrome_ext_dir, ext_id)
            if os.path.isdir(ext_path):
                # Try to read manifest
                for ver_dir in os.listdir(ext_path):
                    manifest = os.path.join(ext_path, ver_dir, "manifest.json")
                    if os.path.isfile(manifest):
                        try:
                            with open(manifest, 'r', encoding='utf-8', errors='ignore') as f:
                                mdata = json.load(f)
                                data["browser_extensions"]["chrome"].append({
                                    "name": mdata.get("name", ext_id),
                                    "version": mdata.get("version", "?"),
                                    "id": ext_id,
                                })
                        except (json.JSONDecodeError, IOError):
                            data["browser_extensions"]["chrome"].append({"name": ext_id, "version": "?", "id": ext_id})
                        break

    # Edge
    edge_ext_dir = os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Extensions")
    if os.path.isdir(edge_ext_dir):
        for ext_id in os.listdir(edge_ext_dir):
            ext_path = os.path.join(edge_ext_dir, ext_id)
            if os.path.isdir(ext_path):
                for ver_dir in os.listdir(ext_path):
                    manifest = os.path.join(ext_path, ver_dir, "manifest.json")
                    if os.path.isfile(manifest):
                        try:
                            with open(manifest, 'r', encoding='utf-8', errors='ignore') as f:
                                mdata = json.load(f)
                                data["browser_extensions"]["edge"].append({
                                    "name": mdata.get("name", ext_id),
                                    "version": mdata.get("version", "?"),
                                })
                        except (json.JSONDecodeError, IOError):
                            data["browser_extensions"]["edge"].append({"name": ext_id, "version": "?"})
                        break

    # Firefox
    ff_profiles = os.path.join(roaming, "Mozilla", "Firefox", "Profiles")
    if os.path.isdir(ff_profiles):
        for profile in os.listdir(ff_profiles):
            ext_json = os.path.join(ff_profiles, profile, "extensions.json")
            if os.path.isfile(ext_json):
                try:
                    with open(ext_json, 'r', encoding='utf-8', errors='ignore') as f:
                        ext_data = json.load(f)
                        for addon in ext_data.get("addons", []):
                            if addon.get("type") == "extension":
                                data["browser_extensions"]["firefox"].append({
                                    "name": addon.get("defaultLocale", {}).get("name", addon.get("id", "?")),
                                    "version": addon.get("version", "?"),
                                    "id": addon.get("id", "?"),
                                })
                except (json.JSONDecodeError, IOError):
                    pass
                break

    # 6.12 Environment variable anomalies
    spinner_line("Threat Detection — Environment")
    path_val = os.environ.get("PATH", "")
    for entry in path_val.split(";"):
        entry_lower = entry.lower().strip()
        if any(s in entry_lower for s in ["temp", "tmp", "public", "downloads"]):
            if entry_lower and entry_lower not in ["", "."]:
                add_finding("warning", "Suspicious PATH", f"PATH contains: {entry[:80]}")
                data["environment_anomalies"].append(entry)

    # 6.13 Recently modified system files
    spinner_line("Threat Detection — Recent System Modifications")
    recent = _run_ps_lines("""
        Get-ChildItem 'C:\\Windows\\System32' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
        Select-Object -ExpandProperty Name -First 30
    """)
    data["recent_system_modifications"] = recent

    # 6.14 PowerShell execution policy & history
    data["powershell_policy"] = _run_ps("Get-ExecutionPolicy")
    ps_history = os.path.join(roaming, "Microsoft", "Windows", "PowerShell", "PSReadLine", "ConsoleHost_history.txt")
    if os.path.isfile(ps_history):
        try:
            size = os.path.getsize(ps_history)
            data["powershell_history_size_kb"] = round(size / 1024, 1)
        except OSError:
            pass

    done_line("Threat Detection & IOCs")
    return data


# ═══════════════════════════════════════════════
#  SECTION 7: EDR / COMPLIANCE POSTURE
# ═══════════════════════════════════════════════

def audit_compliance():
    spinner_line("Compliance — Security Checks")
    checks = []

    def add_check(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    # BitLocker
    bl = _run("manage-bde -status C: 2>nul", timeout=15)
    if bl:
        if "Percentage Encrypted" in bl and "100" in bl:
            add_check("BitLocker", "PASS", "C: drive fully encrypted")
        elif "Fully Decrypted" in bl or "Protection Off" in bl:
            add_check("BitLocker", "FAIL", "C: drive is NOT encrypted")
        else:
            add_check("BitLocker", "WARN", f"BitLocker status unclear")
    else:
        bl_ps = _run_ps("(Get-BitLockerVolume -MountPoint C: -ErrorAction SilentlyContinue).ProtectionStatus")
        if bl_ps == "On":
            add_check("BitLocker", "PASS", "C: drive encrypted")
        elif bl_ps == "Off":
            add_check("BitLocker", "FAIL", "C: drive NOT encrypted")
        else:
            add_check("BitLocker", "WARN", "Cannot determine BitLocker status (may require admin)")

    # Windows Defender
    spinner_line("Compliance — Defender")
    defender = _ps_json("Get-MpComputerStatus -ErrorAction SilentlyContinue | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled, AntivirusSignatureLastUpdated, NISEnabled")
    if defender:
        if defender.get("RealTimeProtectionEnabled"):
            add_check("Defender Real-Time Protection", "PASS", "Real-time protection enabled")
        else:
            add_check("Defender Real-Time Protection", "FAIL", "Real-time protection DISABLED")

        if defender.get("AntivirusEnabled"):
            add_check("Defender Antivirus", "PASS", "Antivirus enabled")
        else:
            add_check("Defender Antivirus", "FAIL", "Antivirus DISABLED")

        sig_date = str(defender.get("AntivirusSignatureLastUpdated", ""))
        add_check("Defender Signatures", "PASS" if sig_date else "WARN", f"Last updated: {sig_date[:19]}")
    else:
        add_check("Windows Defender", "WARN", "Cannot query Defender status (may require admin)")

    # Firewall — 3 profiles
    spinner_line("Compliance — Firewall")
    fw_profiles = _ps_json("Get-NetFirewallProfile -ErrorAction SilentlyContinue | Select-Object Name, Enabled")
    if isinstance(fw_profiles, dict):
        fw_profiles = [fw_profiles]
    if fw_profiles:
        for prof in fw_profiles:
            name = prof.get("Name", "Unknown")
            enabled = prof.get("Enabled", False)
            # Handle both boolean True and integer 1
            is_enabled = enabled is True or enabled == 1 or str(enabled).lower() == "true"
            add_check(f"Firewall ({name})", "PASS" if is_enabled else "FAIL",
                      f"{name} profile: {'Enabled' if is_enabled else 'DISABLED'}")
    else:
        add_check("Firewall", "WARN", "Cannot query firewall profiles")

    # UAC
    uac = _run('reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA 2>nul')
    if "0x1" in uac:
        add_check("UAC", "PASS", "User Account Control is enabled")
    elif "0x0" in uac:
        add_check("UAC", "FAIL", "User Account Control is DISABLED")
    else:
        add_check("UAC", "WARN", "Cannot determine UAC status")

    # Secure Boot
    spinner_line("Compliance — Secure Boot")
    sb = _run_ps("try { Confirm-SecureBootUEFI } catch { 'Error' }", timeout=10)
    if sb == "True":
        add_check("Secure Boot", "PASS", "Secure Boot is enabled")
    elif sb == "False":
        add_check("Secure Boot", "FAIL", "Secure Boot is DISABLED")
    else:
        add_check("Secure Boot", "WARN", "Cannot determine Secure Boot status (legacy BIOS?)")

    # Windows Update recency
    spinner_line("Compliance — Updates")
    hotfix = _run_ps("Get-HotFix -ErrorAction SilentlyContinue | Sort-Object InstalledOn -Descending | Select-Object -First 1 -ExpandProperty InstalledOn")
    if hotfix:
        add_check("Windows Update", "PASS", f"Last update installed: {hotfix[:10]}")
    else:
        add_check("Windows Update", "WARN", "Cannot determine last update date")

    # SMBv1
    smb1 = _run_ps("(Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -ErrorAction SilentlyContinue).State")
    if smb1:
        if "Disabled" in smb1:
            add_check("SMBv1", "PASS", "SMBv1 protocol is disabled")
        elif "Enabled" in smb1:
            add_check("SMBv1", "FAIL", "SMBv1 protocol is ENABLED (vulnerable)")
        else:
            add_check("SMBv1", "WARN", f"SMBv1 status: {smb1}")
    else:
        add_check("SMBv1", "WARN", "Cannot query SMBv1 status (may require admin)")

    # Remote Desktop
    rdp = _run('reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections 2>nul')
    if "0x1" in rdp:
        add_check("Remote Desktop", "PASS", "Remote Desktop is disabled")
    elif "0x0" in rdp:
        add_check("Remote Desktop", "WARN", "Remote Desktop is ENABLED")
    else:
        add_check("Remote Desktop", "WARN", "Cannot determine RDP status")

    # Guest account
    guest = _run_ps("(Get-LocalUser -Name Guest -ErrorAction SilentlyContinue).Enabled")
    if guest == "False":
        add_check("Guest Account", "PASS", "Guest account is disabled")
    elif guest == "True":
        add_check("Guest Account", "FAIL", "Guest account is ENABLED")
    else:
        add_check("Guest Account", "WARN", "Cannot determine guest account status")

    # Password policy
    spinner_line("Compliance — Password Policy")
    net_accts = _run("net accounts 2>nul")
    if net_accts:
        min_len_match = re.search(r"Minimum password length\s+(\d+)", net_accts)
        if min_len_match:
            min_len = int(min_len_match.group(1))
            if min_len >= 8:
                add_check("Password Min Length", "PASS", f"Minimum password length: {min_len}")
            else:
                add_check("Password Min Length", "FAIL", f"Minimum password length: {min_len} (should be ≥8)")
        lockout_match = re.search(r"Lockout threshold\s+(\w+)", net_accts)
        if lockout_match:
            val = lockout_match.group(1)
            if val.lower() == "never":
                add_check("Account Lockout", "FAIL", "Account lockout threshold: Never")
            else:
                add_check("Account Lockout", "PASS", f"Account lockout threshold: {val}")

    # Credential Guard
    cg = _run('reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\DeviceGuard" /v EnableVirtualizationBasedSecurity 2>nul')
    if "0x1" in cg:
        add_check("Credential Guard", "PASS", "Virtualization-based security enabled")
    elif "0x0" in cg:
        add_check("Credential Guard", "FAIL", "Virtualization-based security disabled")
    else:
        add_check("Credential Guard", "WARN", "Cannot determine Credential Guard status")

    # Auto-updates
    auto_update = _run('reg query "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v NoAutoUpdate 2>nul')
    if "0x0" in auto_update or "not found" in auto_update.lower() or not auto_update:
        add_check("Auto-Updates", "PASS", "Automatic updates are enabled")
    elif "0x1" in auto_update:
        add_check("Auto-Updates", "FAIL", "Automatic updates are DISABLED")

    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")
    warnings = sum(1 for c in checks if c["status"] == "WARN")

    done_line("Compliance Posture")
    return {
        "checks": checks,
        "total": len(checks),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════
#  SECTION 8: LOGS & FORENSIC SNAPSHOT
# ═══════════════════════════════════════════════

def audit_logs_forensics():
    spinner_line("Logs & Forensics — Event Logs")
    data = {}

    # 8.1 Failed logins (Event 4625)
    failed = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 20 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated): $($_.Message.Split([char]10)[0])" }
        } catch { 'No events found or access denied' }
    """, timeout=20)
    data["failed_logins"] = failed or ["No failed logins found or access denied"]

    # 8.2 Successful logins (Event 4624)
    spinner_line("Logs & Forensics — Login History")
    success = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='Security';Id=4624} -MaxEvents 15 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated): $($_.Message.Split([char]10)[0])" }
        } catch { 'No events found or access denied' }
    """, timeout=20)
    data["successful_logins"] = success or ["No data or access denied"]

    # 8.3 Privilege escalation (Event 4672)
    priv = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='Security';Id=4672} -MaxEvents 10 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated): $($_.Message.Split([char]10)[0])" }
        } catch { 'No events found or access denied' }
    """, timeout=15)
    data["privilege_escalation"] = priv or ["No data or access denied"]

    # 8.4 RDP sessions (Events 4778/4779)
    spinner_line("Logs & Forensics — RDP Sessions")
    rdp = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='Security';Id=4778,4779} -MaxEvents 10 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated) [ID:$($_.Id)]: $($_.Message.Split([char]10)[0])" }
        } catch { 'No RDP events found' }
    """, timeout=15)
    data["rdp_sessions"] = rdp or ["No RDP sessions found"]

    # 8.5 Service installs (Event 7045)
    spinner_line("Logs & Forensics — Service Installs")
    svc = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='System';Id=7045} -MaxEvents 15 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated): $($_.Message.Split([char]10)[0])" }
        } catch { 'No service install events found' }
    """, timeout=15)
    data["service_installs"] = svc or ["No service install events found"]

    # 8.6 PowerShell script block logging (Event 4104)
    ps_blocks = _run_ps_lines("""
        try {
            Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational';Id=4104} -MaxEvents 10 -ErrorAction Stop |
            ForEach-Object { "$($_.TimeCreated): $($_.Message.Substring(0, [Math]::Min(150, $_.Message.Length)))" }
        } catch { 'No PowerShell script block logs found' }
    """, timeout=15)
    data["powershell_script_blocks"] = ps_blocks or ["No script block logs found"]

    # 8.7 Recent downloads
    spinner_line("Logs & Forensics — Downloads")
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    recent_downloads = []
    if os.path.isdir(downloads_dir):
        now = datetime.datetime.now().timestamp()
        seven_days = 7 * 86400
        try:
            for f in os.listdir(downloads_dir):
                fp = os.path.join(downloads_dir, f)
                if os.path.isfile(fp):
                    mtime = os.path.getmtime(fp)
                    if now - mtime < seven_days:
                        recent_downloads.append({
                            "name": f,
                            "size_kb": round(os.path.getsize(fp) / 1024, 1),
                            "modified": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                        })
        except OSError:
            pass
    data["recent_downloads"] = sorted(recent_downloads, key=lambda x: x.get("modified", ""), reverse=True)[:30]

    # 8.8 Mounted drives
    drives = _ps_json("Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | Select-Object Name, Root, @{N='UsedGB';E={[math]::Round($_.Used/1GB,1)}}, @{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}}")
    if isinstance(drives, dict):
        drives = [drives]
    data["mounted_drives"] = drives or []

    # Network shares
    mappings = _ps_json("Get-SmbMapping -ErrorAction SilentlyContinue | Select-Object LocalPath, RemotePath, Status")
    if isinstance(mappings, dict):
        mappings = [mappings]
    data["network_mappings"] = mappings or []

    done_line("Logs & Forensics")
    return data


# ═══════════════════════════════════════════════
#  GUIDANCE & REMEDIATION ENGINE
# ═══════════════════════════════════════════════

GUIDANCE_DB = {
    "BitLocker": {
        "risk": "Unencrypted disk exposes all data if device is lost or stolen.",
        "fix": "Enable-BitLocker -MountPoint 'C:' -EncryptionMethod XtsAes256 -UsedSpaceOnly -RecoveryPasswordProtector",
        "settings": "Settings > Privacy & Security > Device Encryption",
        "cis": "CIS 18.9.11.1",
    },
    "Defender Real-Time Protection": {
        "risk": "Without real-time protection, malware can execute without detection.",
        "fix": "Set-MpPreference -DisableRealtimeMonitoring $false",
        "settings": "Settings > Privacy & Security > Windows Security > Virus & threat protection",
        "cis": "CIS 18.9.47.4.1",
    },
    "Defender Antivirus": {
        "risk": "Disabled antivirus leaves the system vulnerable to all malware types.",
        "fix": "Set-MpPreference -DisableRealtimeMonitoring $false",
        "settings": "Settings > Privacy & Security > Windows Security > Virus & threat protection",
        "cis": "CIS 18.9.47.4.1",
    },
    "Defender Signatures": {
        "risk": "Outdated signatures miss recently discovered threats.",
        "fix": "Update-MpSignature",
        "settings": "Windows Security > Virus & threat protection > Check for updates",
        "cis": "CIS 18.9.47.10",
    },
    "Firewall (Domain)": {
        "risk": "Disabled domain firewall exposes the system to lateral movement attacks.",
        "fix": "Set-NetFirewallProfile -Profile Domain -Enabled True",
        "settings": "Settings > Privacy & Security > Windows Security > Firewall",
        "cis": "CIS 9.1.1",
    },
    "Firewall (Private)": {
        "risk": "Disabled private firewall leaves the system open on trusted networks.",
        "fix": "Set-NetFirewallProfile -Profile Private -Enabled True",
        "settings": "Settings > Privacy & Security > Windows Security > Firewall",
        "cis": "CIS 9.2.1",
    },
    "Firewall (Public)": {
        "risk": "Disabled public firewall exposes the system on untrusted networks.",
        "fix": "Set-NetFirewallProfile -Profile Public -Enabled True",
        "settings": "Settings > Privacy & Security > Windows Security > Firewall",
        "cis": "CIS 9.3.1",
    },
    "UAC": {
        "risk": "Without UAC, all programs run with full admin rights, enabling malware escalation.",
        "fix": 'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 1 /f',
        "settings": "Control Panel > User Accounts > Change User Account Control settings",
        "cis": "CIS 2.3.17.6",
    },
    "Secure Boot": {
        "risk": "Without Secure Boot, rootkits can load before the OS and evade all security software.",
        "fix": "Enable Secure Boot in UEFI/BIOS firmware settings (requires restart).",
        "settings": "UEFI Firmware Settings (restart required)",
        "cis": "CIS 1.1.1",
    },
    "SMBv1": {
        "risk": "SMBv1 is vulnerable to EternalBlue (WannaCry, NotPetya) and should be disabled.",
        "fix": "Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -NoRestart",
        "settings": "Turn Windows Features on or off > SMB 1.0/CIFS File Sharing Support",
        "cis": "CIS 18.3.3",
    },
    "Remote Desktop": {
        "risk": "Enabled RDP increases attack surface for brute force and credential theft.",
        "fix": 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 1 /f',
        "settings": "Settings > System > Remote Desktop",
        "cis": "CIS 18.8.36.1",
    },
    "Guest Account": {
        "risk": "Enabled guest account provides unauthenticated local access.",
        "fix": "Disable-LocalUser -Name Guest",
        "settings": "Computer Management > Local Users and Groups > Users",
        "cis": "CIS 1.1.2",
    },
    "Password Min Length": {
        "risk": "Short passwords are vulnerable to brute force attacks.",
        "fix": "net accounts /minpwlen:12",
        "settings": "Local Security Policy > Account Policies > Password Policy",
        "cis": "CIS 1.1.4",
    },
    "Account Lockout": {
        "risk": "Without lockout, attackers can brute-force passwords indefinitely.",
        "fix": "net accounts /lockoutthreshold:5",
        "settings": "Local Security Policy > Account Policies > Account Lockout Policy",
        "cis": "CIS 1.2.1",
    },
    "Credential Guard": {
        "risk": "Without Credential Guard, credentials in memory can be dumped by tools like Mimikatz.",
        "fix": 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\DeviceGuard" /v EnableVirtualizationBasedSecurity /t REG_DWORD /d 1 /f',
        "settings": "Group Policy > Computer Configuration > Administrative Templates > Device Guard",
        "cis": "CIS 18.8.5.1",
    },
    "Auto-Updates": {
        "risk": "Without automatic updates, known vulnerabilities remain unpatched.",
        "fix": 'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v NoAutoUpdate /f',
        "settings": "Settings > Windows Update > Advanced options",
        "cis": "CIS 18.9.102.1",
    },
}


def generate_guidance_section(audit_data):
    """Generate remediation guidance from compliance failures and threat findings."""
    guidance = []

    # From compliance checks
    compliance = audit_data.get("compliance", {})
    for check in compliance.get("checks", []):
        if check["status"] in ("FAIL", "WARN"):
            name = check["check"]
            g = GUIDANCE_DB.get(name, {})
            guidance.append({
                "check": name,
                "status": check["status"],
                "detail": check["detail"],
                "risk": g.get("risk", "This check did not pass and may indicate a security weakness."),
                "fix": g.get("fix", "Consult your IT security team for remediation."),
                "settings": g.get("settings", ""),
                "cis": g.get("cis", ""),
            })

    # From threat findings (critical/warning only)
    threats = audit_data.get("threat_detection", {})
    for finding in threats.get("findings", []):
        if finding["severity"] in ("critical", "warning"):
            guidance.append({
                "check": finding["category"],
                "status": "CRITICAL" if finding["severity"] == "critical" else "WARNING",
                "detail": finding["detail"],
                "risk": f"Threat detected: {finding['category']} — requires immediate investigation.",
                "fix": "Investigate the process, terminate if malicious, and scan with Windows Defender.",
                "settings": "Windows Security > Virus & threat protection > Quick scan",
                "cis": "",
            })

    return guidance


# ═══════════════════════════════════════════════
#  FULL AUDIT RUNNER
# ═══════════════════════════════════════════════

def run_full_audit(alert_level="medium"):
    """Run all 8 audit sections and return combined results."""
    print(f"\n  {CYAN}{BOLD}WinDNA Security & Asset Audit{RESET}")
    print(f"  {'─' * 40}")
    if is_admin():
        print(f"  {GREEN}Running as Administrator — full access{RESET}\n")
    else:
        print(f"  {YELLOW}Running without admin — some checks limited{RESET}")
        print(f"  {DIM}Tip: Run as Administrator for best results{RESET}\n")

    results = {
        "metadata": {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hostname": platform.node(),
            "os_version": platform.platform(),
            "architecture": platform.machine(),
            "elevated": is_admin(),
            "alert_level": alert_level,
        },
        "asset_intelligence": audit_asset_intelligence(),
        "user_accounts": audit_user_accounts(),
        "certificates": audit_certificates(),
        "network": audit_network(),
        "domain_management": audit_domain_management(),
        "threat_detection": audit_threat_detection(alert_level),
        "compliance": audit_compliance(),
        "logs_forensics": audit_logs_forensics(),
    }

    results["guidance"] = generate_guidance_section(results)

    # Summary
    comp = results["compliance"]
    threats = results["threat_detection"]["severity_counts"]
    print(f"\n  {'═' * 40}")
    print(f"  {BOLD}AUDIT SUMMARY{RESET}")
    print(f"  {'─' * 40}")
    print(f"  Compliance: {GREEN}{comp['passed']} passed{RESET} | {RED}{comp['failed']} failed{RESET} | {YELLOW}{comp['warnings']} warnings{RESET}")
    print(f"  Threats:    {RED}{threats['critical']} critical{RESET} | {YELLOW}{threats['warning']} warning{RESET} | {threats['info']} info")
    print(f"  Guidance:   {len(results['guidance'])} remediation items")
    print(f"  {'═' * 40}\n")

    return results


# ═══════════════════════════════════════════════
#  HTML REPORT GENERATOR
# ═══════════════════════════════════════════════

def generate_audit_html(audit_data, filepath):
    """Generate a dark-themed interactive HTML audit report."""
    meta = audit_data.get("metadata", {})
    comp = audit_data.get("compliance", {})
    threats = audit_data.get("threat_detection", {})
    guidance = audit_data.get("guidance", [])

    esc = html_mod.escape

    def json_block(obj):
        return esc(json.dumps(obj, indent=2, default=str))

    # Count stats
    total_checks = comp.get("total", 0)
    passed = comp.get("passed", 0)
    failed = comp.get("failed", 0)
    critical_findings = threats.get("severity_counts", {}).get("critical", 0)
    warning_findings = threats.get("severity_counts", {}).get("warning", 0)

    sections_html = ""

    # Build each audit section
    section_map = [
        ("Asset Intelligence", "asset_intelligence", "💻"),
        ("User Accounts & Access", "user_accounts", "👤"),
        ("Certificates", "certificates", "📜"),
        ("Network & Connections", "network", "🌐"),
        ("Domain & Management", "domain_management", "🏢"),
        ("Threat Detection & IOCs", "threat_detection", "🔍"),
        ("Compliance Posture", "compliance", "🛡️"),
        ("Logs & Forensics", "logs_forensics", "📋"),
    ]

    for title, key, icon in section_map:
        section_data = audit_data.get(key, {})

        # Special rendering for compliance checks
        if key == "compliance":
            items_html = ""
            for chk in section_data.get("checks", []):
                status = chk["status"]
                color = "#3fb950" if status == "PASS" else "#f85149" if status == "FAIL" else "#d29922"
                items_html += f'<div class="check-item" style="border-left:3px solid {color};padding:8px 12px;margin:6px 0;background:#161b22;border-radius:4px;"><span style="color:{color};font-weight:bold;">[{esc(status)}]</span> <strong>{esc(chk["check"])}</strong> — {esc(chk["detail"])}</div>\n'
            content = items_html
        elif key == "threat_detection":
            items_html = ""
            for f in section_data.get("findings", []):
                sev = f["severity"]
                color = "#f85149" if sev == "critical" else "#d29922" if sev == "warning" else "#8b949e"
                items_html += f'<div class="check-item" style="border-left:3px solid {color};padding:8px 12px;margin:6px 0;background:#161b22;border-radius:4px;"><span style="color:{color};font-weight:bold;">[{esc(sev.upper())}]</span> <strong>{esc(f["category"])}</strong> — {esc(f["detail"])}</div>\n'
            if not items_html:
                items_html = '<div style="color:#3fb950;padding:12px;">No threats detected ✓</div>'

            # Add browser extensions
            ext = section_data.get("browser_extensions", {})
            for browser, exts in ext.items():
                if exts:
                    items_html += f'<h4 style="color:#8b949e;margin-top:16px;">{esc(browser.title())} Extensions ({len(exts)})</h4>'
                    for e in exts:
                        items_html += f'<div style="padding:4px 12px;color:#c9d1d9;">{esc(str(e.get("name","?")))}</div>'
            content = items_html
        else:
            content = f'<pre style="color:#c9d1d9;overflow-x:auto;font-size:13px;">{json_block(section_data)}</pre>'

        sections_html += f"""
        <div class="section" id="section-{key}">
            <div class="section-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <span>{icon} {esc(title)}</span>
                <span class="toggle">▼</span>
            </div>
            <div class="section-body">{content}</div>
        </div>
        """

    # Guidance section
    guidance_html = ""
    if guidance:
        for g in guidance:
            status = g["status"]
            color = "#f85149" if status in ("FAIL", "CRITICAL") else "#d29922"
            guidance_html += f"""
            <div class="guidance-item" style="border-left:3px solid {color};padding:12px;margin:10px 0;background:#161b22;border-radius:6px;">
                <div style="color:{color};font-weight:bold;font-size:15px;">{esc(g['check'])}</div>
                <div style="color:#c9d1d9;margin:6px 0;">{esc(g['detail'])}</div>
                <div style="margin-top:8px;">
                    <div><strong style="color:#58a6ff;">Risk:</strong> <span style="color:#c9d1d9;">{esc(g['risk'])}</span></div>
                    <div style="margin-top:4px;"><strong style="color:#3fb950;">Fix:</strong> <code style="background:#0d1117;padding:4px 8px;border-radius:4px;color:#f0883e;font-size:13px;">{esc(g['fix'])}</code></div>
                    {"<div style='margin-top:4px;'><strong style='color:#8b949e;'>Settings:</strong> <span style='color:#8b949e;'>" + esc(g['settings']) + "</span></div>" if g.get('settings') else ""}
                    {"<div style='margin-top:4px;'><strong style='color:#8b949e;'>CIS Ref:</strong> <span style='color:#8b949e;'>" + esc(g['cis']) + "</span></div>" if g.get('cis') else ""}
                </div>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WinDNA Security Audit — {esc(meta.get('hostname',''))}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; padding:20px; }}
.header {{ text-align:center; padding:30px 0; border-bottom:1px solid #21262d; margin-bottom:24px; }}
.header h1 {{ color:#58a6ff; font-size:28px; margin-bottom:8px; }}
.header .meta {{ color:#8b949e; font-size:14px; }}
.header .meta span {{ margin:0 12px; }}
.stats {{ display:flex; gap:16px; justify-content:center; flex-wrap:wrap; margin-bottom:24px; }}
.stat-card {{ background:#161b22; border:1px solid #21262d; border-radius:8px; padding:20px 28px; text-align:center; min-width:140px; }}
.stat-card .number {{ font-size:32px; font-weight:bold; }}
.stat-card .label {{ font-size:13px; color:#8b949e; margin-top:4px; }}
.search-box {{ margin:0 auto 24px; max-width:500px; }}
.search-box input {{ width:100%; padding:10px 16px; background:#161b22; border:1px solid #30363d; border-radius:8px; color:#c9d1d9; font-size:14px; outline:none; }}
.search-box input:focus {{ border-color:#58a6ff; }}
.section {{ background:#0d1117; border:1px solid #21262d; border-radius:8px; margin-bottom:12px; overflow:hidden; }}
.section-header {{ padding:14px 20px; background:#161b22; cursor:pointer; display:flex; justify-content:space-between; align-items:center; font-weight:600; font-size:15px; color:#c9d1d9; }}
.section-header:hover {{ background:#1c2128; }}
.section.collapsed .section-body {{ display:none; }}
.section.collapsed .toggle {{ transform:rotate(-90deg); }}
.toggle {{ transition:transform 0.2s; color:#8b949e; }}
.section-body {{ padding:16px 20px; }}
.guidance-section {{ margin-top:30px; }}
.guidance-section h2 {{ color:#f0883e; font-size:20px; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #21262d; }}
.footer {{ text-align:center; color:#484f58; font-size:12px; margin-top:40px; padding:20px; border-top:1px solid #21262d; }}
</style>
</head>
<body>

<div class="header">
    <h1>🧬 WinDNA Security Audit</h1>
    <div class="meta">
        <span>🖥️ {esc(meta.get('hostname',''))}</span>
        <span>📅 {esc(meta.get('timestamp',''))}</span>
        <span>🏗️ {esc(meta.get('architecture',''))}</span>
        <span>{'🔑 Elevated' if meta.get('elevated') else '👤 Standard'}</span>
    </div>
</div>

<div class="stats">
    <div class="stat-card"><div class="number" style="color:#58a6ff;">{total_checks}</div><div class="label">Total Checks</div></div>
    <div class="stat-card"><div class="number" style="color:#3fb950;">{passed}</div><div class="label">Passed</div></div>
    <div class="stat-card"><div class="number" style="color:#f85149;">{failed}</div><div class="label">Failed</div></div>
    <div class="stat-card"><div class="number" style="color:#f85149;">{critical_findings}</div><div class="label">Critical</div></div>
    <div class="stat-card"><div class="number" style="color:#d29922;">{warning_findings}</div><div class="label">Warnings</div></div>
    <div class="stat-card"><div class="number" style="color:#f0883e;">{len(guidance)}</div><div class="label">Remediation</div></div>
</div>

<div class="search-box">
    <input type="text" id="searchInput" placeholder="Search audit results..." oninput="filterSections(this.value)">
</div>

{sections_html}

<div class="guidance-section">
    <h2>🔧 Guidance & Remediation</h2>
    {guidance_html if guidance_html else '<div style="color:#3fb950;padding:12px;">All checks passed — no remediation needed ✓</div>'}
</div>

<div class="footer">
    WinDNA v1.0 | Author: cyberspartan77 | Generated: {esc(meta.get('timestamp',''))}
</div>

<script>
function filterSections(query) {{
    const q = query.toLowerCase();
    document.querySelectorAll('.section').forEach(s => {{
        const text = s.textContent.toLowerCase();
        s.style.display = text.includes(q) ? '' : 'none';
        if (q && text.includes(q)) s.classList.remove('collapsed');
    }});
    document.querySelectorAll('.guidance-item').forEach(g => {{
        g.style.display = g.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}}
</script>

</body>
</html>"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)


# ═══════════════════════════════════════════════
#  MODULE ENTRY POINT (for testing)
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    results = run_full_audit()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles", "audit_test")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "audit.json")
    html_path = os.path.join(out_dir, "audit.html")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    generate_audit_html(results, html_path)
    print(f"  Saved: {json_path}")
    print(f"  Saved: {html_path}")
