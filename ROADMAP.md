# WinDNA — Windows System DNA Capture & Deploy Tool
## Roadmap v1.0
### Author: cyberspartan77

---

## Overview
WinDNA captures, backs up, and deploys Windows system settings, user preferences, and security posture — the Windows counterpart to MacDNA. Ships in **two formats**: Python (`windna.py`) and PowerShell (`windna.ps1`) so Windows users have options.

**GitHub:** https://github.com/fjimenez77/WinDNA

---

## Architecture

### Dual Delivery
| | `windna.py` | `windna.ps1` |
|---|---|---|
| **Runtime** | Python 3.8+ | PowerShell 5.1+ (built into Windows) |
| **Best for** | Cross-platform teams, devs with Python | Sysadmins, zero-install, GPO deployment |
| **Features** | Full parity | Full parity |

### Auto-Detect Architecture
- **x64** — Standard Intel/AMD 64-bit (most common)
- **x86** — Legacy 32-bit systems
- **ARM** — Surface Pro X, Snapdragon laptops, Windows on ARM

One script auto-detects and adjusts paths (`System32` vs `SysWOW64` vs `SysArm32`).

### Folder Structure
```
WinDNA/
├── windna.py              # Python version (interactive menu)
├── windna.ps1             # PowerShell version (interactive menu)
├── profiles/              # Captured profiles (shared)
├── settings.json          # App settings
├── README.md
└── .gitignore
```

---

## Feature Parity with MacDNA

### Main Menu (Interactive, numbered)
1. Capture System DNA
2. Deploy System DNA
3. View Saved Profiles
4. Compare Profiles
5. Delete Profile
6. Security & Asset Audit
7. Settings
8. Exit WinDNA

### Capture Categories
| # | Category | Windows Commands |
|---|---|---|
| 1 | Desktop & Appearance | `reg query HKCU\...\Desktop`, `Get-ItemProperty` |
| 2 | Taskbar & Start Menu | Registry keys for taskbar layout, pinned apps |
| 3 | File Explorer Settings | `reg query HKCU\...\Advanced` (hidden files, extensions, etc.) |
| 4 | Mouse & Keyboard | `reg query HKCU\Control Panel\Mouse`, keyboard repeat rate |
| 5 | Sound & Notifications | Volume, notification settings, focus assist |
| 6 | Power & Sleep | `powercfg /query`, sleep/hibernate settings |
| 7 | Network Settings | Saved Wi-Fi profiles (`netsh wlan`), proxy, DNS |
| 8 | Privacy & Security | Location, camera, microphone permissions |
| 9 | Default Apps | File associations, browser, email client |
| 10 | Installed Apps List | `Get-AppxPackage`, `Get-CimInstance Win32_Product` |

### Deploy Categories
Apply captured settings to a new Windows machine via registry writes, PowerShell commands, and `netsh` imports.

### Output
- Folder-per-capture: `profiles/<ComputerName_Date>/`
- `profile.json` — full capture data
- `profile.html` — interactive dark-theme HTML viewer with search, collapsible sections

---

## Security & Asset Audit Module

### Section 1 — Asset Intelligence
- CPU, cores, threads, RAM, GPU via `Get-CimInstance Win32_Processor/PhysicalMemory/VideoController`
- Storage: `Get-Volume`, `Get-PhysicalDisk` (type, size, BitLocker status)
- Battery: `Get-CimInstance Win32_Battery` (health, cycle count)
- Display: `Get-CimInstance Win32_DesktopMonitor`
- USB: `Get-PnpDevice -Class USB`
- Bluetooth: `Get-PnpDevice -Class Bluetooth`
- Printers: `Get-Printer`
- Serial, model, BIOS: `Get-CimInstance Win32_BIOS`, `Win32_ComputerSystem`

### Section 2 — User Accounts & Access
- Local users: `Get-LocalUser` (admin status, last logon, enabled/disabled)
- Local groups: `Get-LocalGroupMember -Group Administrators`
- RDP users, remote desktop settings
- Scheduled tasks as persistence: `Get-ScheduledTask`

### Section 3 — Certificates
- `Get-ChildItem Cert:\LocalMachine\My`, `Cert:\CurrentUser\My`
- Expiry, issuer, self-signed flags
- Flag expiring within 30/60/90 days

### Section 4 — Network & Connections
- Listening ports: `Get-NetTCPConnection -State Listen`
- Established connections: `Get-NetTCPConnection -State Established`
- UDP: `Get-NetUDPEndpoint`
- Interfaces: `Get-NetIPAddress`, `Get-NetAdapter`
- Active VPN: `Get-VpnConnection`
- Routing table: `Get-NetRoute`
- Firewall rules: `Get-NetFirewallRule`
- Shares: `Get-SmbShare`

### Section 5 — Domain & Management
- Domain join status: `Get-CimInstance Win32_ComputerSystem`
- Active Directory info: `dsquery`, `gpresult /r`
- MDM/Intune enrollment: `dsregcmd /status`
- Group Policy applied: `gpresult /r`

### Section 6 — Threat Detection & IOCs
- Suspicious processes from temp dirs
- Unsigned executables with network access: `Get-AuthenticodeSignature`
- Crypto miner indicators
- Known malware process names
- Non-standard listening ports
- Connections to unusual port ranges
- Recently created user accounts
- Scheduled tasks in suspicious locations (persistence)
- Startup items: `Get-CimInstance Win32_StartupCommand`
- Browser extensions (Chrome/Firefox/Edge)
- Environment variable anomalies
- Recently modified system files (`C:\Windows\System32`, last 7 days)
- PowerShell execution policy & history

### Section 7 — EDR / Compliance Posture
- BitLocker status: `Get-BitLockerVolume`
- Windows Defender: `Get-MpComputerStatus`
- Firewall: `Get-NetFirewallProfile`
- UAC level: registry check
- Secure Boot: `Confirm-SecureBootUEFI`
- Windows Update status: `Get-WindowsUpdateLog`
- SMBv1 disabled check
- Remote Desktop enabled check
- Guest account status
- Password policy: `net accounts`
- Audit policy: `auditpol /get /category:*`
- Credential Guard status

### Section 8 — Logs & Forensic Snapshot
- Failed logins (48h): `Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625}`
- Successful logins: Event ID 4624
- Privilege escalation: Event ID 4672
- RDP sessions: Event ID 4778/4779
- PowerShell script block logging: Event ID 4104
- Service installs: Event ID 7045
- Recently downloaded files
- Mounted drives & network shares

### Guidance & Remediation Engine
- Every failed check gets: What / Risk / Fix / Reference
- Color-coded: Red (critical), Yellow (warning), Green (pass)
- CIS Benchmark references where applicable
- Fix commands provided as PowerShell one-liners

---

## Command Mapping: macOS → Windows

| macOS | Windows (PowerShell) | Windows (CMD) |
|---|---|---|
| `system_profiler` | `Get-CimInstance` | `systeminfo` |
| `defaults read/write` | `Get-/Set-ItemProperty` | `reg query/add` |
| `lsof -i` | `Get-NetTCPConnection` | `netstat -ano` |
| `security find-certificate` | `Get-ChildItem Cert:\` | `certutil -store` |
| `csrutil status` | `Confirm-SecureBootUEFI` | `bcdedit` |
| `dscl . list /Users` | `Get-LocalUser` | `net user` |
| `socketfilterfw` | `Get-NetFirewallProfile` | `netsh advfirewall` |
| `launchctl` / `cron` | `Get-ScheduledTask` | `schtasks` |
| `codesign -v` | `Get-AuthenticodeSignature` | `signtool verify` |
| `diskutil` | `Get-Volume` | `diskpart` |
| `pmset` | `powercfg` | `powercfg` |
| `scutil` | `Get-DnsClientServerAddress` | `ipconfig /all` |

---

## Build Priority
1. Python version first (`windna.py`) — capture + deploy + menu
2. Security audit module in Python
3. HTML report generator
4. PowerShell version (`windna.ps1`) — full parity port
5. Testing across x64, x86, ARM
6. Push to GitHub

---

## Notes
- PowerShell version requires no external dependencies — runs on any Windows 10/11 box
- Python version requires Python 3.8+ (available via winget/Microsoft Store)
- Both versions share the same `profiles/` directory and `settings.json`
- Architecture detection: `[System.Environment]::Is64BitOperatingSystem`, `$env:PROCESSOR_ARCHITECTURE`
- ARM detection: `PROCESSOR_ARCHITECTURE -eq "ARM64"`

---

*Saved: 2026-03-17 | Project: WinDNA | Author: cyberspartan77*
