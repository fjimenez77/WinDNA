#Requires -Version 5.1
<#
.SYNOPSIS
    WinDNA v1 - Capture, Deploy, Clone Your Windows PC
.DESCRIPTION
    A self-contained interactive menu-driven PowerShell script that captures
    your Windows PC's full configuration DNA and deploys it to any new machine.
    No external dependencies. Works on Windows 10/11 with PowerShell 5.1+.
.AUTHOR
    cyberspartan77
.VERSION
    1.0
.DATE
    March 2026
.NOTES
    Just run: .\windna.ps1
    Or: powershell -ExecutionPolicy Bypass -File windna.ps1
#>

# ═══════════════════════════════════════════════
#  STRICT MODE & ENCODING
# ═══════════════════════════════════════════════
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ═══════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════
$script:APP_DIR = $PSScriptRoot
if (-not $script:APP_DIR) { $script:APP_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $script:APP_DIR) { $script:APP_DIR = (Get-Location).Path }
$script:PROFILES_DIR = Join-Path $script:APP_DIR "profiles"
$script:SETTINGS_FILE = Join-Path $script:APP_DIR "settings.json"

# ═══════════════════════════════════════════════
#  ARCHITECTURE DETECTION
# ═══════════════════════════════════════════════
function Get-CPUArchitecture {
    $archEnv = $env:PROCESSOR_ARCHITECTURE
    $archW64 = $env:PROCESSOR_ARCHITEW6432
    if ($archEnv -match 'ARM' -or $archW64 -match 'ARM') {
        return "ARM64"
    }
    elseif ($archEnv -match 'AMD64' -or $archW64 -match 'AMD64') {
        return "x64"
    }
    else {
        return "x86"
    }
}

$script:ARCH = Get-CPUArchitecture
$script:Is64Bit = [System.Environment]::Is64BitOperatingSystem

# ═══════════════════════════════════════════════
#  ADMIN CHECK
# ═══════════════════════════════════════════════
function Test-IsAdmin {
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch { return $false }
}

$script:IsAdmin = Test-IsAdmin

# ═══════════════════════════════════════════════
#  TERMINAL UI HELPERS
# ═══════════════════════════════════════════════
function Write-Banner {
    $w = 46
    $top    = "  " + [char]0x2554 + ([string][char]0x2550 * $w) + [char]0x2557
    $mid    = "  " + [char]0x2560 + ([string][char]0x2550 * $w) + [char]0x2563
    $bottom = "  " + [char]0x255A + ([string][char]0x2550 * $w) + [char]0x255D

    $l1 = [char]0x1F9EC + "  W i n D N A   v 1"
    $l2 = "Capture  -  Deploy  -  Clone Your PC"
    $l3 = "Author: cyberspartan77  |  v1.0  |  2026"

    $line1 = "  " + [char]0x2551 + $l1.PadLeft(($w + $l1.Length) / 2).PadRight($w) + [char]0x2551
    $line2 = "  " + [char]0x2551 + $l2.PadLeft(($w + $l2.Length) / 2).PadRight($w) + [char]0x2551
    $line3 = "  " + [char]0x2551 + $l3.PadLeft(($w + $l3.Length) / 2).PadRight($w) + [char]0x2551

    Write-Host ""
    Write-Host $top -ForegroundColor Cyan
    Write-Host $line1 -ForegroundColor Cyan
    Write-Host $line2 -ForegroundColor Cyan
    Write-Host $mid -ForegroundColor Cyan
    Write-Host $line3 -ForegroundColor Cyan
    Write-Host $bottom -ForegroundColor Cyan
    Write-Host ""
}

function Write-Divider {
    param([string]$Title = "")
    $dash = [char]0x2500
    if ($Title) {
        $trail = [string]$dash * (40 - $Title.Length)
        Write-Host ""
        Write-Host "  $($dash)$($dash)$($dash) " -ForegroundColor Cyan -NoNewline
        Write-Host $Title -ForegroundColor White -NoNewline
        Write-Host " $trail" -ForegroundColor Cyan
    }
    else {
        Write-Host "  $([string]$dash * 48)" -ForegroundColor DarkGray
    }
}

function Write-Status {
    param(
        [string]$Icon,
        [ConsoleColor]$IconColor,
        [string]$Message,
        [string]$Detail = ""
    )
    Write-Host "  $Icon" -ForegroundColor $IconColor -NoNewline
    Write-Host "  $Message" -NoNewline
    if ($Detail) {
        Write-Host " $Detail" -ForegroundColor DarkGray
    }
    else {
        Write-Host ""
    }
}

function Write-Success {
    param([string]$Message, [string]$Detail = "")
    Write-Status ([char]0x2713) Green $Message $Detail
}

function Write-Fail {
    param([string]$Message, [string]$Detail = "")
    Write-Status ([char]0x2717) Red $Message $Detail
}

function Write-Warn {
    param([string]$Message, [string]$Detail = "")
    Write-Status "!" Yellow $Message $Detail
}

function Write-Info {
    param([string]$Message, [string]$Detail = "")
    Write-Status "i" Cyan $Message $Detail
}

function Write-SpinnerLine {
    param([string]$Message)
    Write-Host "`r  " -NoNewline
    Write-Host ([char]0x23F3) -ForegroundColor Yellow -NoNewline
    Write-Host " $Message..." -NoNewline
}

function Write-SpinnerDone {
    param([string]$Message)
    Write-Host "`r  " -NoNewline
    Write-Host ([char]0x2713) -ForegroundColor Green -NoNewline
    Write-Host "  $Message        "
}

function Write-SpinnerFail {
    param([string]$Message, [string]$Err = "")
    $e = if ($Err) { " - $Err" } else { "" }
    Write-Host "`r  " -NoNewline
    Write-Host ([char]0x2717) -ForegroundColor Red -NoNewline
    Write-Host "  $Message$e        "
}

function Read-Prompt {
    param([string]$Message, [string]$Default = "")
    $d = if ($Default) { " [$Default]" } else { "" }
    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host ">" -ForegroundColor Cyan -NoNewline
    Write-Host " $Message$d" -NoNewline
    Write-Host ": " -NoNewline
    try {
        $val = Read-Host
        $val = $val.Trim()
        if ($val -eq "" -and $Default) { return $Default }
        return $val
    }
    catch { return "" }
}

function Read-Pause {
    Write-Host ""
    Write-Host "  Press Enter to continue..." -ForegroundColor DarkGray -NoNewline
    try { $null = Read-Host } catch {}
}

function Clear-Screen {
    Clear-Host
}

function Show-Menu {
    param(
        [string]$Title,
        [array]$Options,
        [bool]$ShowBack = $true
    )
    Clear-Screen
    Write-Banner
    Write-Divider $Title
    Write-Host ""

    for ($i = 0; $i -lt $Options.Count; $i++) {
        $label = $Options[$i][0]
        $desc  = $Options[$i][1]
        $num   = $i + 1
        Write-Host "    " -NoNewline
        Write-Host "$num" -ForegroundColor Cyan -NoNewline
        Write-Host "  $label"
        if ($desc) {
            Write-Host "       $desc" -ForegroundColor DarkGray
        }
    }

    if ($ShowBack) {
        Write-Host ""
        Write-Host "    " -NoNewline
        Write-Host "0" -ForegroundColor Cyan -NoNewline
        Write-Host "  Back" -ForegroundColor DarkGray
    }
    Write-Host ""

    $choice = Read-Prompt "Choose an option"
    try {
        return [int]$choice
    }
    catch { return -1 }
}

function Show-Checklist {
    param(
        [string]$Title,
        [array]$Items,
        [bool]$PreselectAll = $true
    )
    # Items = array of @(key, label)
    if ($PreselectAll) {
        $selected = [System.Collections.Generic.HashSet[int]]::new()
        for ($i = 0; $i -lt $Items.Count; $i++) { $null = $selected.Add($i) }
    }
    else {
        $selected = [System.Collections.Generic.HashSet[int]]::new()
    }

    while ($true) {
        Clear-Screen
        Write-Banner
        Write-Divider $Title
        Write-Host "  Toggle items by number. Press A=all, N=none, Enter=confirm." -ForegroundColor DarkGray
        Write-Host ""

        for ($i = 0; $i -lt $Items.Count; $i++) {
            $key   = $Items[$i][0]
            $label = $Items[$i][1]
            if ($selected.Contains($i)) {
                Write-Host "    " -NoNewline
                Write-Host "[x]" -ForegroundColor Green -NoNewline
            }
            else {
                Write-Host "    " -NoNewline
                Write-Host "[ ]" -ForegroundColor DarkGray -NoNewline
            }
            $num = $i + 1
            Write-Host " " -NoNewline
            Write-Host "$num" -ForegroundColor White -NoNewline
            Write-Host "  $label"
        }

        Write-Host ""
        Write-Host "  Selected: $($selected.Count)/$($Items.Count)" -ForegroundColor DarkGray
        $choice = Read-Prompt "Toggle # / A=all / N=none / Enter=GO"

        if ($choice -eq "") { break }
        elseif ($choice.ToUpper() -eq "A") {
            $selected.Clear()
            for ($i = 0; $i -lt $Items.Count; $i++) { $null = $selected.Add($i) }
        }
        elseif ($choice.ToUpper() -eq "N") {
            $selected.Clear()
        }
        else {
            $nums = $choice -replace ',', ' ' -split '\s+' | Where-Object { $_ -match '^\d+$' }
            foreach ($n in $nums) {
                $idx = [int]$n - 1
                if ($idx -ge 0 -and $idx -lt $Items.Count) {
                    if ($selected.Contains($idx)) { $null = $selected.Remove($idx) }
                    else { $null = $selected.Add($idx) }
                }
            }
        }
    }

    $result = @()
    foreach ($i in ($selected | Sort-Object)) {
        $result += $Items[$i][0]
    }
    return $result
}

# ═══════════════════════════════════════════════
#  SETTINGS ENGINE
# ═══════════════════════════════════════════════
$script:DEFAULT_SETTINGS = [ordered]@{
    profile_save_location       = ""
    auto_backup_before_deploy   = $true
    dry_run_by_default          = $false
    compact_json                = $false
    color_output                = $true
    confirm_before_apply        = $true
    auto_name_profiles          = $false
    backup_directory            = ""
    default_capture_categories  = "all"
    security_audit_with_capture = $false
    threat_alert_level          = "medium"
}

function Get-AppSettings {
    $settings = [ordered]@{}
    foreach ($k in $script:DEFAULT_SETTINGS.Keys) {
        $settings[$k] = $script:DEFAULT_SETTINGS[$k]
    }
    if (Test-Path $script:SETTINGS_FILE) {
        try {
            $saved = Get-Content $script:SETTINGS_FILE -Raw | ConvertFrom-Json
            foreach ($prop in $saved.PSObject.Properties) {
                $settings[$prop.Name] = $prop.Value
            }
        }
        catch {}
    }
    return $settings
}

function Save-AppSettings {
    param([hashtable]$Settings)
    $Settings | ConvertTo-Json -Depth 10 | Set-Content -Path $script:SETTINGS_FILE -Encoding UTF8
}

function Get-ProfilesDir {
    param([hashtable]$Settings)
    $custom = ($Settings['profile_save_location']).ToString().Trim()
    if ($custom) { return $custom }
    return $script:PROFILES_DIR
}

function Get-BackupDir {
    param([hashtable]$Settings)
    $custom = ($Settings['backup_directory']).ToString().Trim()
    if ($custom) { return $custom }
    return Join-Path $env:USERPROFILE ".windna_backup"
}

# ═══════════════════════════════════════════════
#  REGISTRY HELPER
# ═══════════════════════════════════════════════
function Get-RegValue {
    param(
        [string]$Path,
        [string]$Name = $null
    )
    try {
        if ($Name) {
            $item = Get-ItemProperty -Path "Registry::$Path" -Name $Name -ErrorAction Stop
            return $item.$Name
        }
        else {
            $item = Get-ItemProperty -Path "Registry::$Path" -ErrorAction Stop
            return $item.'(default)'
        }
    }
    catch { return $null }
}

function Set-RegValue {
    param(
        [string]$Path,
        [string]$Name,
        [object]$Value,
        [string]$Type = "DWord"
    )
    try {
        $regPath = "Registry::$Path"
        if (-not (Test-Path $regPath)) {
            $null = New-Item -Path $regPath -Force
        }
        Set-ItemProperty -Path $regPath -Name $Name -Value $Value -Type $Type -Force -ErrorAction Stop
        return $true
    }
    catch { return $false }
}

# ═══════════════════════════════════════════════
#  CAPTURE MODULES
# ═══════════════════════════════════════════════

function Capture-MachineIdentity {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    $bios = Get-CimInstance Win32_BIOS -ErrorAction SilentlyContinue
    $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
    $totalRam = if ($cs.TotalPhysicalMemory) { [math]::Round($cs.TotalPhysicalMemory / 1GB, 1) } else { "N/A" }

    return [ordered]@{
        captured_at     = (Get-Date).ToString("o")
        hostname        = $env:COMPUTERNAME
        windows_edition = if ($os) { $os.Caption } else { "N/A" }
        windows_version = if ($os) { $os.Version } else { "N/A" }
        windows_build   = if ($os) { $os.BuildNumber } else { "N/A" }
        architecture    = $script:ARCH
        domain          = $env:USERDOMAIN
        dns_domain      = $env:USERDNSDOMAIN
        serial_number   = if ($bios) { $bios.SerialNumber } else { "N/A" }
        manufacturer    = if ($cs) { $cs.Manufacturer } else { "N/A" }
        model           = if ($cs) { $cs.Model } else { "N/A" }
        total_ram_gb    = $totalRam
        username        = $env:USERNAME
        ps_version      = $PSVersionTable.PSVersion.ToString()
    }
}

function Capture-DesktopAppearance {
    $desktopKey  = "HKCU\Control Panel\Desktop"
    $persKey     = "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    $dwmKey      = "HKCU\Software\Microsoft\Windows\DWM"
    $themeKey    = "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes"

    $wallpaper       = Get-RegValue $desktopKey "Wallpaper"
    $wallpaperStyle  = Get-RegValue $desktopKey "WallpaperStyle"
    $tileWallpaper   = Get-RegValue $desktopKey "TileWallpaper"
    $appsLight       = Get-RegValue $persKey "AppsUseLightTheme"
    $systemLight     = Get-RegValue $persKey "SystemUsesLightTheme"
    $colorPrev       = Get-RegValue $persKey "ColorPrevalence"
    $transparency    = Get-RegValue $persKey "EnableTransparency"
    $accentColor     = Get-RegValue $dwmKey "AccentColor"
    $colorization    = Get-RegValue $dwmKey "ColorizationColor"
    $dpi             = Get-RegValue $desktopKey "LogPixels"
    $dpiScaling      = Get-RegValue $desktopKey "Win8DpiScaling"
    $currentTheme    = Get-RegValue $themeKey "CurrentTheme"

    return [ordered]@{
        wallpaper              = $wallpaper
        wallpaper_style        = $wallpaperStyle
        tile_wallpaper         = $tileWallpaper
        dark_mode_apps         = if ($null -ne $appsLight) { $appsLight -eq 0 } else { $null }
        dark_mode_system       = if ($null -ne $systemLight) { $systemLight -eq 0 } else { $null }
        color_on_titlebar      = $colorPrev
        transparency_effects   = $transparency
        accent_color           = $accentColor
        colorization           = $colorization
        dpi                    = $dpi
        dpi_scaling            = $dpiScaling
        current_theme          = $currentTheme
    }
}

function Capture-TaskbarStart {
    $advKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    $searchKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Search"
    $explorerKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer"

    $taskbarAl      = Get-RegValue $advKey "TaskbarAl"
    $taskbarDa      = Get-RegValue $advKey "TaskbarDa"
    $taskbarMn      = Get-RegValue $advKey "TaskbarMn"
    $taskbarSi      = Get-RegValue $advKey "TaskbarSi"
    $showTaskView   = Get-RegValue $advKey "ShowTaskViewButton"
    $searchMode     = Get-RegValue $searchKey "SearchboxTaskbarMode"
    $showSeconds    = Get-RegValue $advKey "ShowSecondsInSystemClock"
    $autoTray       = Get-RegValue $explorerKey "EnableAutoTray"

    $alignment = switch ($taskbarAl) {
        0 { "left" }
        1 { "center" }
        default { $taskbarAl }
    }

    return [ordered]@{
        taskbar_alignment       = $alignment
        taskbar_size            = $taskbarSi
        taskbar_widgets         = $taskbarDa
        taskbar_chat            = $taskbarMn
        show_task_view          = $showTaskView
        search_mode             = $searchMode
        show_seconds_in_clock   = $showSeconds
        auto_hide_tray_icons    = $autoTray
    }
}

function Capture-FileExplorer {
    $advKey      = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    $explorerKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer"
    $ribbonKey   = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Ribbon"

    $hidden         = Get-RegValue $advKey "Hidden"
    $hideExt        = Get-RegValue $advKey "HideFileExt"
    $hideDrives     = Get-RegValue $advKey "HideDrivesWithNoMedia"
    $launchTo       = Get-RegValue $advKey "LaunchTo"
    $compactMode    = Get-RegValue $advKey "UseCompactMode"
    $sepProcess     = Get-RegValue $advKey "SeparateProcess"
    $fullPath       = Get-RegValue $advKey "FullPath"
    $statusBar      = Get-RegValue $advKey "ShowStatusBar"
    $showRecent     = Get-RegValue $explorerKey "ShowRecent"
    $showFrequent   = Get-RegValue $explorerKey "ShowFrequent"
    $ribbonMin      = Get-RegValue $ribbonKey "MinimizedStateTabletModeOff"

    $launchLabel = switch ($launchTo) {
        1 { "This PC" }
        2 { "Quick Access" }
        default { $launchTo }
    }

    return [ordered]@{
        show_hidden_files      = if ($null -ne $hidden) { $hidden -eq 1 } else { $null }
        show_file_extensions   = if ($null -ne $hideExt) { $hideExt -eq 0 } else { $null }
        hide_drives_no_media   = $hideDrives
        launch_to              = $launchLabel
        use_compact_mode       = $compactMode
        separate_process       = $sepProcess
        show_full_path         = $fullPath
        show_status_bar        = $statusBar
        show_recent_files      = $showRecent
        show_frequent_folders  = $showFrequent
        ribbon_minimized       = $ribbonMin
    }
}

function Capture-MouseKeyboard {
    $mouseKey    = "HKCU\Control Panel\Mouse"
    $kbKey       = "HKCU\Control Panel\Keyboard"
    $desktopKey  = "HKCU\Control Panel\Desktop"

    return [ordered]@{
        mouse = [ordered]@{
            speed              = Get-RegValue $mouseKey "MouseSpeed"
            threshold1         = Get-RegValue $mouseKey "MouseThreshold1"
            threshold2         = Get-RegValue $mouseKey "MouseThreshold2"
            sensitivity        = Get-RegValue $mouseKey "MouseSensitivity"
            swap_buttons       = (Get-RegValue $mouseKey "SwapMouseButtons") -eq "1"
            scroll_lines       = Get-RegValue $desktopKey "WheelScrollLines"
            double_click_speed = Get-RegValue $mouseKey "DoubleClickSpeed"
        }
        keyboard = [ordered]@{
            repeat_speed       = Get-RegValue $kbKey "KeyboardSpeed"
            repeat_delay       = Get-RegValue $kbKey "KeyboardDelay"
            cursor_blink_rate  = Get-RegValue $desktopKey "CursorBlinkRate"
        }
    }
}

function Capture-SoundNotifications {
    $schemePath = "HKCU\AppEvents\Schemes"
    $pushKey    = "HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications"
    $notifKey   = "HKCU\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"

    $soundScheme  = Get-RegValue $schemePath
    $toastEnabled = Get-RegValue $pushKey "ToastEnabled"
    $soundOnNotif = Get-RegValue $notifKey "NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND"

    return [ordered]@{
        sound_scheme           = $soundScheme
        focus_assist           = "not configured"
        notifications_enabled  = $toastEnabled
        notification_sounds    = $soundOnNotif
    }
}

function Capture-PowerSleep {
    # Active power plan
    $planName = ""
    $planGuid = ""
    $allPlans = @()

    try {
        $activeRaw = & powercfg /getactivescheme 2>$null
        if ($activeRaw -match 'GUID:\s*(\S+)\s*\((.+?)\)') {
            $planGuid = $Matches[1]
            $planName = $Matches[2]
        }
    } catch {}

    try {
        $listRaw = & powercfg /list 2>$null
        foreach ($line in $listRaw) {
            if ($line -match 'GUID:\s*(\S+)\s*\((.+?)\)') {
                $allPlans += [ordered]@{
                    guid   = $Matches[1]
                    name   = $Matches[2]
                    active = $line -match '\*'
                }
            }
        }
    } catch {}

    # Hibernate
    $hibEnabled = Get-RegValue "HKLM\SYSTEM\CurrentControlSet\Control\Power" "HibernateEnabled"

    # Sleep/screen timeouts via powercfg
    $sleepAc = ""; $sleepDc = ""; $screenAc = ""; $screenDc = ""
    $lidAc = ""; $lidDc = ""
    try {
        $sleepQuery = & powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 2>$null
        foreach ($l in $sleepQuery) {
            if ($l -match 'Current AC.*?:\s*(.+)') { $sleepAc = $Matches[1].Trim() }
            if ($l -match 'Current DC.*?:\s*(.+)') { $sleepDc = $Matches[1].Trim() }
        }
        $screenQuery = & powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE 2>$null
        foreach ($l in $screenQuery) {
            if ($l -match 'Current AC.*?:\s*(.+)') { $screenAc = $Matches[1].Trim() }
            if ($l -match 'Current DC.*?:\s*(.+)') { $screenDc = $Matches[1].Trim() }
        }
        $lidQuery = & powercfg /query SCHEME_CURRENT SUB_BUTTONS LIDACTION 2>$null
        foreach ($l in $lidQuery) {
            if ($l -match 'Current AC.*?:\s*(.+)') { $lidAc = $Matches[1].Trim() }
            if ($l -match 'Current DC.*?:\s*(.+)') { $lidDc = $Matches[1].Trim() }
        }
    } catch {}

    return [ordered]@{
        active_plan      = $planName
        active_plan_guid = $planGuid
        all_plans        = $allPlans
        hibernate_enabled = if ($null -ne $hibEnabled) { $hibEnabled -eq 1 } else { $null }
        sleep_timeout_ac  = $sleepAc
        sleep_timeout_dc  = $sleepDc
        screen_timeout_ac = $screenAc
        screen_timeout_dc = $screenDc
        lid_close_ac      = $lidAc
        lid_close_dc      = $lidDc
    }
}

function Capture-Network {
    # Wi-Fi profiles
    $wifiProfiles = @()
    try {
        $profilesRaw = & netsh wlan show profiles 2>$null
        foreach ($line in $profilesRaw) {
            if ($line -match 'All User Profile\s*:\s*(.+)$') {
                $wifiProfiles += $Matches[1].Trim()
            }
        }
    } catch {}

    # Current Wi-Fi
    $currentWifi = ""
    try {
        $ifaceRaw = & netsh wlan show interfaces 2>$null
        foreach ($line in $ifaceRaw) {
            if ($line -match '^\s*SSID\s*:\s*(.+)$' -and $line -notmatch 'BSSID') {
                $currentWifi = $Matches[1].Trim()
                break
            }
        }
    } catch {}

    # DNS servers
    $dnsServers = @()
    try {
        $dnsEntries = Get-DnsClientServerAddress -ErrorAction SilentlyContinue |
                      Where-Object { $_.ServerAddresses } |
                      Select-Object -ExpandProperty ServerAddresses |
                      Sort-Object -Unique
        $dnsServers = @($dnsEntries)
    } catch {}

    # Proxy settings
    $inetKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    $proxyEnable   = Get-RegValue $inetKey "ProxyEnable"
    $proxyServer   = Get-RegValue $inetKey "ProxyServer"
    $proxyOverride = Get-RegValue $inetKey "ProxyOverride"

    # IP addresses
    $ipAddresses = @()
    try {
        $adapters = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
                    Where-Object { $_.IPAddress -ne '127.0.0.1' } |
                    Select-Object -ExpandProperty IPAddress
        $ipAddresses = @($adapters)
    } catch {}

    return [ordered]@{
        wifi_profiles  = $wifiProfiles
        current_wifi   = $currentWifi
        dns_servers    = $dnsServers
        proxy_enabled  = if ($null -ne $proxyEnable) { $proxyEnable -eq 1 } else { $false }
        proxy_server   = $proxyServer
        proxy_bypass   = $proxyOverride
        ip_addresses   = $ipAddresses
    }
}

function Capture-PrivacySecurity {
    $consentBase = "HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"
    $categories = [ordered]@{
        location      = "location"
        camera        = "webcam"
        microphone    = "microphone"
        notifications = "userNotificationListener"
        contacts      = "contacts"
        calendar      = "appointments"
        call_history  = "phoneCallHistory"
        email         = "email"
        documents     = "documentsLibrary"
        pictures      = "picturesLibrary"
        videos        = "videosLibrary"
        file_system   = "broadFileSystemAccess"
    }

    $permissions = [ordered]@{}
    foreach ($friendly in $categories.Keys) {
        $regName = $categories[$friendly]
        $val = Get-RegValue "$consentBase\$regName" "Value"
        $permissions[$friendly] = if ($val) { $val } else { "not configured" }
    }

    # Defender status
    $defenderData = [ordered]@{}
    try {
        $mpStatus = Get-MpComputerStatus -ErrorAction Stop
        $defenderData = [ordered]@{
            AntivirusEnabled              = $mpStatus.AntivirusEnabled
            RealTimeProtectionEnabled     = $mpStatus.RealTimeProtectionEnabled
            AntivirusSignatureLastUpdated = $mpStatus.AntivirusSignatureLastUpdated.ToString("o")
        }
    } catch {
        $defenderData = [ordered]@{ error = "Could not query Defender status" }
    }

    # Firewall
    $fwDomain = ""; $fwPrivate = ""; $fwPublic = ""
    try {
        $fwProfiles = Get-NetFirewallProfile -ErrorAction Stop
        foreach ($p in $fwProfiles) {
            switch ($p.Name) {
                "Domain"  { $fwDomain  = $p.Enabled.ToString() }
                "Private" { $fwPrivate = $p.Enabled.ToString() }
                "Public"  { $fwPublic  = $p.Enabled.ToString() }
            }
        }
    } catch {}

    # UAC level
    $uacLevel = Get-RegValue "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" "ConsentPromptBehaviorAdmin"

    return [ordered]@{
        permissions = $permissions
        defender    = $defenderData
        firewall    = [ordered]@{
            domain  = $fwDomain
            private = $fwPrivate
            public  = $fwPublic
        }
        uac_level   = $uacLevel
    }
}

function Capture-InstalledApps {
    # Store apps (AppX)
    $storeApps = @()
    try {
        $appxList = Get-AppxPackage -ErrorAction SilentlyContinue | Select-Object Name, Version
        foreach ($app in $appxList) {
            $storeApps += [ordered]@{
                name    = $app.Name
                version = $app.Version
            }
        }
    } catch {}

    # Traditional programs from registry
    $traditionalApps = @()
    $seen = @{}
    $regPaths = @(
        "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    )

    foreach ($regPath in $regPaths) {
        try {
            $items = Get-ChildItem "Registry::$regPath" -ErrorAction SilentlyContinue
            foreach ($item in $items) {
                try {
                    $props = Get-ItemProperty $item.PSPath -ErrorAction SilentlyContinue
                    $name = $props.DisplayName
                    if ($name -and -not $seen.ContainsKey($name)) {
                        $seen[$name] = $true
                        $traditionalApps += [ordered]@{
                            name      = $name
                            version   = $props.DisplayVersion
                            publisher = $props.Publisher
                        }
                    }
                } catch {}
            }
        } catch {}
    }
    $traditionalApps = $traditionalApps | Sort-Object { $_.name }

    # Winget list
    $wingetApps = @()
    try {
        $wingetPath = Get-Command winget -ErrorAction SilentlyContinue
        if ($wingetPath) {
            $wingetRaw = & winget list --disable-interactivity 2>$null
            $dataStarted = $false
            foreach ($line in $wingetRaw) {
                if ($line -match '---') { $dataStarted = $true; continue }
                if ($dataStarted -and $line.Trim()) {
                    $wingetApps += $line.Trim()
                    if ($wingetApps.Count -ge 100) { break }
                }
            }
        }
    } catch {}

    return [ordered]@{
        store_apps            = $storeApps
        traditional_apps      = $traditionalApps
        winget_list           = $wingetApps
        total_store_apps      = $storeApps.Count
        total_traditional_apps = $traditionalApps.Count
    }
}

# Capture module registry
$script:CAPTURE_MODULES = @(
    @("machine_identity",    "Machine Identity",       { Capture-MachineIdentity }),
    @("desktop_appearance",  "Desktop & Appearance",   { Capture-DesktopAppearance }),
    @("taskbar_start",       "Taskbar & Start Menu",   { Capture-TaskbarStart }),
    @("file_explorer",       "File Explorer",          { Capture-FileExplorer }),
    @("mouse_keyboard",      "Mouse & Keyboard",       { Capture-MouseKeyboard }),
    @("sound_notifications", "Sound & Notifications",  { Capture-SoundNotifications }),
    @("power_sleep",         "Power & Sleep",          { Capture-PowerSleep }),
    @("network",             "Network",                { Capture-Network }),
    @("privacy_security",    "Privacy & Security",     { Capture-PrivacySecurity }),
    @("installed_apps",      "Installed Apps",         { Capture-InstalledApps })
)

# ═══════════════════════════════════════════════
#  DEPLOY MODULES
# ═══════════════════════════════════════════════

function Deploy-DesktopAppearance {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()
    $actions = @()

    if ($Data['wallpaper']) {
        $actions += ,@("Wallpaper -> $($Data['wallpaper'])", "HKCU\Control Panel\Desktop", "Wallpaper", $Data['wallpaper'], "String")
    }
    if ($Data['wallpaper_style']) {
        $actions += ,@("Wallpaper Style -> $($Data['wallpaper_style'])", "HKCU\Control Panel\Desktop", "WallpaperStyle", $Data['wallpaper_style'], "String")
    }

    $darkApps = $Data['dark_mode_apps']
    if ($null -ne $darkApps) {
        $val = if ($darkApps) { 0 } else { 1 }
        $label = "Dark Mode (Apps) -> $(if ($darkApps) { 'ON' } else { 'OFF' })"
        $actions += ,@($label, "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme", $val, "DWord")
    }

    $darkSys = $Data['dark_mode_system']
    if ($null -ne $darkSys) {
        $val = if ($darkSys) { 0 } else { 1 }
        $label = "Dark Mode (System) -> $(if ($darkSys) { 'ON' } else { 'OFF' })"
        $actions += ,@($label, "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme", $val, "DWord")
    }

    if ($null -ne $Data['transparency_effects']) {
        $actions += ,@("Transparency -> $($Data['transparency_effects'])", "HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", $Data['transparency_effects'], "DWord")
    }

    foreach ($action in $actions) {
        $label = $action[0]; $key = $action[1]; $vname = $action[2]; $vdata = $action[3]; $rtype = $action[4]
        if ($DryRun) {
            Write-Info $label "[DRY RUN]"
        }
        else {
            $ok = Set-RegValue -Path $key -Name $vname -Value $vdata -Type $rtype
            if ($ok) { Write-Success $label } else { Write-Fail $label }
        }
        $results += $label
    }

    if (-not $DryRun -and $results.Count -gt 0) {
        try { & RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters ,1 ,True 2>$null } catch {}
        Write-Info "Desktop refreshed"
    }
    return $results
}

function Deploy-FileExplorer {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()
    $advKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    $actions = @()

    if ($null -ne $Data['show_hidden_files']) {
        $val = if ($Data['show_hidden_files']) { 1 } else { 2 }
        $label = "Show Hidden Files -> $(if ($Data['show_hidden_files']) { 'ON' } else { 'OFF' })"
        $actions += ,@($label, $advKey, "Hidden", $val, "DWord")
    }
    if ($null -ne $Data['show_file_extensions']) {
        $val = if ($Data['show_file_extensions']) { 0 } else { 1 }
        $label = "Show File Extensions -> $(if ($Data['show_file_extensions']) { 'ON' } else { 'OFF' })"
        $actions += ,@($label, $advKey, "HideFileExt", $val, "DWord")
    }
    if ($Data['launch_to']) {
        $val = if ($Data['launch_to'] -eq "This PC") { 1 } else { 2 }
        $actions += ,@("Open Explorer to -> $($Data['launch_to'])", $advKey, "LaunchTo", $val, "DWord")
    }
    if ($null -ne $Data['use_compact_mode']) {
        $actions += ,@("Compact Mode -> $($Data['use_compact_mode'])", $advKey, "UseCompactMode", $Data['use_compact_mode'], "DWord")
    }
    if ($null -ne $Data['show_status_bar']) {
        $actions += ,@("Status Bar -> $($Data['show_status_bar'])", $advKey, "ShowStatusBar", $Data['show_status_bar'], "DWord")
    }

    foreach ($action in $actions) {
        $label = $action[0]; $key = $action[1]; $vname = $action[2]; $vdata = $action[3]; $rtype = $action[4]
        if ($DryRun) {
            Write-Info $label "[DRY RUN]"
        }
        else {
            $ok = Set-RegValue -Path $key -Name $vname -Value $vdata -Type $rtype
            if ($ok) { Write-Success $label } else { Write-Fail $label }
        }
        $results += $label
    }

    if (-not $DryRun -and $results.Count -gt 0) {
        Write-Info "Restarting Explorer to apply changes..."
        try {
            Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
            Start-Process explorer.exe
        } catch {}
    }
    return $results
}

function Deploy-MouseKeyboard {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()
    $actions = @()

    $mouse    = $Data['mouse']
    $keyboard = $Data['keyboard']

    if ($mouse) {
        if ($mouse['sensitivity']) {
            $actions += ,@("Mouse Sensitivity -> $($mouse['sensitivity'])", "HKCU\Control Panel\Mouse", "MouseSensitivity", $mouse['sensitivity'], "String")
        }
        if ($mouse['speed']) {
            $actions += ,@("Mouse Speed -> $($mouse['speed'])", "HKCU\Control Panel\Mouse", "MouseSpeed", $mouse['speed'], "String")
        }
        if ($mouse['scroll_lines']) {
            $actions += ,@("Scroll Lines -> $($mouse['scroll_lines'])", "HKCU\Control Panel\Desktop", "WheelScrollLines", $mouse['scroll_lines'], "String")
        }
        if ($null -ne $mouse['swap_buttons']) {
            $val = if ($mouse['swap_buttons']) { "1" } else { "0" }
            $actions += ,@("Swap Mouse Buttons -> $(if ($mouse['swap_buttons']) { 'ON' } else { 'OFF' })", "HKCU\Control Panel\Mouse", "SwapMouseButtons", $val, "String")
        }
        if ($mouse['double_click_speed']) {
            $actions += ,@("Double Click Speed -> $($mouse['double_click_speed'])", "HKCU\Control Panel\Mouse", "DoubleClickSpeed", $mouse['double_click_speed'], "String")
        }
    }

    if ($keyboard) {
        if ($keyboard['repeat_speed']) {
            $actions += ,@("Key Repeat Speed -> $($keyboard['repeat_speed'])", "HKCU\Control Panel\Keyboard", "KeyboardSpeed", $keyboard['repeat_speed'], "String")
        }
        if ($keyboard['repeat_delay']) {
            $actions += ,@("Key Repeat Delay -> $($keyboard['repeat_delay'])", "HKCU\Control Panel\Keyboard", "KeyboardDelay", $keyboard['repeat_delay'], "String")
        }
        if ($keyboard['cursor_blink_rate']) {
            $actions += ,@("Cursor Blink Rate -> $($keyboard['cursor_blink_rate'])", "HKCU\Control Panel\Desktop", "CursorBlinkRate", $keyboard['cursor_blink_rate'], "String")
        }
    }

    foreach ($action in $actions) {
        $label = $action[0]; $key = $action[1]; $vname = $action[2]; $vdata = $action[3]; $rtype = $action[4]
        if ($DryRun) {
            Write-Info $label "[DRY RUN]"
        }
        else {
            $ok = Set-RegValue -Path $key -Name $vname -Value $vdata -Type $rtype
            if ($ok) { Write-Success $label } else { Write-Fail $label }
        }
        $results += $label
    }
    return $results
}

function Deploy-PowerSleep {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()

    $guid = $Data['active_plan_guid']
    $name = $Data['active_plan']
    if ($guid) {
        $label = "Set power plan -> $name ($guid)"
        if ($DryRun) { Write-Info $label "[DRY RUN]" }
        else {
            try { & powercfg /setactive $guid 2>$null } catch {}
            Write-Success $label
        }
        $results += $label
    }

    $hib = $Data['hibernate_enabled']
    if ($null -ne $hib) {
        $label = "Hibernate -> $(if ($hib) { 'ON' } else { 'OFF' })"
        if ($DryRun) { Write-Info $label "[DRY RUN]" }
        else {
            $hibVal = if ($hib) { "on" } else { "off" }
            try { & powercfg /hibernate $hibVal 2>$null } catch {}
            Write-Success $label
        }
        $results += $label
    }
    return $results
}

function Deploy-Network {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()
    $inetKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    $proxyEnabled = $Data['proxy_enabled']
    if ($null -ne $proxyEnabled) {
        $val = if ($proxyEnabled) { 1 } else { 0 }
        $label = "Proxy -> $(if ($proxyEnabled) { 'Enabled' } else { 'Disabled' })"
        if ($DryRun) { Write-Info $label "[DRY RUN]" }
        else {
            Set-RegValue -Path $inetKey -Name "ProxyEnable" -Value $val -Type "DWord"
            Write-Success $label
        }
        $results += $label
    }

    $proxyServer = $Data['proxy_server']
    if ($proxyServer) {
        $label = "Proxy Server -> $proxyServer"
        if ($DryRun) { Write-Info $label "[DRY RUN]" }
        else {
            Set-RegValue -Path $inetKey -Name "ProxyServer" -Value $proxyServer -Type "String"
            Write-Success $label
        }
        $results += $label
    }

    $dns = $Data['dns_servers']
    if ($dns -and $dns.Count -gt 0) {
        $label = "DNS Servers -> $($dns -join ', ')"
        if ($DryRun) { Write-Info $label "[DRY RUN]" }
        else {
            Write-Warn "DNS settings ($($dns -join ', ')) require admin privileges to change"
            Write-Warn "Run: Set-DnsClientServerAddress -InterfaceAlias 'Ethernet' -ServerAddresses @('$($dns -join "','")') to apply manually"
        }
        $results += $label
    }

    $wifi = $Data['wifi_profiles']
    if ($wifi -and $wifi.Count -gt 0) {
        Write-Warn "$($wifi.Count) Wi-Fi profiles captured (import via netsh wlan add profile)"
    }
    return $results
}

function Deploy-PrivacySecurity {
    param([hashtable]$Data, [bool]$DryRun = $false)
    $results = @()
    $consentBase = "HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"

    $regNameMap = @{
        location      = "location"
        camera        = "webcam"
        microphone    = "microphone"
        notifications = "userNotificationListener"
        contacts      = "contacts"
        calendar      = "appointments"
        call_history  = "phoneCallHistory"
        email         = "email"
        documents     = "documentsLibrary"
        pictures      = "picturesLibrary"
        videos        = "videosLibrary"
        file_system   = "broadFileSystemAccess"
    }

    $permissions = $Data['permissions']
    if ($permissions) {
        foreach ($friendly in $permissions.Keys) {
            $value = $permissions[$friendly]
            if ($value -and $value -ne "not configured") {
                $regName = $regNameMap[$friendly]
                if ($regName) {
                    $label = "$friendly -> $value"
                    if ($DryRun) { Write-Info $label "[DRY RUN]" }
                    else {
                        $ok = Set-RegValue -Path "$consentBase\$regName" -Name "Value" -Value $value -Type "String"
                        if ($ok) { Write-Success $label } else { Write-Fail $label }
                    }
                    $results += $label
                }
            }
        }
    }

    $fw = $Data['firewall']
    if ($fw) {
        Write-Warn "Firewall settings require admin privileges to change"
        foreach ($profile in $fw.Keys) {
            $val = $fw[$profile]
            if ($val) { Write-Info "  Firewall ${profile}: $val" }
        }
    }
    return $results
}

# Deploy module registry
$script:DEPLOY_MODULES = @(
    @("desktop_appearance", "Desktop & Appearance",  { param($d,$r) Deploy-DesktopAppearance $d $r }),
    @("file_explorer",      "File Explorer",         { param($d,$r) Deploy-FileExplorer $d $r }),
    @("mouse_keyboard",     "Mouse & Keyboard",      { param($d,$r) Deploy-MouseKeyboard $d $r }),
    @("power_sleep",        "Power & Sleep",          { param($d,$r) Deploy-PowerSleep $d $r }),
    @("network",            "Network",               { param($d,$r) Deploy-Network $d $r }),
    @("privacy_security",   "Privacy & Security",    { param($d,$r) Deploy-PrivacySecurity $d $r })
)

# ═══════════════════════════════════════════════
#  HTML REPORT GENERATOR
# ═══════════════════════════════════════════════

function Format-HtmlValue {
    param([object]$Value)
    if ($Value -eq $true)  { return '<span class="val-true">true &#x2713;</span>' }
    if ($Value -eq $false) { return '<span class="val-false">false &#x2717;</span>' }
    if ($null -eq $Value -or $Value -eq "") { return '<span class="val-empty">(default)</span>' }
    if ($Value -is [int] -or $Value -is [double] -or $Value -is [long]) {
        return "<span class=`"val-number`">$Value</span>"
    }
    $s = [System.Web.HttpUtility]::HtmlEncode($Value.ToString())
    return "<span class=`"val-string`">$s</span>"
}

function Build-DataHtml {
    param([string]$Key, [object]$Data, [int]$Depth = 0)

    if ($Data -is [hashtable] -or $Data -is [System.Collections.Specialized.OrderedDictionary]) {
        $rows = ""
        foreach ($k in $Data.Keys) {
            $v = $Data[$k]
            # Special handling for installed_apps
            if ($Key -eq "installed_apps" -and $k -eq "traditional_apps" -and $v -is [array]) {
                $tags = ""
                $limit = [Math]::Min($v.Count, 80)
                for ($i = 0; $i -lt $limit; $i++) {
                    $appName = [System.Web.HttpUtility]::HtmlEncode($v[$i]['name'])
                    $appVer  = [System.Web.HttpUtility]::HtmlEncode($v[$i]['version'])
                    $tags += "<span class=`"item-tag app`">$appName ($appVer)</span>"
                }
                $extra = if ($v.Count -gt 80) { " (+$($v.Count - 80) more)" } else { "" }
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">Traditional Programs ($($v.Count))$extra</div><div class=`"item-list`">$tags</div></div>"
            }
            elseif ($Key -eq "installed_apps" -and $k -eq "store_apps" -and $v -is [array]) {
                $tags = ""
                $limit = [Math]::Min($v.Count, 60)
                for ($i = 0; $i -lt $limit; $i++) {
                    $appName = [System.Web.HttpUtility]::HtmlEncode($v[$i]['name'])
                    $tags += "<span class=`"item-tag store`">$appName</span>"
                }
                $extra = if ($v.Count -gt 60) { " (+$($v.Count - 60) more)" } else { "" }
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">Store Apps ($($v.Count))$extra</div><div class=`"item-list`">$tags</div></div>"
            }
            elseif ($Key -eq "installed_apps" -and $k -eq "winget_list" -and $v -is [array]) {
                if ($v.Count -gt 0) {
                    $limit = [Math]::Min($v.Count, 50)
                    $content = ($v[0..($limit-1)] | ForEach-Object { [System.Web.HttpUtility]::HtmlEncode($_) }) -join "`n"
                    $rows += "<div class=`"subsection`"><div class=`"subsection-title`">Winget List (first $limit)</div><div class=`"code-block`">$content</div></div>"
                }
            }
            elseif ($Key -eq "network" -and $k -eq "wifi_profiles" -and $v -is [array]) {
                $tags = ($v | ForEach-Object { "<span class=`"item-tag wifi`">$([System.Web.HttpUtility]::HtmlEncode($_))</span>" }) -join ""
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">Wi-Fi Profiles ($($v.Count))</div><div class=`"item-list`">$tags</div></div>"
            }
            elseif ($Key -eq "network" -and ($k -eq "dns_servers" -or $k -eq "ip_addresses") -and $v -is [array]) {
                $fk = ($k -replace '_', ' ').ToUpper()
                $tags = ($v | ForEach-Object { "<span class=`"item-tag`">$([System.Web.HttpUtility]::HtmlEncode($_))</span>" }) -join ""
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">$fk</div><div class=`"item-list`">$tags</div></div>"
            }
            elseif ($Key -eq "power_sleep" -and $k -eq "all_plans" -and $v -is [array]) {
                $tags = ""
                foreach ($plan in $v) {
                    $cls = if ($plan['active']) { "item-tag app" } else { "item-tag" }
                    $star = if ($plan['active']) { " *" } else { "" }
                    $tags += "<span class=`"$cls`">$([System.Web.HttpUtility]::HtmlEncode($plan['name']))$star</span>"
                }
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">Power Plans</div><div class=`"item-list`">$tags</div></div>"
            }
            elseif ($v -is [hashtable] -or $v -is [System.Collections.Specialized.OrderedDictionary]) {
                $subRows = ""
                foreach ($sk in $v.Keys) {
                    $sv = $v[$sk]
                    $subRows += "<tr><td>$sk</td><td>$(Format-HtmlValue $sv)</td></tr>"
                }
                $friendly = ($k -replace '_', ' ')
                $rows += "<div class=`"subsection`"><div class=`"subsection-title`">$friendly</div><table class=`"data-table`">$subRows</table></div>"
            }
            elseif ($v -is [array]) {
                if ($v.Count -gt 0) {
                    $tags = ($v | ForEach-Object { "<span class=`"item-tag`">$([System.Web.HttpUtility]::HtmlEncode($_.ToString()))</span>" }) -join ""
                    $friendly = ($k -replace '_', ' ')
                    $rows += "<div class=`"subsection`"><div class=`"subsection-title`">$friendly ($($v.Count))</div><div class=`"item-list`">$tags</div></div>"
                }
            }
            else {
                $rows += "<table class=`"data-table`"><tr><td>$k</td><td>$(Format-HtmlValue $v)</td></tr></table>"
            }
        }
        return $rows
    }
    elseif ($Data -is [array]) {
        $tags = ($Data | ForEach-Object { "<span class=`"item-tag`">$([System.Web.HttpUtility]::HtmlEncode($_.ToString()))</span>" }) -join ""
        return "<div class=`"item-list`">$tags</div>"
    }
    else {
        return "<p>$(Format-HtmlValue $Data)</p>"
    }
}

function Build-SectionCard {
    param([string]$Key, [string]$Icon, [string]$Title, [object]$Data)
    $badge = ""
    if ($Data -is [hashtable] -or $Data -is [System.Collections.Specialized.OrderedDictionary]) {
        $badge = "$($Data.Count) items"
    }
    elseif ($Data -is [array]) { $badge = "$($Data.Count) items" }

    $bodyHtml = Build-DataHtml -Key $Key -Data $Data
    return @"
  <div class="section" data-key="$Key">
    <div class="section-header">
      <div class="section-icon">$Icon</div>
      <div class="section-title">$Title</div>
      <div class="section-badge">$badge</div>
      <div class="section-arrow">&#x25b6;</div>
    </div>
    <div class="section-body">$bodyHtml</div>
  </div>
"@
}

function Generate-HtmlReport {
    param([hashtable]$Profile, [string]$FilePath)

    # Load System.Web for HtmlEncode
    try { Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue } catch {}

    $meta = $Profile['machine_identity']
    if (-not $meta) { $meta = @{} }
    $hostname   = if ($meta['hostname']) { $meta['hostname'] } else { "Unknown PC" }
    $captured   = if ($meta['captured_at']) { $meta['captured_at'] } else { "" }
    $winEdition = if ($meta['windows_edition']) { $meta['windows_edition'] } else { "" }
    $arch       = if ($meta['architecture']) { $meta['architecture'] } else { "" }
    $serial     = if ($meta['serial_number']) { $meta['serial_number'] } else { "N/A" }

    $sectionMap = [ordered]@{
        machine_identity    = @([char]0x1F4BB, "Machine Identity")
        desktop_appearance  = @("⚙️", "Desktop & Appearance")
        taskbar_start       = @([char]0x1F4CC, "Taskbar & Start Menu")
        file_explorer       = @([char]0x1F4C2, "File Explorer")
        mouse_keyboard      = @("⌨️", "Mouse & Keyboard")
        sound_notifications = @([char]0x1F50A, "Sound & Notifications")
        power_sleep         = @("⚡", "Power & Sleep")
        network             = @([char]0x1F310, "Network")
        privacy_security    = @([char]0x1F512, "Privacy & Security")
        installed_apps      = @([char]0x1F4E6, "Installed Apps")
    }

    $sectionOrder = @(
        "machine_identity", "desktop_appearance", "taskbar_start",
        "file_explorer", "mouse_keyboard", "sound_notifications",
        "power_sleep", "network", "privacy_security", "installed_apps"
    )

    $sectionCards = ""
    foreach ($key in $sectionOrder) {
        $data = $Profile[$key]
        if (-not $data) { continue }
        $mapEntry = $sectionMap[$key]
        $icon = $mapEntry[0]; $title = $mapEntry[1]
        $sectionCards += Build-SectionCard -Key $key -Icon $icon -Title $title -Data $data
    }

    # Stats
    $nStore = if ($Profile['installed_apps']) { ($Profile['installed_apps']['store_apps']).Count } else { 0 }
    $nTrad  = if ($Profile['installed_apps']) { ($Profile['installed_apps']['traditional_apps']).Count } else { 0 }
    $nWifi  = if ($Profile['network']) { ($Profile['network']['wifi_profiles']).Count } else { 0 }
    $darkApps = if ($Profile['desktop_appearance']) { $Profile['desktop_appearance']['dark_mode_apps'] } else { $false }
    $plan = if ($Profile['power_sleep']) { $Profile['power_sleep']['active_plan'] } else { "N/A" }

    $profileJsonRaw = $Profile | ConvertTo-Json -Depth 10 -Compress:$false
    $profileJsonEscaped = $profileJsonRaw.Replace('<','&lt;').Replace('>','&gt;')
    $capturedDate = if ($captured.Length -ge 10) { $captured.Substring(0, 10) } else { "N/A" }
    $darkModeLabel = if ($darkApps) { "Yes" } else { "No" }

    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧬 WinDNA - $hostname</title>
<style>
  :root {
    --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
    --dim: #8b949e; --cyan: #58a6ff; --green: #3fb950; --yellow: #d29922;
    --red: #f85149; --purple: #bc8cff;
    --font: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; }
  .header { background: linear-gradient(135deg, #161b22 0%, #1a2332 100%); border-bottom: 1px solid var(--border); padding: 2rem 2rem 1.5rem; text-align: center; }
  .header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
  .header h1 span { color: var(--cyan); }
  .header .subtitle { color: var(--dim); font-size: 0.95rem; }
  .header .meta-row { display: flex; justify-content: center; gap: 2rem; margin-top: 1rem; flex-wrap: wrap; }
  .header .meta-item { font-size: 0.85rem; color: var(--dim); }
  .header .meta-item strong { color: var(--text); }
  .stats { display: flex; justify-content: center; gap: 1.5rem; padding: 1rem 2rem; background: var(--card); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  .stat { text-align: center; min-width: 80px; }
  .stat .num { font-size: 1.5rem; font-weight: 700; color: var(--cyan); }
  .stat .label { font-size: 0.75rem; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; }
  .search-bar { padding: 1rem 2rem; background: var(--bg); position: sticky; top: 0; z-index: 10; border-bottom: 1px solid var(--border); }
  .search-bar input { width: 100%; max-width: 500px; display: block; margin: 0 auto; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border); background: var(--card); color: var(--text); font-size: 0.95rem; outline: none; }
  .search-bar input:focus { border-color: var(--cyan); box-shadow: 0 0 0 2px rgba(88,166,255,0.2); }
  .container { max-width: 900px; margin: 0 auto; padding: 1.5rem; }
  .section { background: var(--card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 1rem; overflow: hidden; transition: border-color 0.2s; }
  .section:hover { border-color: var(--cyan); }
  .section-header { display: flex; align-items: center; padding: 0.9rem 1.2rem; cursor: pointer; user-select: none; gap: 0.75rem; }
  .section-header:hover { background: rgba(88,166,255,0.05); }
  .section-icon { font-size: 1.3rem; width: 2rem; text-align: center; }
  .section-title { font-weight: 600; font-size: 1rem; flex: 1; }
  .section-badge { font-size: 0.75rem; padding: 0.15rem 0.6rem; border-radius: 10px; background: rgba(88,166,255,0.15); color: var(--cyan); }
  .section-arrow { color: var(--dim); transition: transform 0.2s; font-size: 0.8rem; }
  .section.open .section-arrow { transform: rotate(90deg); }
  .section-body { display: none; padding: 0 1.2rem 1.2rem; border-top: 1px solid var(--border); }
  .section.open .section-body { display: block; padding-top: 1rem; }
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table tr { border-bottom: 1px solid rgba(48,54,61,0.5); }
  .data-table tr:last-child { border-bottom: none; }
  .data-table td { padding: 0.45rem 0; vertical-align: top; }
  .data-table td:first-child { color: var(--dim); font-size: 0.85rem; width: 40%; padding-right: 1rem; }
  .data-table td:last-child { font-family: var(--mono); font-size: 0.85rem; word-break: break-word; }
  .val-true { color: var(--green); } .val-false { color: var(--red); }
  .val-empty { color: var(--dim); font-style: italic; }
  .val-string { color: var(--text); } .val-number { color: var(--purple); }
  .item-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.3rem; }
  .item-tag { font-size: 0.8rem; padding: 0.2rem 0.6rem; border-radius: 6px; background: rgba(88,166,255,0.1); color: var(--cyan); font-family: var(--mono); border: 1px solid rgba(88,166,255,0.15); }
  .item-tag.app { background: rgba(63,185,80,0.1); color: var(--green); border-color: rgba(63,185,80,0.15); }
  .item-tag.store { background: rgba(188,140,255,0.1); color: var(--purple); border-color: rgba(188,140,255,0.15); }
  .item-tag.wifi { background: rgba(210,153,34,0.1); color: var(--yellow); border-color: rgba(210,153,34,0.15); }
  .subsection { margin-top: 1rem; }
  .subsection-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--dim); margin-bottom: 0.5rem; font-weight: 600; }
  .code-block { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem; font-family: var(--mono); font-size: 0.8rem; line-height: 1.5; overflow-x: auto; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto; }
  .footer { text-align: center; padding: 2rem; color: var(--dim); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 2rem; }
  .raw-toggle { text-align: center; margin: 1.5rem 0; }
  .raw-toggle button { background: var(--card); border: 1px solid var(--border); color: var(--dim); padding: 0.5rem 1.5rem; border-radius: 8px; font-size: 0.85rem; cursor: pointer; transition: all 0.2s; }
  .raw-toggle button:hover { border-color: var(--cyan); color: var(--cyan); }
  .raw-json { display: none; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.2rem; margin-top: 1rem; max-height: 600px; overflow: auto; }
  .raw-json pre { font-family: var(--mono); font-size: 0.8rem; white-space: pre-wrap; word-break: break-all; }
  .hidden { display: none !important; }
</style>
</head>
<body>
<div class="header">
  <h1>🧬 <span>WinDNA</span> Profile</h1>
  <div class="subtitle">$hostname - captured $capturedDate</div>
  <div class="meta-row">
    <div class="meta-item">Windows <strong>$winEdition</strong></div>
    <div class="meta-item">Arch <strong>$arch</strong></div>
    <div class="meta-item">Dark Mode <strong>$darkModeLabel</strong></div>
    <div class="meta-item">Serial <strong>$serial</strong></div>
  </div>
</div>
<div class="stats">
  <div class="stat"><div class="num">$nTrad</div><div class="label">Programs</div></div>
  <div class="stat"><div class="num">$nStore</div><div class="label">Store Apps</div></div>
  <div class="stat"><div class="num">$nWifi</div><div class="label">Wi-Fi</div></div>
  <div class="stat"><div class="num">$plan</div><div class="label">Power Plan</div></div>
</div>
<div class="search-bar">
  <input type="text" id="search" placeholder="Search settings, apps, values..." autocomplete="off">
</div>
<div class="container">
$sectionCards
  <div class="raw-toggle"><button onclick="toggleRaw()">Show Raw JSON</button></div>
  <div class="raw-json" id="rawJson"><pre>$profileJsonEscaped</pre></div>
</div>
<div class="footer">🧬 WinDNA v1.0 - Author: cyberspartan77 - Generated $capturedDate</div>
<script>
document.querySelectorAll('.section-header').forEach(h => {
  h.addEventListener('click', () => { h.parentElement.classList.toggle('open'); });
});
document.getElementById('search').addEventListener('input', function() {
  const q = this.value.toLowerCase();
  document.querySelectorAll('.section').forEach(s => {
    if (!q) { s.classList.remove('hidden'); return; }
    const text = s.textContent.toLowerCase();
    if (text.includes(q)) { s.classList.remove('hidden'); s.classList.add('open'); }
    else { s.classList.add('hidden'); }
  });
});
function toggleRaw() {
  const el = document.getElementById('rawJson');
  el.style.display = el.style.display === 'block' ? 'none' : 'block';
}
document.querySelectorAll('.section').forEach(s => s.classList.add('open'));
</script>
</body>
</html>
"@

    $html | Out-File -FilePath $FilePath -Encoding UTF8
}

# ═══════════════════════════════════════════════
#  PROFILE HELPERS
# ═══════════════════════════════════════════════

function Get-ProfileDisplayName {
    param([string]$FilePath)
    $parent = Split-Path (Split-Path $FilePath -Parent) -Leaf
    $filename = Split-Path $FilePath -Leaf
    if ($filename -eq "profile.json") { return $parent }
    return $filename
}

function Get-SavedProfiles {
    $settings = Get-AppSettings
    $pdir = Get-ProfilesDir $settings
    if (-not (Test-Path $pdir)) { $null = New-Item -Path $pdir -ItemType Directory -Force }

    $folderProfiles = @()
    $flatProfiles = @()
    try {
        $folderProfiles = @(Get-ChildItem -Path $pdir -Recurse -Filter "profile.json" -ErrorAction SilentlyContinue |
                            Sort-Object LastWriteTime -Descending |
                            Select-Object -ExpandProperty FullName)
    } catch {}
    try {
        $flatProfiles = @(Get-ChildItem -Path $pdir -Filter "*.json" -ErrorAction SilentlyContinue |
                          Where-Object { $_.Name -ne "profile.json" } |
                          Sort-Object LastWriteTime -Descending |
                          Select-Object -ExpandProperty FullName)
    } catch {}

    return @($folderProfiles) + @($flatProfiles)
}

# ═══════════════════════════════════════════════
#  MENU FLOW: CAPTURE
# ═══════════════════════════════════════════════

function Invoke-FlowCapture {
    $settings = Get-AppSettings

    $defaultCats = $settings['default_capture_categories']
    $preselect = ($defaultCats -eq "all")

    $checklistItems = @()
    foreach ($mod in $script:CAPTURE_MODULES) {
        $checklistItems += ,@($mod[0], $mod[1])
    }

    $selectedKeys = Show-Checklist -Title "Select categories to capture" -Items $checklistItems -PreselectAll $preselect
    if (-not $selectedKeys -or $selectedKeys.Count -eq 0) {
        Write-Warn "Nothing selected"
        Read-Pause
        return
    }

    Clear-Screen
    Write-Banner
    Write-Divider "CAPTURING"
    Write-Host ""

    $profile = [ordered]@{}
    foreach ($mod in $script:CAPTURE_MODULES) {
        $key = $mod[0]; $label = $mod[1]; $func = $mod[2]
        if ($selectedKeys -notcontains $key) { continue }

        Write-SpinnerLine $label
        try {
            $profile[$key] = & $func
            Write-SpinnerDone $label
        }
        catch {
            $profile[$key] = [ordered]@{ error = $_.Exception.Message }
            Write-SpinnerFail $label $_.Exception.Message
        }
    }

    # Save - create folder per capture
    $pdir = Get-ProfilesDir $settings
    $hostClean = ($profile['machine_identity']['hostname'] -replace '[^\w\-]', '_')
    $dateStr = (Get-Date).ToString("yyyy-MM-dd")
    $folderName = "${hostClean}_${dateStr}"

    if (-not $settings['auto_name_profiles']) {
        Write-Host ""
        $folderName = Read-Prompt "Profile folder name" $folderName
    }

    $folderPath = Join-Path $pdir $folderName
    if (-not (Test-Path $folderPath)) { $null = New-Item -Path $folderPath -ItemType Directory -Force }

    # Write JSON
    $jsonPath = Join-Path $folderPath "profile.json"
    $indent = if ($settings['compact_json']) { $false } else { $true }
    if ($indent) {
        $profile | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
    }
    else {
        $profile | ConvertTo-Json -Depth 10 -Compress | Set-Content -Path $jsonPath -Encoding UTF8
    }

    # Write HTML
    Write-SpinnerLine "Generating HTML report"
    $htmlPath = Join-Path $folderPath "profile.html"
    Generate-HtmlReport -Profile $profile -FilePath $htmlPath
    Write-SpinnerDone "HTML report generated"

    Write-Host ""
    Write-Divider "CAPTURE COMPLETE"
    Write-Success "Folder: $folderPath"
    $jsonSize = [math]::Round((Get-Item $jsonPath).Length / 1KB, 1)
    $htmlSize = [math]::Round((Get-Item $htmlPath).Length / 1KB, 1)
    Write-Info "JSON:   $jsonSize KB"
    Write-Info "HTML:   $htmlSize KB"

    # Quick stats
    $trad  = $profile['installed_apps']['traditional_apps']
    $store = $profile['installed_apps']['store_apps']
    $wifi  = $profile['network']['wifi_profiles']
    if ($trad) { Write-Info "Traditional programs: $($trad.Count)" }
    if ($store) { Write-Info "Store apps: $($store.Count)" }
    if ($wifi) { Write-Info "Wi-Fi profiles: $($wifi.Count)" }

    # Auto security audit
    if ($settings['security_audit_with_capture']) {
        Write-Host ""
        Write-Divider "AUTO SECURITY AUDIT"
        $alertLevel = $settings['threat_alert_level']
        $auditData = Invoke-SecurityAudit -AlertLevel $alertLevel
        $auditJson = Join-Path $folderPath "audit.json"
        $auditHtml = Join-Path $folderPath "audit.html"
        $auditData | ConvertTo-Json -Depth 10 | Set-Content -Path $auditJson -Encoding UTF8
        Generate-AuditHtml -AuditData $auditData -FilePath $auditHtml
        Write-Success "Security audit saved alongside profile"
    }

    $openIt = Read-Prompt "Open HTML report in browser? (y/N)"
    if ($openIt -eq "y") {
        try { Start-Process $htmlPath } catch {}
    }
    Read-Pause
}

# ═══════════════════════════════════════════════
#  MENU FLOW: DEPLOY
# ═══════════════════════════════════════════════

function Invoke-FlowDeploy {
    $settings = Get-AppSettings
    $profiles = Get-SavedProfiles

    if ($profiles.Count -eq 0) {
        Clear-Screen
        Write-Banner
        Write-Warn "No saved profiles found."
        $pdir = Get-ProfilesDir $settings
        Write-Info "Capture a profile first, or place .json files in:`n       $pdir"
        Read-Pause
        return
    }

    # Pick a profile
    $options = @()
    foreach ($p in $profiles) {
        $name = Get-ProfileDisplayName $p
        $size = [math]::Round((Get-Item $p).Length / 1KB, 1)
        $mtime = (Get-Item $p).LastWriteTime.ToString("yyyy-MM-dd HH:mm")
        $options += ,@($name, "$size KB - $mtime")
    }

    $choice = Show-Menu -Title "DEPLOY - Select a Profile" -Options $options
    if ($choice -le 0 -or $choice -gt $profiles.Count) { return }

    $profilePath = $profiles[$choice - 1]
    $profile = Get-Content $profilePath -Raw | ConvertFrom-Json

    # Convert PSCustomObject to hashtable recursively
    $profileHash = ConvertTo-Hashtable $profile

    $hostname = $profileHash['machine_identity']['hostname']
    $captured = $profileHash['machine_identity']['captured_at']

    # Build checklist
    $available = @()
    foreach ($mod in $script:DEPLOY_MODULES) {
        $key = $mod[0]; $label = $mod[1]
        if ($profileHash[$key]) {
            $available += ,@($key, $label)
        }
    }

    if ($available.Count -eq 0) {
        Write-Warn "This profile has no deployable data"
        Read-Pause
        return
    }

    $selectedKeys = Show-Checklist -Title "Select categories to deploy" -Items $available -PreselectAll $true
    if (-not $selectedKeys -or $selectedKeys.Count -eq 0) {
        Write-Warn "Nothing selected"
        Read-Pause
        return
    }

    # Dry run or live
    Clear-Screen
    Write-Banner
    Write-Divider "Deploy Mode"
    Write-Host ""
    Write-Host "    " -NoNewline; Write-Host "1" -ForegroundColor Cyan -NoNewline; Write-Host "  Dry Run   " -NoNewline; Write-Host "(preview changes, touch nothing)" -ForegroundColor DarkGray
    Write-Host "    " -NoNewline; Write-Host "2" -ForegroundColor Cyan -NoNewline; Write-Host "  Apply     " -NoNewline; Write-Host "(make changes to this PC)" -ForegroundColor DarkGray
    Write-Host "    " -NoNewline; Write-Host "0" -ForegroundColor Cyan -NoNewline; Write-Host "  Cancel" -ForegroundColor DarkGray

    $defaultMode = if ($settings['dry_run_by_default']) { "1" } else { "" }
    $mode = Read-Prompt "Choose mode" $defaultMode
    if ($mode -eq "0" -or $mode -eq "") { return }

    $dryRun = $mode -ne "2"

    if (-not $dryRun -and $settings['confirm_before_apply']) {
        Clear-Screen
        Write-Banner
        Write-Divider "CONFIRM DEPLOYMENT"
        Write-Host ""
        Write-Warn "This will modify settings on THIS PC."
        Write-Info "Source profile: $hostname"
        Write-Info "Categories: $($selectedKeys.Count)"
        if ($settings['auto_backup_before_deploy']) {
            Write-Info "Auto-backup: ON - current values will be backed up first"
        }
        Write-Host ""
        $confirm = Read-Prompt "Type YES to proceed"
        if ($confirm -ne "YES") {
            Write-Info "Cancelled."
            Read-Pause
            return
        }
    }

    # Auto-backup
    if (-not $dryRun -and $settings['auto_backup_before_deploy']) {
        $backupDir = Get-BackupDir $settings
        $ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
        $backupPath = Join-Path $backupDir $ts
        $null = New-Item -Path $backupPath -ItemType Directory -Force

        $backupProfile = [ordered]@{}
        foreach ($mod in $script:CAPTURE_MODULES) {
            $ckey = $mod[0]; $cfunc = $mod[2]
            if ($selectedKeys -contains $ckey) {
                try { $backupProfile[$ckey] = & $cfunc }
                catch { $backupProfile[$ckey] = [ordered]@{ error = "backup capture failed" } }
            }
        }
        $backupJson = Join-Path $backupPath "pre_deploy_backup.json"
        $backupProfile | ConvertTo-Json -Depth 10 | Set-Content -Path $backupJson -Encoding UTF8
        Write-Info "Pre-deploy backup saved: $backupPath"
    }

    # Execute deployment
    Clear-Screen
    Write-Banner
    $modeLabel = if ($dryRun) { "DRY RUN" } else { "APPLYING" }
    Write-Divider "DEPLOYING - $modeLabel"

    $allResults = @{ applied = @(); skipped = @(); errors = @() }

    foreach ($mod in $script:DEPLOY_MODULES) {
        $key = $mod[0]; $label = $mod[1]; $func = $mod[2]
        if ($selectedKeys -notcontains $key) { continue }
        $data = $profileHash[$key]
        if (-not $data) {
            $allResults['skipped'] += $label
            continue
        }
        Write-Host ""
        Write-Divider $label
        try {
            $results = & $func $data $dryRun
            $allResults['applied'] += $label
        }
        catch {
            Write-Fail "$label`: $($_.Exception.Message)"
            $allResults['errors'] += "$label`: $($_.Exception.Message)"
        }
    }

    # Report
    Write-Host ""
    $dblLine = [string][char]0x2550 * 48
    Write-Host "  $dblLine" -ForegroundColor Cyan
    Write-Host "    DEPLOYMENT REPORT" -ForegroundColor White
    Write-Host "  $dblLine" -ForegroundColor Cyan
    Write-Host ""
    foreach ($a in $allResults['applied']) { Write-Success $a }
    foreach ($s in $allResults['skipped']) { Write-Warn "$s (skipped - no data)" }
    foreach ($e in $allResults['errors'])  { Write-Fail $e }

    if (-not $dryRun) {
        Write-Host ""
        Write-Warn "Some changes may require a logoff/restart to take effect."
    }
    Read-Pause
}

# Helper: Convert PSCustomObject to ordered hashtable recursively
function ConvertTo-Hashtable {
    param([object]$InputObject)

    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $hash = [ordered]@{}
        foreach ($prop in $InputObject.PSObject.Properties) {
            $hash[$prop.Name] = ConvertTo-Hashtable $prop.Value
        }
        return $hash
    }
    elseif ($InputObject -is [System.Collections.IList]) {
        $list = @()
        foreach ($item in $InputObject) {
            $list += ,(ConvertTo-Hashtable $item)
        }
        return $list
    }
    else { return $InputObject }
}

# ═══════════════════════════════════════════════
#  MENU FLOW: VIEW PROFILE
# ═══════════════════════════════════════════════

function Invoke-FlowViewProfile {
    $profiles = Get-SavedProfiles
    if ($profiles.Count -eq 0) {
        Clear-Screen; Write-Banner; Write-Warn "No saved profiles."; Read-Pause; return
    }

    $options = @()
    foreach ($p in $profiles) {
        $name = Get-ProfileDisplayName $p
        $size = [math]::Round((Get-Item $p).Length / 1KB, 1)
        $options += ,@($name, "$size KB")
    }

    $choice = Show-Menu -Title "VIEW - Select a Profile" -Options $options
    if ($choice -le 0 -or $choice -gt $profiles.Count) { return }

    $profile = Get-Content $profiles[$choice - 1] -Raw | ConvertFrom-Json
    $profileHash = ConvertTo-Hashtable $profile

    while ($true) {
        $sections = @()
        foreach ($k in $profileHash.Keys) {
            $charCount = ($profileHash[$k] | ConvertTo-Json -Depth 5 -Compress).Length
            $sections += ,@($k, "$charCount chars")
        }

        $secChoice = Show-Menu -Title "Profile Sections - $(Get-ProfileDisplayName $profiles[$choice-1])" -Options $sections
        if ($secChoice -le 0 -or $secChoice -gt $sections.Count) { break }

        $key = $sections[$secChoice - 1][0]
        $data = $profileHash[$key]

        Clear-Screen
        Write-Banner
        Write-Divider "Section: $key"
        Write-Host ""
        $data | ConvertTo-Json -Depth 5 | Write-Host
        Read-Pause
    }
}

# ═══════════════════════════════════════════════
#  MENU FLOW: COMPARE PROFILES
# ═══════════════════════════════════════════════

function Invoke-FlowDiff {
    $profiles = Get-SavedProfiles
    if ($profiles.Count -lt 2) {
        Clear-Screen; Write-Banner; Write-Warn "Need at least 2 saved profiles to compare."; Read-Pause; return
    }

    $options = @()
    foreach ($p in $profiles) { $options += ,@((Get-ProfileDisplayName $p), "") }

    Clear-Screen; Write-Banner; Write-Divider "DIFF - Select FIRST profile"
    for ($i = 0; $i -lt $options.Count; $i++) {
        $num = $i + 1
        Write-Host "    " -NoNewline; Write-Host "$num" -ForegroundColor Cyan -NoNewline; Write-Host "  $($options[$i][0])"
    }
    $c1 = Read-Prompt "First profile #"
    try { $idx1 = [int]$c1 - 1 } catch { return }

    Clear-Screen; Write-Banner; Write-Divider "DIFF - Select SECOND profile"
    for ($i = 0; $i -lt $options.Count; $i++) {
        $num = $i + 1
        $marker = if ($i -eq $idx1) { " <- first" } else { "" }
        Write-Host "    " -NoNewline; Write-Host "$num" -ForegroundColor Cyan -NoNewline; Write-Host "  $($options[$i][0])" -NoNewline
        if ($marker) { Write-Host $marker -ForegroundColor Yellow } else { Write-Host "" }
    }
    $c2 = Read-Prompt "Second profile #"
    try { $idx2 = [int]$c2 - 1 } catch { return }

    if ($idx1 -eq $idx2) { Write-Warn "Same profile selected twice"; Read-Pause; return }

    $p1 = ConvertTo-Hashtable (Get-Content $profiles[$idx1] -Raw | ConvertFrom-Json)
    $p2 = ConvertTo-Hashtable (Get-Content $profiles[$idx2] -Raw | ConvertFrom-Json)

    Clear-Screen; Write-Banner
    $name1 = Get-ProfileDisplayName $profiles[$idx1]
    $name2 = Get-ProfileDisplayName $profiles[$idx2]
    Write-Divider "DIFF: $name1 vs $name2"
    Write-Host ""

    $allKeys = @($p1.Keys) + @($p2.Keys) | Sort-Object -Unique
    $diffsFound = 0

    foreach ($section in $allKeys) {
        $d1 = $p1[$section]; $d2 = $p2[$section]
        $j1 = $d1 | ConvertTo-Json -Depth 5 -Compress
        $j2 = $d2 | ConvertTo-Json -Depth 5 -Compress

        if ($j1 -eq $j2) { Write-Success "$section`: identical"; continue }
        if ($null -eq $d1) { Write-Warn "$section`: only in $name2"; $diffsFound++; continue }
        if ($null -eq $d2) { Write-Warn "$section`: only in $name1"; $diffsFound++; continue }

        if ($d1 -is [hashtable] -and $d2 -is [hashtable]) {
            $changed = @()
            $allSubKeys = @($d1.Keys) + @($d2.Keys) | Sort-Object -Unique
            foreach ($k in $allSubKeys) {
                $v1j = $d1[$k] | ConvertTo-Json -Depth 3 -Compress
                $v2j = $d2[$k] | ConvertTo-Json -Depth 3 -Compress
                if ($v1j -ne $v2j) { $changed += $k }
            }
            if ($changed.Count -gt 0) {
                Write-Fail "$section`: $($changed.Count) differences"
                $showCount = [Math]::Min($changed.Count, 5)
                for ($i = 0; $i -lt $showCount; $i++) {
                    $k = $changed[$i]
                    $v1s = ($d1[$k] | ConvertTo-Json -Depth 2 -Compress)
                    $v2s = ($d2[$k] | ConvertTo-Json -Depth 2 -Compress)
                    if ($v1s.Length -gt 40) { $v1s = $v1s.Substring(0, 40) }
                    if ($v2s.Length -gt 40) { $v2s = $v2s.Substring(0, 40) }
                    Write-Host "       $k`: $v1s -> $v2s" -ForegroundColor DarkGray
                }
                if ($changed.Count -gt 5) {
                    Write-Host "       ...and $($changed.Count - 5) more" -ForegroundColor DarkGray
                }
                $diffsFound += $changed.Count
            }
        }
        else {
            Write-Fail "$section`: different"
            $diffsFound++
        }
    }

    Write-Host ""
    if ($diffsFound -eq 0) { Write-Success "Profiles are identical!" }
    else { Write-Info "Total differences: $diffsFound" }
    Read-Pause
}

# ═══════════════════════════════════════════════
#  MENU FLOW: DELETE PROFILE
# ═══════════════════════════════════════════════

function Invoke-FlowDeleteProfile {
    $profiles = Get-SavedProfiles
    if ($profiles.Count -eq 0) {
        Clear-Screen; Write-Banner; Write-Warn "No saved profiles."; Read-Pause; return
    }

    $options = @()
    foreach ($p in $profiles) {
        $name = Get-ProfileDisplayName $p
        $size = [math]::Round((Get-Item $p).Length / 1KB, 1)
        $options += ,@($name, "$size KB")
    }

    $choice = Show-Menu -Title "DELETE - Select a Profile" -Options $options
    if ($choice -le 0 -or $choice -gt $profiles.Count) { return }

    $target = $profiles[$choice - 1]
    $name = Get-ProfileDisplayName $target
    $confirm = Read-Prompt "Delete $name? Type DELETE to confirm"

    if ($confirm -eq "DELETE") {
        $parentDir = Split-Path $target -Parent
        $settings = Get-AppSettings
        $pdir = Get-ProfilesDir $settings
        if ((Split-Path $target -Leaf) -eq "profile.json" -and $parentDir -ne $pdir) {
            Remove-Item $parentDir -Recurse -Force
            Write-Success "Deleted folder: $name"
        }
        else {
            Remove-Item $target -Force
            Write-Success "Deleted $name"
        }
    }
    else {
        Write-Info "Cancelled"
    }
    Read-Pause
}

# ═══════════════════════════════════════════════
#  SECURITY & ASSET AUDIT (INLINE)
# ═══════════════════════════════════════════════

function Audit-AssetIntelligence {
    $result = [ordered]@{}
    try {
        $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop
        $result['cpu'] = [ordered]@{
            name         = $cpu.Name
            cores        = $cpu.NumberOfCores
            logical      = $cpu.NumberOfLogicalProcessors
            max_clock_mhz = $cpu.MaxClockSpeed
            architecture = $cpu.Architecture
        }
    } catch { $result['cpu'] = [ordered]@{ error = $_.Exception.Message } }

    try {
        $mem = Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop
        $sticks = @()
        foreach ($m in $mem) {
            $sticks += [ordered]@{
                capacity_gb = [math]::Round($m.Capacity / 1GB, 1)
                speed_mhz   = $m.Speed
                manufacturer = $m.Manufacturer
                part_number  = $m.PartNumber
            }
        }
        $totalGb = ($sticks | Measure-Object -Property capacity_gb -Sum).Sum
        $result['memory'] = [ordered]@{ total_gb = $totalGb; sticks = $sticks }
    } catch { $result['memory'] = [ordered]@{ error = $_.Exception.Message } }

    try {
        $gpu = Get-CimInstance Win32_VideoController -ErrorAction Stop
        $gpuList = @()
        foreach ($g in $gpu) {
            $gpuList += [ordered]@{
                name        = $g.Name
                driver_ver  = $g.DriverVersion
                vram_mb     = [math]::Round($g.AdapterRAM / 1MB, 0)
            }
        }
        $result['gpu'] = $gpuList
    } catch { $result['gpu'] = @() }

    try {
        $disks = Get-CimInstance Win32_DiskDrive -ErrorAction Stop
        $diskList = @()
        foreach ($d in $disks) {
            $diskList += [ordered]@{
                model    = $d.Model
                size_gb  = [math]::Round($d.Size / 1GB, 1)
                type     = $d.MediaType
                serial   = $d.SerialNumber
            }
        }
        $result['disks'] = $diskList
    } catch { $result['disks'] = @() }

    try {
        $battery = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
        if ($battery) {
            $result['battery'] = [ordered]@{
                status      = $battery.Status
                charge_pct  = $battery.EstimatedChargeRemaining
                description = $battery.Description
            }
        }
        else { $result['battery'] = "No battery detected" }
    } catch { $result['battery'] = "N/A" }

    try {
        $bios = Get-CimInstance Win32_BIOS -ErrorAction Stop
        $result['bios'] = [ordered]@{
            manufacturer  = $bios.Manufacturer
            version       = $bios.SMBIOSBIOSVersion
            serial        = $bios.SerialNumber
            release_date  = if ($bios.ReleaseDate) { $bios.ReleaseDate.ToString("o") } else { "N/A" }
        }
    } catch { $result['bios'] = [ordered]@{ error = $_.Exception.Message } }

    # TPM
    try {
        $tpm = Get-CimInstance -Namespace "root\cimv2\Security\MicrosoftTpm" -ClassName Win32_Tpm -ErrorAction Stop
        $result['tpm'] = [ordered]@{
            present       = $true
            version       = $tpm.SpecVersion
            manufacturer  = $tpm.ManufacturerIdTxt
            enabled       = $tpm.IsEnabled_InitialValue
            activated     = $tpm.IsActivated_InitialValue
        }
    } catch {
        $result['tpm'] = [ordered]@{ present = $false; error = "TPM not found or access denied" }
    }

    return $result
}

function Audit-UserAccounts {
    $result = [ordered]@{}
    try {
        $users = Get-LocalUser -ErrorAction Stop
        $userList = @()
        foreach ($u in $users) {
            $userList += [ordered]@{
                name       = $u.Name
                enabled    = $u.Enabled
                last_logon = if ($u.LastLogon) { $u.LastLogon.ToString("o") } else { "Never" }
                password_required = $u.PasswordRequired
                password_changeable = $u.UserMayChangePassword
            }
        }
        $result['local_users'] = $userList
    } catch { $result['local_users'] = @() }

    try {
        $admins = Get-LocalGroupMember -Group "Administrators" -ErrorAction Stop
        $result['admin_members'] = @($admins | ForEach-Object { $_.Name })
    } catch { $result['admin_members'] = @() }

    # Guest account
    try {
        $guest = Get-LocalUser -Name "Guest" -ErrorAction Stop
        $result['guest_enabled'] = $guest.Enabled
    } catch { $result['guest_enabled'] = $false }

    return $result
}

function Audit-Certificates {
    $result = [ordered]@{}
    $stores = @("Cert:\CurrentUser\My", "Cert:\CurrentUser\Root", "Cert:\LocalMachine\My", "Cert:\LocalMachine\Root")

    foreach ($store in $stores) {
        try {
            $certs = Get-ChildItem $store -ErrorAction SilentlyContinue
            $certList = @()
            foreach ($c in $certs) {
                $certList += [ordered]@{
                    subject     = $c.Subject
                    issuer      = $c.Issuer
                    not_after   = $c.NotAfter.ToString("o")
                    thumbprint  = $c.Thumbprint
                    expired     = ($c.NotAfter -lt (Get-Date))
                }
            }
            $storeName = $store -replace 'Cert:\\', ''
            $result[$storeName] = [ordered]@{
                count = $certList.Count
                expired = ($certList | Where-Object { $_.expired }).Count
                certs = $certList
            }
        } catch {}
    }
    return $result
}

function Audit-NetworkSecurity {
    $result = [ordered]@{}

    # Open TCP connections
    try {
        $connections = Get-NetTCPConnection -State Established,Listen -ErrorAction Stop |
            Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess |
            Sort-Object LocalPort
        $connList = @()
        foreach ($c in $connections) {
            $procName = ""
            try { $procName = (Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue).ProcessName } catch {}
            $connList += [ordered]@{
                local_addr  = "$($c.LocalAddress):$($c.LocalPort)"
                remote_addr = "$($c.RemoteAddress):$($c.RemotePort)"
                state       = $c.State.ToString()
                process     = "$procName (PID $($c.OwningProcess))"
            }
        }
        $result['tcp_connections'] = $connList
    } catch { $result['tcp_connections'] = @() }

    # Network adapters
    try {
        $adapters = Get-NetAdapter -ErrorAction Stop
        $adapterList = @()
        foreach ($a in $adapters) {
            $adapterList += [ordered]@{
                name      = $a.Name
                status    = $a.Status.ToString()
                mac       = $a.MacAddress
                speed_mbps = if ($a.LinkSpeed) { $a.LinkSpeed } else { "N/A" }
            }
        }
        $result['adapters'] = $adapterList
    } catch { $result['adapters'] = @() }

    # Firewall profiles
    try {
        $fwProfiles = Get-NetFirewallProfile -ErrorAction Stop
        $fwList = @()
        foreach ($p in $fwProfiles) {
            $fwList += [ordered]@{
                name     = $p.Name
                enabled  = $p.Enabled
                action   = $p.DefaultInboundAction.ToString()
            }
        }
        $result['firewall_profiles'] = $fwList
    } catch { $result['firewall_profiles'] = @() }

    # Shares
    try {
        $shares = Get-SmbShare -ErrorAction SilentlyContinue
        $shareList = @()
        foreach ($s in $shares) {
            $shareList += [ordered]@{
                name = $s.Name
                path = $s.Path
                description = $s.Description
            }
        }
        $result['smb_shares'] = $shareList
    } catch { $result['smb_shares'] = @() }

    return $result
}

function Audit-DomainInfo {
    $result = [ordered]@{}
    try {
        $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
        $result['domain_role'] = switch ($cs.DomainRole) {
            0 { "Standalone Workstation" }
            1 { "Member Workstation" }
            2 { "Standalone Server" }
            3 { "Member Server" }
            4 { "Backup Domain Controller" }
            5 { "Primary Domain Controller" }
            default { "Unknown ($($cs.DomainRole))" }
        }
        $result['domain'] = $cs.Domain
        $result['part_of_domain'] = $cs.PartOfDomain
    } catch {}

    # dsregcmd for Azure AD
    try {
        $dsreg = & dsregcmd /status 2>$null
        $azureJoined = $false; $deviceId = ""
        foreach ($line in $dsreg) {
            if ($line -match 'AzureAdJoined\s*:\s*(\w+)') { $azureJoined = $Matches[1] -eq "YES" }
            if ($line -match 'DeviceId\s*:\s*(.+)') { $deviceId = $Matches[1].Trim() }
        }
        $result['azure_ad_joined'] = $azureJoined
        $result['device_id'] = $deviceId
    } catch {}

    return $result
}

function Audit-ThreatDetection {
    param([string]$AlertLevel = "medium")
    $result = [ordered]@{ findings = @(); severity_counts = [ordered]@{ critical = 0; warning = 0; info = 0 } }

    # Suspicious processes
    try {
        $suspiciousNames = @("mimikatz", "lazagne", "procdump", "psexec", "netcat", "nc", "ncat",
                             "pwdump", "wce", "gsecdump", "covenant", "empire", "meterpreter",
                             "cobalt", "bloodhound", "rubeus", "sharphound")
        $procs = Get-Process -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            foreach ($s in $suspiciousNames) {
                if ($p.ProcessName -match $s) {
                    $result['findings'] += [ordered]@{
                        category = "Suspicious Process"
                        severity = "critical"
                        detail   = "Process '$($p.ProcessName)' (PID $($p.Id)) matches known threat tool"
                    }
                    $result['severity_counts']['critical']++
                }
            }
        }
    } catch {}

    # Startup items
    try {
        $startupPaths = @(
            "HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "HKLM\Software\Microsoft\Windows\CurrentVersion\Run",
            "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce",
            "HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce"
        )
        foreach ($path in $startupPaths) {
            try {
                $items = Get-ItemProperty "Registry::$path" -ErrorAction SilentlyContinue
                if ($items) {
                    foreach ($prop in $items.PSObject.Properties) {
                        if ($prop.Name -match '^PS' -or $prop.Name -eq '(default)') { continue }
                        $val = $prop.Value.ToString().ToLower()
                        if ($val -match 'powershell.*-enc' -or $val -match 'cmd.*\/c.*start' -or
                            $val -match 'mshta' -or $val -match 'wscript.*\.vbs' -or
                            $val -match 'cscript.*\.vbs' -or $val -match 'certutil.*-decode') {
                            $sev = if ($AlertLevel -eq "low") { "warning" } else { "critical" }
                            $result['findings'] += [ordered]@{
                                category = "Suspicious Startup"
                                severity = $sev
                                detail   = "Suspicious startup entry '$($prop.Name)': $($prop.Value)"
                            }
                            $result['severity_counts'][$sev]++
                        }
                    }
                }
            } catch {}
        }
    } catch {}

    # Scheduled tasks
    try {
        $tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Ready' -or $_.State -eq 'Running' }
        $suspTaskCount = 0
        foreach ($t in $tasks) {
            try {
                $actions = $t.Actions
                foreach ($a in $actions) {
                    $exe = $a.Execute
                    if ($exe -and ($exe -match 'powershell.*-enc' -or $exe -match 'mshta' -or
                                   $exe -match 'cmd.*\/c.*http' -or $exe -match 'certutil')) {
                        $result['findings'] += [ordered]@{
                            category = "Suspicious Task"
                            severity = "warning"
                            detail   = "Task '$($t.TaskName)' runs: $exe"
                        }
                        $result['severity_counts']['warning']++
                        $suspTaskCount++
                    }
                }
            } catch {}
        }
        $result['total_scheduled_tasks'] = if ($tasks) { $tasks.Count } else { 0 }
        $result['suspicious_tasks'] = $suspTaskCount
    } catch {}

    # Environment variable check (PATH hijacking)
    try {
        $pathDirs = $env:PATH -split ';'
        foreach ($d in $pathDirs) {
            if ($d -and (Test-Path $d -ErrorAction SilentlyContinue)) {
                $acl = Get-Acl $d -ErrorAction SilentlyContinue
                foreach ($access in $acl.Access) {
                    if ($access.IdentityReference -match 'Everyone|Users|Authenticated Users' -and
                        $access.FileSystemRights -match 'Write|FullControl|Modify') {
                        if ($AlertLevel -ne "low") {
                            $result['findings'] += [ordered]@{
                                category = "PATH Hijack Risk"
                                severity = "warning"
                                detail   = "'$d' is writable by '$($access.IdentityReference)'"
                            }
                            $result['severity_counts']['warning']++
                        }
                    }
                }
            }
        }
    } catch {}

    # Browser extensions summary
    $result['browser_extensions_note'] = "Manual review recommended for Chrome/Edge/Firefox extensions"

    return $result
}

function Audit-Compliance {
    $result = [ordered]@{ checks = @(); passed = 0; failed = 0; total = 0 }

    $checks = @(
        @{ name = "BitLocker"; test = {
            try {
                $bl = Get-BitLockerVolume -MountPoint "C:" -ErrorAction Stop
                return $bl.ProtectionStatus -eq 'On'
            } catch { return $false }
        }; remediation = "Enable BitLocker: manage-bde -on C: -RecoveryPassword" },
        @{ name = "Windows Defender Antivirus"; test = {
            try { return (Get-MpComputerStatus -ErrorAction Stop).AntivirusEnabled } catch { return $false }
        }; remediation = "Enable Defender via Windows Security > Virus & Threat Protection" },
        @{ name = "Real-Time Protection"; test = {
            try { return (Get-MpComputerStatus -ErrorAction Stop).RealTimeProtectionEnabled } catch { return $false }
        }; remediation = "Enable in Windows Security > Virus & Threat Protection > Real-time protection" },
        @{ name = "Firewall (Domain)"; test = {
            try { return (Get-NetFirewallProfile -Name Domain -ErrorAction Stop).Enabled } catch { return $false }
        }; remediation = "Enable: Set-NetFirewallProfile -Profile Domain -Enabled True" },
        @{ name = "Firewall (Private)"; test = {
            try { return (Get-NetFirewallProfile -Name Private -ErrorAction Stop).Enabled } catch { return $false }
        }; remediation = "Enable: Set-NetFirewallProfile -Profile Private -Enabled True" },
        @{ name = "Firewall (Public)"; test = {
            try { return (Get-NetFirewallProfile -Name Public -ErrorAction Stop).Enabled } catch { return $false }
        }; remediation = "Enable: Set-NetFirewallProfile -Profile Public -Enabled True" },
        @{ name = "UAC Enabled"; test = {
            $val = Get-RegValue "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" "EnableLUA"
            return $val -eq 1
        }; remediation = "Enable UAC: Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableLUA -Value 1" },
        @{ name = "Secure Boot"; test = {
            try { return (Confirm-SecureBootUEFI -ErrorAction Stop) } catch { return $false }
        }; remediation = "Enable Secure Boot in BIOS/UEFI firmware settings" },
        @{ name = "SMBv1 Disabled"; test = {
            try {
                $smb1 = Get-SmbServerConfiguration -ErrorAction Stop
                return -not $smb1.EnableSMB1Protocol
            } catch { return $true }
        }; remediation = "Disable SMBv1: Set-SmbServerConfiguration -EnableSMB1Protocol `$false -Force" },
        @{ name = "RDP Disabled or Secured"; test = {
            $rdp = Get-RegValue "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server" "fDenyTSConnections"
            return $rdp -eq 1
        }; remediation = "Disable RDP: Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 1" },
        @{ name = "Guest Account Disabled"; test = {
            try { return -not (Get-LocalUser -Name "Guest" -ErrorAction Stop).Enabled } catch { return $true }
        }; remediation = "Disable Guest: Disable-LocalUser -Name Guest" },
        @{ name = "Password Policy (Min Length)"; test = {
            try {
                $policy = & net accounts 2>$null
                foreach ($line in $policy) {
                    if ($line -match 'Minimum password length\s*:\s*(\d+)') {
                        return [int]$Matches[1] -ge 8
                    }
                }
                return $false
            } catch { return $false }
        }; remediation = "Set minimum password length: net accounts /minpwlen:8" }
    )

    foreach ($check in $checks) {
        $result['total']++
        try {
            $passed = & $check.test
            $result['checks'] += [ordered]@{
                name        = $check.name
                passed      = [bool]$passed
                remediation = $check.remediation
            }
            if ($passed) { $result['passed']++ } else { $result['failed']++ }
        }
        catch {
            $result['checks'] += [ordered]@{
                name        = $check.name
                passed      = $false
                remediation = $check.remediation
                error       = $_.Exception.Message
            }
            $result['failed']++
        }
    }
    return $result
}

function Audit-EventLogs {
    $result = [ordered]@{}

    # Failed logins (Event 4625)
    try {
        $failedLogins = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625} -MaxEvents 20 -ErrorAction Stop
        $result['failed_logins'] = @()
        foreach ($evt in $failedLogins) {
            $result['failed_logins'] += [ordered]@{
                time    = $evt.TimeCreated.ToString("o")
                message = $evt.Message.Substring(0, [Math]::Min($evt.Message.Length, 200))
            }
        }
    } catch { $result['failed_logins'] = @() }

    # Successful logins (Event 4624)
    try {
        $successLogins = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624} -MaxEvents 10 -ErrorAction Stop
        $result['recent_logins'] = @()
        foreach ($evt in $successLogins) {
            $result['recent_logins'] += [ordered]@{
                time    = $evt.TimeCreated.ToString("o")
                message = $evt.Message.Substring(0, [Math]::Min($evt.Message.Length, 200))
            }
        }
    } catch { $result['recent_logins'] = @() }

    # New services installed (Event 7045)
    try {
        $newServices = Get-WinEvent -FilterHashtable @{LogName='System'; Id=7045} -MaxEvents 10 -ErrorAction Stop
        $result['new_services'] = @()
        foreach ($evt in $newServices) {
            $result['new_services'] += [ordered]@{
                time    = $evt.TimeCreated.ToString("o")
                message = $evt.Message.Substring(0, [Math]::Min($evt.Message.Length, 200))
            }
        }
    } catch { $result['new_services'] = @() }

    return $result
}

function Invoke-SecurityAudit {
    param(
        [array]$SelectedSections = @("asset_intelligence","user_accounts","certificates","network","domain","threat_detection","compliance","logs_forensics"),
        [string]$AlertLevel = "medium"
    )

    $auditData = [ordered]@{
        audit_meta = [ordered]@{
            hostname    = $env:COMPUTERNAME
            timestamp   = (Get-Date).ToString("o")
            is_admin    = $script:IsAdmin
            alert_level = $AlertLevel
        }
    }

    $sectionFuncs = [ordered]@{
        asset_intelligence = @("Asset Intelligence",     { Audit-AssetIntelligence })
        user_accounts      = @("User Accounts & Access", { Audit-UserAccounts })
        certificates       = @("Certificates",           { Audit-Certificates })
        network            = @("Network & Connections",   { Audit-NetworkSecurity })
        domain             = @("Domain & Azure AD",       { Audit-DomainInfo })
        threat_detection   = @("Threat Detection",        { param($al) Audit-ThreatDetection $al })
        compliance         = @("Compliance Posture",      { Audit-Compliance })
        logs_forensics     = @("Event Log Forensics",     { Audit-EventLogs })
    }

    foreach ($key in $sectionFuncs.Keys) {
        if ($SelectedSections -notcontains $key) { continue }
        $label = $sectionFuncs[$key][0]
        $func  = $sectionFuncs[$key][1]
        Write-SpinnerLine $label
        try {
            if ($key -eq "threat_detection") {
                $auditData[$key] = & $func $AlertLevel
            }
            else {
                $auditData[$key] = & $func
            }
            Write-SpinnerDone $label
        }
        catch {
            $auditData[$key] = [ordered]@{ error = $_.Exception.Message }
            Write-SpinnerFail $label $_.Exception.Message
        }
    }

    return $auditData
}

# ═══════════════════════════════════════════════
#  GUIDANCE ENGINE
# ═══════════════════════════════════════════════

$script:GUIDANCE = @{
    "BitLocker"                   = "Enable BitLocker full-disk encryption to protect data at rest. Run: manage-bde -on C: -RecoveryPassword. Save the recovery key to a secure location."
    "Windows Defender Antivirus"  = "Ensure Windows Defender is enabled and definitions are up to date. Open Windows Security > Virus & Threat Protection > Check for updates."
    "Real-Time Protection"        = "Real-time protection scans files as they are accessed. Enable via Windows Security > Virus & Threat Protection > Manage settings."
    "Firewall (Domain)"           = "Domain firewall profile should be enabled for corporate network protection. Run: Set-NetFirewallProfile -Profile Domain -Enabled True"
    "Firewall (Private)"          = "Private firewall profile protects home/work networks. Run: Set-NetFirewallProfile -Profile Private -Enabled True"
    "Firewall (Public)"           = "Public firewall profile is critical for untrusted networks. Run: Set-NetFirewallProfile -Profile Public -Enabled True"
    "UAC Enabled"                 = "User Account Control prevents unauthorized changes. Keep enabled. If disabled, re-enable in Control Panel > User Accounts > Change UAC settings."
    "Secure Boot"                 = "Secure Boot prevents unauthorized bootloaders. Enable in BIOS/UEFI. Requires UEFI mode (not Legacy/CSM)."
    "SMBv1 Disabled"              = "SMBv1 is vulnerable to EternalBlue/WannaCry. Disable: Set-SmbServerConfiguration -EnableSMB1Protocol `$false -Force. Or use: Disable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol"
    "RDP Disabled or Secured"     = "Remote Desktop should be disabled if not needed. If required, use Network Level Authentication and restrict access via firewall rules."
    "Guest Account Disabled"      = "The Guest account provides anonymous access. Ensure it is disabled: Disable-LocalUser -Name Guest"
    "Password Policy (Min Length)" = "Minimum password length of 8+ characters is recommended. Set via: net accounts /minpwlen:8. Consider 12+ for enhanced security."
    "Suspicious Process"          = "A process matching a known offensive tool was detected. Investigate immediately: identify the source, check if legitimate, and terminate if malicious."
    "Suspicious Startup"          = "A startup entry contains suspicious commands (encoded PowerShell, mshta, etc.). Review and remove if not legitimate."
    "Suspicious Task"             = "A scheduled task runs suspicious commands. Review task details and remove if not authorized."
    "PATH Hijack Risk"            = "A directory in PATH is writable by non-admin users. Attackers could place malicious executables there. Restrict write permissions on PATH directories."
}

# ═══════════════════════════════════════════════
#  AUDIT HTML REPORT GENERATOR
# ═══════════════════════════════════════════════

function Generate-AuditHtml {
    param([hashtable]$AuditData, [string]$FilePath)

    try { Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue } catch {}

    $meta = $AuditData['audit_meta']
    $hostname  = if ($meta['hostname']) { $meta['hostname'] } else { "Unknown" }
    $timestamp = if ($meta['timestamp']) { $meta['timestamp'] } else { "" }
    $isAdmin   = if ($meta['is_admin']) { "Yes" } else { "No" }
    $alertLvl  = if ($meta['alert_level']) { $meta['alert_level'] } else { "medium" }
    $tsDate    = if ($timestamp.Length -ge 10) { $timestamp.Substring(0, 10) } else { "N/A" }

    # Compliance stats
    $compliance = $AuditData['compliance']
    $passed = 0; $failed = 0; $total = 0
    if ($compliance) {
        $passed = $compliance['passed']; $failed = $compliance['failed']; $total = $compliance['total']
    }
    $pct = if ($total -gt 0) { [math]::Round(($passed / $total) * 100) } else { 0 }
    $pctColor = if ($pct -ge 80) { "#3fb950" } elseif ($pct -ge 60) { "#d29922" } else { "#f85149" }

    # Threat counts
    $threats = $AuditData['threat_detection']
    $nCrit = 0; $nWarn = 0; $nInfo = 0
    if ($threats -and $threats['severity_counts']) {
        $nCrit = $threats['severity_counts']['critical']
        $nWarn = $threats['severity_counts']['warning']
        $nInfo = $threats['severity_counts']['info']
    }

    # Build section cards
    $sectionMap = [ordered]@{
        asset_intelligence = @("🖥️", "Asset Intelligence")
        user_accounts      = @("👥", "User Accounts & Access")
        certificates       = @("📜", "Certificates")
        network            = @("🌐", "Network & Connections")
        domain             = @("🏢", "Domain & Azure AD")
        threat_detection   = @("🛡️", "Threat Detection & IOCs")
        compliance         = @("✅", "Compliance Posture")
        logs_forensics     = @("📋", "Event Log Forensics")
    }

    $cards = ""
    foreach ($key in $sectionMap.Keys) {
        $data = $AuditData[$key]
        if (-not $data) { continue }
        $icon = $sectionMap[$key][0]; $title = $sectionMap[$key][1]

        $bodyHtml = ""
        if ($key -eq "compliance" -and $data['checks']) {
            $bodyHtml += "<table class=`"data-table`">"
            foreach ($chk in $data['checks']) {
                $statusIcon = if ($chk['passed']) { '<span class="val-true">PASS &#x2713;</span>' } else { '<span class="val-false">FAIL &#x2717;</span>' }
                $rem = [System.Web.HttpUtility]::HtmlEncode($chk['remediation'])
                $guidance = ""
                if (-not $chk['passed'] -and $script:GUIDANCE[$chk['name']]) {
                    $g = [System.Web.HttpUtility]::HtmlEncode($script:GUIDANCE[$chk['name']])
                    $guidance = "<br><span style=`"color:#58a6ff;font-size:0.8rem`">💡 $g</span>"
                }
                $bodyHtml += "<tr><td>$($chk['name'])</td><td>$statusIcon<br><span style=`"color:#8b949e;font-size:0.8rem`">$rem</span>$guidance</td></tr>"
            }
            $bodyHtml += "</table>"
        }
        elseif ($key -eq "threat_detection" -and $data['findings']) {
            if ($data['findings'].Count -gt 0) {
                $bodyHtml += "<table class=`"data-table`">"
                foreach ($f in $data['findings']) {
                    $sevColor = switch ($f['severity']) { "critical" { "#f85149" }; "warning" { "#d29922" }; default { "#58a6ff" } }
                    $sevLabel = $f['severity'].ToUpper()
                    $det = [System.Web.HttpUtility]::HtmlEncode($f['detail'])
                    $guidance = ""
                    if ($script:GUIDANCE[$f['category']]) {
                        $g = [System.Web.HttpUtility]::HtmlEncode($script:GUIDANCE[$f['category']])
                        $guidance = "<br><span style=`"color:#58a6ff;font-size:0.8rem`">💡 $g</span>"
                    }
                    $bodyHtml += "<tr><td><span style=`"color:$sevColor;font-weight:bold`">[$sevLabel]</span> $($f['category'])</td><td>$det$guidance</td></tr>"
                }
                $bodyHtml += "</table>"
            }
            else {
                $bodyHtml = "<p style=`"color:#3fb950`">No threats detected &#x2713;</p>"
            }
            # Extra info
            if ($data['total_scheduled_tasks']) {
                $bodyHtml += "<table class=`"data-table`"><tr><td>Total Scheduled Tasks</td><td>$($data['total_scheduled_tasks'])</td></tr>"
                $bodyHtml += "<tr><td>Suspicious Tasks</td><td>$($data['suspicious_tasks'])</td></tr></table>"
            }
        }
        else {
            $bodyHtml = Build-DataHtml -Key $key -Data $data
        }

        $badge = ""
        if ($data -is [hashtable] -or $data -is [System.Collections.Specialized.OrderedDictionary]) {
            $badge = "$($data.Count) items"
        }

        $cards += @"
  <div class="section open" data-key="$key">
    <div class="section-header">
      <div class="section-icon">$icon</div>
      <div class="section-title">$title</div>
      <div class="section-badge">$badge</div>
      <div class="section-arrow">&#x25b6;</div>
    </div>
    <div class="section-body">$bodyHtml</div>
  </div>
"@
    }

    $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🛡️ WinDNA Security Audit - $hostname</title>
<style>
  :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3; --dim: #8b949e; --cyan: #58a6ff; --green: #3fb950; --yellow: #d29922; --red: #f85149; --purple: #bc8cff; --font: 'Segoe UI', sans-serif; --mono: 'Cascadia Code', 'Consolas', monospace; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; }
  .header { background: linear-gradient(135deg, #161b22 0%, #1a2332 100%); border-bottom: 1px solid var(--border); padding: 2rem; text-align: center; }
  .header h1 { font-size: 2rem; font-weight: 700; } .header h1 span { color: var(--cyan); }
  .header .subtitle { color: var(--dim); font-size: 0.95rem; }
  .header .meta-row { display: flex; justify-content: center; gap: 2rem; margin-top: 1rem; flex-wrap: wrap; }
  .header .meta-item { font-size: 0.85rem; color: var(--dim); } .header .meta-item strong { color: var(--text); }
  .stats { display: flex; justify-content: center; gap: 1.5rem; padding: 1rem 2rem; background: var(--card); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  .stat { text-align: center; min-width: 80px; } .stat .num { font-size: 1.5rem; font-weight: 700; } .stat .label { font-size: 0.75rem; color: var(--dim); text-transform: uppercase; }
  .container { max-width: 900px; margin: 0 auto; padding: 1.5rem; }
  .section { background: var(--card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 1rem; overflow: hidden; }
  .section:hover { border-color: var(--cyan); }
  .section-header { display: flex; align-items: center; padding: 0.9rem 1.2rem; cursor: pointer; user-select: none; gap: 0.75rem; }
  .section-header:hover { background: rgba(88,166,255,0.05); }
  .section-icon { font-size: 1.3rem; width: 2rem; text-align: center; }
  .section-title { font-weight: 600; flex: 1; } .section-badge { font-size: 0.75rem; padding: 0.15rem 0.6rem; border-radius: 10px; background: rgba(88,166,255,0.15); color: var(--cyan); }
  .section-arrow { color: var(--dim); transition: transform 0.2s; font-size: 0.8rem; }
  .section.open .section-arrow { transform: rotate(90deg); }
  .section-body { display: none; padding: 0 1.2rem 1.2rem; border-top: 1px solid var(--border); }
  .section.open .section-body { display: block; padding-top: 1rem; }
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table tr { border-bottom: 1px solid rgba(48,54,61,0.5); } .data-table tr:last-child { border-bottom: none; }
  .data-table td { padding: 0.45rem 0; vertical-align: top; }
  .data-table td:first-child { color: var(--dim); font-size: 0.85rem; width: 40%; padding-right: 1rem; }
  .data-table td:last-child { font-family: var(--mono); font-size: 0.85rem; word-break: break-word; }
  .val-true { color: var(--green); } .val-false { color: var(--red); } .val-empty { color: var(--dim); font-style: italic; }
  .val-string { color: var(--text); } .val-number { color: var(--purple); }
  .item-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.3rem; }
  .item-tag { font-size: 0.8rem; padding: 0.2rem 0.6rem; border-radius: 6px; background: rgba(88,166,255,0.1); color: var(--cyan); font-family: var(--mono); border: 1px solid rgba(88,166,255,0.15); }
  .subsection { margin-top: 1rem; } .subsection-title { font-size: 0.8rem; text-transform: uppercase; color: var(--dim); margin-bottom: 0.5rem; font-weight: 600; }
  .footer { text-align: center; padding: 2rem; color: var(--dim); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 2rem; }
</style>
</head>
<body>
<div class="header">
  <h1>🛡️ <span>WinDNA</span> Security Audit</h1>
  <div class="subtitle">$hostname - $tsDate</div>
  <div class="meta-row">
    <div class="meta-item">Admin <strong>$isAdmin</strong></div>
    <div class="meta-item">Alert Level <strong>$alertLvl</strong></div>
  </div>
</div>
<div class="stats">
  <div class="stat"><div class="num" style="color:$pctColor">$pct%</div><div class="label">Compliance</div></div>
  <div class="stat"><div class="num" style="color:#3fb950">$passed</div><div class="label">Passed</div></div>
  <div class="stat"><div class="num" style="color:#f85149">$failed</div><div class="label">Failed</div></div>
  <div class="stat"><div class="num" style="color:#f85149">$nCrit</div><div class="label">Critical</div></div>
  <div class="stat"><div class="num" style="color:#d29922">$nWarn</div><div class="label">Warnings</div></div>
</div>
<div class="container">
$cards
</div>
<div class="footer">🛡️ WinDNA Security Audit v1.0 - Author: cyberspartan77 - $tsDate</div>
<script>
document.querySelectorAll('.section-header').forEach(h => {
  h.addEventListener('click', () => { h.parentElement.classList.toggle('open'); });
});
</script>
</body>
</html>
"@

    $html | Out-File -FilePath $FilePath -Encoding UTF8
}

# ═══════════════════════════════════════════════
#  MENU FLOW: SECURITY AUDIT
# ═══════════════════════════════════════════════

function Invoke-FlowSecurityAudit {
    $settings = Get-AppSettings
    $alertLevel = $settings['threat_alert_level']

    if (-not $script:IsAdmin) {
        Write-Host ""
        Write-Warn "For full results, run as Administrator"
        Write-Host "  Some checks need elevated access." -ForegroundColor DarkGray
        Write-Host ""
    }

    $auditItems = @(
        @("asset_intelligence", "Asset Intelligence (hardware, TPM, storage)"),
        @("user_accounts",      "User Accounts & Access (local users, admin)"),
        @("certificates",       "Certificates (stores, expired certs)"),
        @("network",            "Network & Connections (ports, shares, firewall)"),
        @("domain",             "Domain & Azure AD (join status, role)"),
        @("threat_detection",   "Threat Detection & IOCs (services, tasks, startup)"),
        @("compliance",         "Compliance Posture (BitLocker, Defender, UAC)"),
        @("logs_forensics",     "Event Log Forensics (logins, audit events)")
    )

    $selected = Show-Checklist -Title "Security Audit - Select Sections" -Items $auditItems -PreselectAll $true
    if (-not $selected -or $selected.Count -eq 0) {
        Write-Warn "Nothing selected"
        Read-Pause
        return
    }

    Clear-Screen
    Write-Banner
    Write-Divider "SECURITY AUDIT - Alert Level: $($alertLevel.ToUpper())"
    Write-Host ""

    $auditData = Invoke-SecurityAudit -SelectedSections $selected -AlertLevel $alertLevel

    # Save
    $pdir = Get-ProfilesDir $settings
    $hostClean = ($env:COMPUTERNAME -replace '[^\w\-]', '_')
    $dateStr = (Get-Date).ToString("yyyy-MM-dd")
    $folderName = "${hostClean}_${dateStr}_audit"

    if (-not $settings['auto_name_profiles']) {
        Write-Host ""
        $folderName = Read-Prompt "Audit folder name" $folderName
    }

    $folderPath = Join-Path $pdir $folderName
    if (-not (Test-Path $folderPath)) { $null = New-Item -Path $folderPath -ItemType Directory -Force }

    $jsonPath = Join-Path $folderPath "audit.json"
    $auditData | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8

    Write-SpinnerLine "Generating Audit HTML report"
    $htmlPath = Join-Path $folderPath "audit.html"
    Generate-AuditHtml -AuditData $auditData -FilePath $htmlPath
    Write-SpinnerDone "Audit HTML report generated"

    Write-Host ""
    Write-Divider "AUDIT COMPLETE"
    Write-Success "Folder: $folderPath"
    $jsonSize = [math]::Round((Get-Item $jsonPath).Length / 1KB, 1)
    $htmlSize = [math]::Round((Get-Item $htmlPath).Length / 1KB, 1)
    Write-Info "JSON:   $jsonSize KB"
    Write-Info "HTML:   $htmlSize KB"

    # Show summary
    $threats = $auditData['threat_detection']
    if ($threats -and $threats['severity_counts']) {
        $nc = $threats['severity_counts']['critical']
        $nw = $threats['severity_counts']['warning']
        $ni = $threats['severity_counts']['info']
        if ($nc) { Write-Host ""; Write-Host "  !!! $nc CRITICAL FINDINGS !!!" -ForegroundColor Red }
        if ($nw) { Write-Host "  $nw warnings" -ForegroundColor Yellow }
        if ($ni) { Write-Host "  $ni informational items" -ForegroundColor Cyan }
    }

    $comp = $auditData['compliance']
    if ($comp -and $comp['total'] -gt 0) {
        $compPct = [math]::Round(($comp['passed'] / $comp['total']) * 100)
        $compColor = if ($compPct -ge 80) { "Green" } elseif ($compPct -ge 60) { "Yellow" } else { "Red" }
        Write-Host ""
        Write-Host "  Compliance: $($comp['passed'])/$($comp['total']) checks passed ($compPct%)" -ForegroundColor $compColor
    }

    $openIt = Read-Prompt "Open HTML audit report in browser? (y/N)"
    if ($openIt -eq "y") {
        try { Start-Process $htmlPath } catch {}
    }
    Read-Pause
}

# ═══════════════════════════════════════════════
#  MENU FLOW: SETTINGS
# ═══════════════════════════════════════════════

$script:SETTINGS_DEFS = @(
    @("profile_save_location",       "Profile Save Location",        "Where captured profiles are saved (blank = ./profiles/)",   "path"),
    @("backup_directory",            "Backup Directory",             "Where pre-deploy backups go (blank = ~/.windna_backup/)",   "path"),
    @("auto_backup_before_deploy",   "Auto-Backup Before Deploy",    "Backup current values before overwriting",                 "bool"),
    @("dry_run_by_default",          "Dry-Run by Default",           "Always preview before applying changes",                   "bool"),
    @("confirm_before_apply",        "Confirm Before Apply",         "Require typing YES before deploy",                         "bool"),
    @("auto_name_profiles",          "Auto-Name Profiles",           "Skip save-as prompt, auto-generate filename",              "bool"),
    @("compact_json",                "Compact JSON",                 "Save profiles as compact (smaller) vs pretty-printed",     "bool"),
    @("color_output",                "Color Output",                 "Enable/disable terminal colors",                           "bool"),
    @("default_capture_categories",  "Default Capture Categories",   "Pre-selected categories (all or comma-separated keys)",    "text"),
    @("security_audit_with_capture", "Security Audit with Capture",  "Auto-run security audit when capturing a profile",         "bool"),
    @("threat_alert_level",          "Threat Alert Level",           "Sensitivity for threat detection (low/medium/high)",        "choice")
)

function Invoke-FlowSettings {
    $settings = Get-AppSettings

    while ($true) {
        Clear-Screen
        Write-Banner
        Write-Divider "SETTINGS"
        Write-Host ""

        for ($i = 0; $i -lt $script:SETTINGS_DEFS.Count; $i++) {
            $key   = $script:SETTINGS_DEFS[$i][0]
            $label = $script:SETTINGS_DEFS[$i][1]
            $desc  = $script:SETTINGS_DEFS[$i][2]
            $stype = $script:SETTINGS_DEFS[$i][3]
            $val   = $settings[$key]
            if ($null -eq $val) { $val = $script:DEFAULT_SETTINGS[$key] }

            $num = $i + 1
            $display = ""

            switch ($stype) {
                "bool" {
                    if ($val) { $display = "ON"; $color = "Green" }
                    else { $display = "OFF"; $color = "Red" }
                }
                "path" {
                    if ($val -and $val.ToString().Trim()) { $display = $val; $color = "Cyan" }
                    else {
                        $hint = if ($key -match 'profile') { "./profiles/ (default)" } else { "~/.windna_backup/ (default)" }
                        $display = $hint; $color = "DarkGray"
                    }
                }
                "choice" {
                    $display = $val
                    $color = switch ($val) { "low" { "Green" }; "medium" { "Yellow" }; "high" { "Red" }; default { "Cyan" } }
                }
                default { $display = $val; $color = "Cyan" }
            }

            Write-Host "    " -NoNewline
            Write-Host "$($num.ToString().PadLeft(2))" -ForegroundColor Cyan -NoNewline
            Write-Host "  $label"
            Write-Host "        $desc" -ForegroundColor DarkGray
            Write-Host "        Current: " -NoNewline
            Write-Host $display -ForegroundColor $color
            Write-Host ""
        }

        Write-Host "    " -NoNewline; Write-Host " R" -ForegroundColor Cyan -NoNewline; Write-Host "  " -NoNewline; Write-Host "Reset All to Defaults" -ForegroundColor Yellow
        Write-Host "    " -NoNewline; Write-Host " 0" -ForegroundColor Cyan -NoNewline; Write-Host "  Back to Main Menu" -ForegroundColor DarkGray
        Write-Host ""

        $choice = Read-Prompt "Setting # to change / R=reset / 0=back"

        if ($choice -eq "0" -or $choice -eq "") { break }

        if ($choice.ToUpper() -eq "R") {
            $confirm = Read-Prompt "Reset ALL settings to defaults? (y/N)"
            if ($confirm -eq "y") {
                $settings = [ordered]@{}
                foreach ($k in $script:DEFAULT_SETTINGS.Keys) { $settings[$k] = $script:DEFAULT_SETTINGS[$k] }
                Save-AppSettings $settings
                Write-Success "All settings reset to defaults"
                Read-Pause
            }
            continue
        }

        try { $idx = [int]$choice - 1 } catch { continue }
        if ($idx -lt 0 -or $idx -ge $script:SETTINGS_DEFS.Count) { continue }

        $key   = $script:SETTINGS_DEFS[$idx][0]
        $label = $script:SETTINGS_DEFS[$idx][1]
        $stype = $script:SETTINGS_DEFS[$idx][3]

        switch ($stype) {
            "bool" {
                $current = $settings[$key]
                $settings[$key] = -not $current
                Save-AppSettings $settings
            }
            "path" {
                $current = $settings[$key]
                Write-Host ""
                Write-Info "Current: $(if ($current) { $current } else { '(default)' })"
                $newVal = Read-Prompt "New path (blank = use default)"
                if ($newVal) {
                    $expanded = [System.Environment]::ExpandEnvironmentVariables($newVal)
                    if (-not (Test-Path $expanded)) {
                        $create = Read-Prompt "Directory doesn't exist. Create it? (y/N)"
                        if ($create -eq "y") {
                            try {
                                $null = New-Item -Path $expanded -ItemType Directory -Force
                                $settings[$key] = $expanded
                                Save-AppSettings $settings
                                Write-Success "Created and set: $expanded"
                            }
                            catch { Write-Fail "Could not create: $($_.Exception.Message)" }
                            Read-Pause
                        }
                        else {
                            $settings[$key] = $expanded
                            Save-AppSettings $settings
                        }
                    }
                    else {
                        $settings[$key] = $expanded
                        Save-AppSettings $settings
                    }
                }
                else {
                    $settings[$key] = ""
                    Save-AppSettings $settings
                }
            }
            "choice" {
                Write-Host ""
                Write-Info "Current: $($settings[$key])"
                Write-Host "    " -NoNewline; Write-Host "1" -ForegroundColor Cyan -NoNewline; Write-Host "  low    " -NoNewline; Write-Host "(fewer alerts, only critical)" -ForegroundColor DarkGray
                Write-Host "    " -NoNewline; Write-Host "2" -ForegroundColor Cyan -NoNewline; Write-Host "  medium " -NoNewline; Write-Host "(balanced - recommended)" -ForegroundColor DarkGray
                Write-Host "    " -NoNewline; Write-Host "3" -ForegroundColor Cyan -NoNewline; Write-Host "  high   " -NoNewline; Write-Host "(verbose, flags everything)" -ForegroundColor DarkGray
                $pick = Read-Prompt "Choose 1/2/3" "2"
                $choiceMap = @{ "1" = "low"; "2" = "medium"; "3" = "high" }
                $settings[$key] = if ($choiceMap[$pick]) { $choiceMap[$pick] } else { "medium" }
                Save-AppSettings $settings
            }
            "text" {
                Write-Host ""
                Write-Info "Current: $($settings[$key])"
                Write-Info "Enter 'all' for all categories, or comma-separated keys:"
                Write-Info "  Available: machine_identity, desktop_appearance, taskbar_start,"
                Write-Info "  file_explorer, mouse_keyboard, sound_notifications, power_sleep,"
                Write-Info "  network, privacy_security, installed_apps"
                $newVal = Read-Prompt "New value" $settings[$key]
                $settings[$key] = $newVal.Trim()
                Save-AppSettings $settings
            }
        }
    }
}

# ═══════════════════════════════════════════════
#  MAIN MENU LOOP
# ═══════════════════════════════════════════════

function Start-WinDNA {
    while ($true) {
        $nProfiles = (Get-SavedProfiles).Count
        $profileInfo = if ($nProfiles) { "$nProfiles saved" } else { "none yet" }

        $menuOptions = @(
            @("Capture This PC",         "Scan and save all Windows settings to a profile"),
            @("Deploy to This PC",       "Apply a saved profile to this machine"),
            @("View Profile",            "Browse the contents of a saved profile"),
            @("Compare Profiles",        "Diff two profiles side by side"),
            @("Delete Profile",          "Remove a saved profile ($profileInfo)"),
            @("Security & Asset Audit",  "Full security audit with threat detection"),
            @("Settings",                "Configure WinDNA preferences"),
            @("Exit WinDNA",             "Quit the application")
        )

        $choice = Show-Menu -Title "MAIN MENU" -Options $menuOptions -ShowBack $false

        switch ($choice) {
            1 { Invoke-FlowCapture }
            2 { Invoke-FlowDeploy }
            3 { Invoke-FlowViewProfile }
            4 { Invoke-FlowDiff }
            5 { Invoke-FlowDeleteProfile }
            6 { Invoke-FlowSecurityAudit }
            7 { Invoke-FlowSettings }
            { $_ -eq 8 -or $_ -eq 0 } {
                Clear-Host
                Write-Host ""
                Write-Host "  " -NoNewline
                Write-Host ([char]0x1F9EC) -NoNewline
                Write-Host " Thanks for using WinDNA. Your PC's DNA is safe." -ForegroundColor Cyan
                Write-Host ""
                exit 0
            }
        }
    }
}

# ═══════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════
Start-WinDNA
