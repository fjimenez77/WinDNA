```
   ╭─╮  ██╗    ██╗██╗███╗   ██╗██████╗ ███╗   ██╗ █████╗
   │╳│  ██║    ██║██║████╗  ██║██╔══██╗████╗  ██║██╔══██╗
   ╰╮╯  ██║ █╗ ██║██║██╔██╗ ██║██║  ██║██╔██╗ ██║███████║
   ╭╯╮  ██║███╗██║██║██║╚██╗██║██║  ██║██║╚██╗██║██╔══██║
   │╳│  ╚███╔███╔╝██║██║ ╚████║██████╔╝██║ ╚████║██║  ██║
   ╰─╯   ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🧬  Capture · Deploy · Clone Your PC
    v1.0  ━━  cyberspartan77  ━━  2026
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Capture your PC's complete configuration DNA and deploy it to any new Windows machine.**

WinDNA scans your current Windows PC — preferences, apps, taskbar layout, explorer settings, security posture, network config — and saves everything into a portable profile. Take that profile to a brand new PC, deploy it, and your setup is restored.

Ships in **two formats**: Python and PowerShell. Pick whichever you prefer.

No external dependencies. Runs on any Windows 10/11 machine.

---

## How to Run

### Option A: Python Version

**Requirements:** Python 3.8+ — install via `winget install Python.Python.3` or [python.org](https://python.org)

```powershell
# 1. Clone the repo
git clone https://github.com/fjimenez77/WinDNA.git
cd WinDNA

# 2. Run the app
python windna.py

# 3. For full security audit (recommended)
# Right-click Terminal → Run as Administrator, then:
python windna.py
# Select option 6 from the menu
```

### Option B: PowerShell Version (zero-install — nothing to download)

**Requirements:** PowerShell 5.1+ (already built into every Windows 10/11 machine)

```powershell
# 1. Clone the repo
git clone https://github.com/fjimenez77/WinDNA.git
cd WinDNA

# 2. Run the app
powershell -ExecutionPolicy Bypass -File windna.ps1

# 3. For full security audit (recommended)
# Right-click Terminal → Run as Administrator, then:
powershell -ExecutionPolicy Bypass -File windna.ps1
# Select option 6 from the menu
```

### What You'll See

Both versions present the same interactive menu:

```
╔══════════════════════════════════════════════╗
║        🧬  W i n D N A   v 1                ║
║   Capture  -  Deploy  -  Clone Your PC       ║
╠══════════════════════════════════════════════╣
║  Author: cyberspartan77  |  v1.0  |  2026    ║
╚══════════════════════════════════════════════╝

─── MAIN MENU ────────────────────────────────

  1  📸  Capture This PC
  2  🚀  Deploy to This PC
  3  📄  View Profile
  4  🔀  Compare Profiles
  5  🗑️  Delete Profile
  6  🛡️  Security & Asset Audit
  7  ⚙️  Settings
  8  ❌  Exit WinDNA
```

### Quick Usage Guide

| What you want to do | Steps |
|---------------------|-------|
| **Backup your PC settings** | Run app → pick `1` → select categories → done. JSON + HTML saved to `profiles/` |
| **Restore settings on a new PC** | Copy the `profiles/` folder to the new PC → run app → pick `2` → select a profile → confirm |
| **Run a security audit** | Run as Admin → pick `6` → audit runs all 8 sections → JSON + HTML saved |
| **Compare two PCs** | Capture both → copy profiles to one machine → pick `4` → select two profiles |
| **Change settings** | Pick `7` → toggle any of the 11 configurable options |

### Admin vs Non-Admin

| Feature | Without Admin | With Admin |
|---------|--------------|------------|
| Capture settings | ✅ Full | ✅ Full |
| Deploy settings | ✅ Full | ✅ Full |
| Security audit — asset intel | ✅ Full | ✅ Full |
| Security audit — compliance | ⚠️ Partial (BitLocker, Defender limited) | ✅ Full |
| Security audit — event logs | ⚠️ Limited (access denied) | ✅ Full |
| Security audit — threats | ✅ Full | ✅ Full |

## Two Versions, Full Parity

| | `windna.py` | `windna.ps1` |
|---|---|---|
| **Runtime** | Python 3.8+ | PowerShell 5.1+ (built into Windows) |
| **Best for** | Cross-platform teams, devs with Python | Sysadmins, zero-install, GPO deployment |
| **Dependencies** | Python stdlib only | None — runs on any Windows box |
| **Features** | Full | Full |

## Architecture Support

WinDNA auto-detects and supports:
- **x64** — Standard Intel/AMD 64-bit
- **x86** — Legacy 32-bit systems
- **ARM64** — Surface Pro X, Snapdragon laptops, Windows on ARM

## What It Captures

| Category | What's Grabbed |
|----------|---------------|
| **Machine Identity** | Hostname, Windows version/build, architecture, domain, serial |
| **Desktop & Appearance** | Wallpaper, theme (light/dark), accent color, DPI scaling |
| **Taskbar & Start Menu** | Alignment, size, auto-hide, system tray icons |
| **File Explorer** | Hidden files, file extensions, compact view, recent files, launch location |
| **Mouse & Keyboard** | Mouse speed, scroll lines, button swap, key repeat rate/delay |
| **Sound & Notifications** | Sound scheme, notification settings, focus assist |
| **Power & Sleep** | Active power plan, sleep/hibernate timeouts, lid close action |
| **Network** | Saved Wi-Fi profiles, DNS servers, proxy settings |
| **Privacy & Security** | Location, camera, microphone permission states |
| **Installed Apps** | Windows Store apps, traditional programs, winget packages |

## Output

Each capture creates a folder with two files:

```
profiles\
  MyPC_2026-03-17\
    profile.json    ← machine-readable, used for deploy
    profile.html    ← interactive browser viewer
```

### HTML Viewer
Dark-themed, searchable, expandable viewer — open in any browser, no server needed:
- Stats dashboard (app counts, Wi-Fi profiles, settings captured)
- Collapsible sections for every category
- Color-coded tags for apps, store packages, Wi-Fi networks
- Full raw JSON toggle
- Search bar to find any setting

## Security & Asset Audit

Run as Administrator for full results.

A comprehensive security assessment covering 8 audit domains with 60+ checks:

| Section | What's Scanned |
|---------|---------------|
| **Asset Intelligence** | CPU, RAM, GPU, storage volumes, battery, USB/Bluetooth devices, BIOS, serial |
| **User Accounts & Access** | Local users, admin group, RDP users, scheduled tasks (persistence) |
| **Certificates** | Machine & user certs, expiry dates, self-signed detection, 30/60/90-day warnings |
| **Network & Connections** | Listening ports, established connections, UDP, adapters, VPN, routes, SMB shares, firewall profiles |
| **Domain & Management** | Active Directory, Azure AD, MDM/Intune enrollment, Group Policy |
| **Threat Detection & IOCs** | Reverse shells, suspicious processes, unsigned binaries, crypto miners, malware names, scheduled task persistence, browser extensions, env variable anomalies, recently modified system files, PowerShell history |
| **Compliance Posture** | BitLocker, Defender, Firewall, UAC, Secure Boot, SMBv1, RDP, Guest account, password policy, audit policy, Credential Guard, auto-updates |
| **Logs & Forensics** | Failed/successful logins, privilege escalation, RDP sessions, PowerShell script blocks, service installs, recent downloads |

### Guidance & Remediation Engine

Every failed check or threat finding includes actionable remediation:

- **What** — plain English description of the issue
- **Risk** — why it matters to your security posture
- **Fix** — the exact PowerShell command to remediate
- **Settings Path** — where to fix it in Windows Settings UI
- **CIS Reference** — CIS Benchmark ID where applicable

Findings are color-coded: 🔴 Critical | 🟡 Warning | 🟢 Pass

### Audit Output

```
profiles\
  MyPC_2026-03-17\
    profile.json    ← system capture
    profile.html    ← system capture viewer
    audit.json      ← security audit data
    audit.html      ← security audit viewer with guidance
```

## Deploy

Pick a saved profile → select which categories to apply → dry-run or live.

- **Dry Run** — previews every registry change, touches nothing
- **Apply** — writes settings via `reg add` / `Set-ItemProperty`, applies power plans, restores Wi-Fi profiles
- **Auto-backup** — current values backed up to `~\.windna_backup\` before overwrite
- **Idempotent** — skips settings that already match
- **Confirmation** — requires typing `YES` before any changes

## Settings

Configurable via the in-app Settings menu (option 7):

| Setting | Default |
|---------|---------|
| Profile save location | `.\profiles\` |
| Backup directory | `~\.windna_backup\` |
| Auto-backup before deploy | ON |
| Dry-run by default | OFF |
| Confirm before apply | ON |
| Auto-name profiles | OFF |
| Compact JSON | OFF |
| Color output | ON |
| Default capture categories | All |
| Security audit with capture | OFF |
| Threat alert level | medium |

Settings persist in `settings.json`.

## Security

- **Never captures** passwords, tokens, credentials, or encryption keys
- **Profiles stay local** — .gitignore excludes them from version control
- **Capture is read-only** — safe to run anytime
- **Deploy is cautious** — confirmation required, dry-run available
- **Admin not required** — runs without elevation, degrades gracefully for admin-only checks

## Requirements

- Windows 10 or Windows 11
- **Python version**: Python 3.8+ (available via winget: `winget install Python.Python.3`)
- **PowerShell version**: PowerShell 5.1+ (built into Windows)
- x64, x86, or ARM64 architecture
- Optional: Run as Administrator for full security audit

## Project Structure

```
WinDNA/
├── windna.py              # Python version (interactive menu)
├── windna.ps1             # PowerShell version (interactive menu, all-in-one)
├── securityaudit_win.py   # Security audit engine (imported by windna.py)
├── profiles/              # Saved captures and audits
├── LICENSE
└── README.md
```

## Related Projects

- **[MacDNA](https://github.com/fjimenez77/MacDNA)** — macOS counterpart

---

## Keywords

Windows system backup, PC settings capture, Windows migration tool, deploy Windows preferences, clone PC setup, Windows configuration DNA, registry backup, Windows security audit, BitLocker audit, Defender compliance check, CIS benchmark Windows, Windows forensic snapshot, PowerShell system tool, winget backup, Windows IT admin tool, Active Directory audit, Group Policy audit, Windows compliance checker, STIG compliance, endpoint security assessment

## Contributing

Pull requests, bug reports, and feature suggestions are welcome.

Quick version:

```powershell
# 1. Fork the repo on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/WinDNA.git
cd WinDNA

# 3. Create a feature branch
git checkout -b feature/your-idea

# 4. Make changes, test locally
python windna.py
python -m py_compile windna.py

# Or test the PowerShell version:
powershell -ExecutionPolicy Bypass -File windna.ps1

# 5. Commit + push + open a PR
git commit -m "Add: your change"
git push origin feature/your-idea
```

Before opening a PR:

- Open an issue first for non-trivial changes
- Keep PRs focused (one logical change per PR)
- Test the affected functionality manually
- No new external dependencies without discussion
- No real credentials, registry exports, or PII in commits

Reporting bugs? Include Windows version, Python version, architecture (x64/x86/ARM64), and reproduction steps.

Found a security issue? Don't open a public issue — use [GitHub Security Advisories](https://github.com/fjimenez77/WinDNA/security/advisories) instead.

## Contributors

- [@fjimenez77](https://github.com/fjimenez77) (Felix J.)
- [@canadayb](https://github.com/canadayb) (Brian Canaday)
- [@DevForgeAtlas](https://github.com/DevForgeAtlas)

## License

Apache License 2.0 — see [LICENSE](LICENSE) for full text.

Copyright 2026 Felix J. ([@fjimenez77](https://github.com/fjimenez77)) and contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
