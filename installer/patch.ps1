#Requires -Version 5.1
<#
    Prominence Poker 简体中文汉化 · 安装/还原脚本

    用法：
        patch.ps1                     交互菜单
        patch.ps1 -Action install     直接安装
        patch.ps1 -Action restore     直接还原
        patch.ps1 -Action status      检查状态
        patch.ps1 -GamePath "D:\..."  指定游戏目录

    两种数据来源：
        1) 发布包：同目录下有 payload/（manifest.json + locres + fonts）
        2) 源码包：上层目录有 assets/（Game.locres + 字体子集 + font_targets.txt），
           运行时现场组装，无需预打包
#>
[CmdletBinding()]
param(
    [ValidateSet('menu', 'install', 'restore', 'status')]
    [string]$Action = 'menu',
    [string]$GamePath = '',
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$Root         = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Parent       = Split-Path -Parent $Root
$PayloadDir   = Join-Path $Root 'payload'
$ManifestFile = Join-Path $PayloadDir 'manifest.json'
$BackupName   = '_zhCN_backup'
$GameExe      = 'Prominence-Win64-Shipping'
$ReleaseUrl   = 'https://github.com/zhangjh-psy/prominence-poker-zhcn/releases/latest'

# ---------------- 输出辅助 ----------------
function Write-Title($t) {
    Write-Host ''
    Write-Host ('  ' + $t) -ForegroundColor White
    Write-Host ('  ' + ('-' * 52)) -ForegroundColor DarkGray
}
function Write-Ok($t)   { Write-Host ('  [OK]   ' + $t) -ForegroundColor Green }
function Write-Warn2($t){ Write-Host ('  [注意] ' + $t) -ForegroundColor Yellow }
function Write-Err($t)  { Write-Host ('  [错误] ' + $t) -ForegroundColor Red }
function Write-Info($t) { Write-Host ('         ' + $t) -ForegroundColor Gray }

function Pause-Any {
    if ($Yes) { return }
    Write-Host ''
    Write-Host '  按回车继续…' -ForegroundColor DarkGray
    [void](Read-Host)
}

# ---------------- 清单 ----------------
function New-ManifestFromAssets($assets) {
    $locres  = Join-Path $assets 'Game.locres'
    $targets = Join-Path $assets 'font_targets.txt'
    $reg     = Join-Path $assets 'ui_cjk_subset.otf'
    $bold    = Join-Path $assets 'ui_cjk_subset_bold.otf'

    $list = @()
    $list += [pscustomobject]@{
        source = $locres
        target = 'Prominence/Content/Localization/Game/en/Game.locres'
    }
    foreach ($raw in (Get-Content $targets -Encoding UTF8)) {
        $n = $raw.Trim()
        if (-not $n) { continue }
        if ($n -match 'Bold|Heavy|Semi|XtraBold|ExtraBold') { $src = $bold } else { $src = $reg }
        $list += [pscustomobject]@{ source = $src; target = "Prominence/Content/UI/FONTS/$n" }
    }
    foreach ($f in $list) {
        $f | Add-Member -NotePropertyName size   -NotePropertyValue (Get-Item -LiteralPath $f.source).Length
        $f | Add-Member -NotePropertyName sha256 -NotePropertyValue (Get-FileHash -LiteralPath $f.source -Algorithm SHA256).Hash.ToLower()
    }
    return [pscustomobject]@{
        version             = 'dev'
        sourceMode          = $true
        locres_md5          = (Get-FileHash -LiteralPath $locres -Algorithm MD5).Hash.ToLower()
        original_locres_md5 = ''
        files               = $list
    }
}

function Get-Manifest {
    if (Test-Path $ManifestFile) {
        $m = Get-Content $ManifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($f in $m.files) {
            if (-not ($f.PSObject.Properties.Name -contains 'source')) {
                $f | Add-Member -NotePropertyName source `
                                -NotePropertyValue (Join-Path $PayloadDir $f.payload)
            }
        }
        return $m
    }

    # 源码包模式：用仓库内 assets/ 现场组装
    $assets = Join-Path $Parent 'assets'
    if ((Test-Path (Join-Path $assets 'Game.locres')) -and
        (Test-Path (Join-Path $assets 'font_targets.txt')) -and
        (Test-Path (Join-Path $assets 'ui_cjk_subset.otf'))) {
        return New-ManifestFromAssets $assets
    }

    Write-Host ''
    Write-Err '没有找到补丁数据，无法安装。'
    Write-Host ''
    Write-Host '  如果你是点 GitHub 页面的「Code → Download ZIP」下载的，' -ForegroundColor Yellow
    Write-Host '  得到的是源代码包，里面不含打包好的补丁。' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '  请到这个地址下载 Release 中的 zip：' -ForegroundColor White
    Write-Host "  $ReleaseUrl" -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  解压后双击「一键汉化.bat」。' -ForegroundColor Gray
    Pause-Any
    exit 2
}

# ---------------- 定位游戏 ----------------
function Test-GameDir($dir) {
    if ([string]::IsNullOrWhiteSpace($dir)) { return $false }
    $p = Join-Path $dir 'Prominence\Content\Localization\Game\en\Game.locres'
    return (Test-Path $p)
}

function Find-GamePath {
    $cands = New-Object System.Collections.Generic.List[string]

    try {
        $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath
        if ($steam) {
            $cands.Add($steam)
            $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
            if (Test-Path $vdf) {
                $raw = Get-Content $vdf -Raw -Encoding UTF8
                foreach ($m in [regex]::Matches($raw, '"path"\s+"([^"]+)"')) {
                    $cands.Add(($m.Groups[1].Value -replace '\\\\', '\'))
                }
            }
        }
    } catch { }

    $cands.Add('C:\Program Files (x86)\Steam')
    $cands.Add('C:\Program Files\Steam')
    $cands.Add('D:\Steam')
    $cands.Add('E:\Steam')
    $cands.Add('F:\Steam')
    $cands.Add('F:\youxi')

    foreach ($lib in $cands) {
        $g = Join-Path $lib 'steamapps\common\Prominence Poker'
        if (Test-GameDir $g) { return $g }
    }
    return ''
}

function Ask-GamePath {
    Write-Host ''
    Write-Host '  没有自动找到游戏目录，请手动指定。' -ForegroundColor Yellow
    Write-Host '  提示：Steam 库中右键游戏 → 管理 → 浏览本地文件，复制地址栏路径。' -ForegroundColor Gray
    Write-Host ''
    try {
        Add-Type -AssemblyName System.Windows.Forms | Out-Null
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = '请选择 Prominence Poker 游戏根目录（包含 Prominence 文件夹的那一层）'
        if ($dlg.ShowDialog() -eq 'OK') {
            if (Test-GameDir $dlg.SelectedPath) { return $dlg.SelectedPath }
            Write-Err '该目录下没有找到 Prominence\Content\Localization\Game\en\Game.locres'
        }
    } catch { }

    $manual = Read-Host '  请输入游戏根目录路径'
    if (Test-GameDir $manual) { return $manual }
    return ''
}

function Resolve-Game {
    if ($GamePath -and (Test-GameDir $GamePath)) { return $GamePath }
    if ($GamePath) { Write-Err "指定的目录无效：$GamePath" }
    $found = Find-GamePath
    if ($found) {
        Write-Ok "已找到游戏：$found"
        return $found
    }
    return (Ask-GamePath)
}

function Test-GameRunning {
    $p = Get-Process -Name $GameExe -ErrorAction SilentlyContinue
    return ($null -ne $p)
}

# ---------------- 备份 ----------------
function Get-BackupRoot($game) { return (Join-Path $game $BackupName) }

function Invoke-Backup($game, $manifest) {
    $broot = Get-BackupRoot $game
    $made  = 0
    foreach ($f in $manifest.files) {
        $target = Join-Path $game $f.target
        if (-not (Test-Path $target)) { continue }
        $bpath = Join-Path $broot $f.target
        if (Test-Path $bpath) { continue }
        $bdir = Split-Path -Parent $bpath
        if (-not (Test-Path $bdir)) { New-Item -ItemType Directory -Path $bdir -Force | Out-Null }
        Copy-Item -LiteralPath $target -Destination $bpath -Force
        $made++
    }
    $meta = Join-Path $broot 'backup.json'
    if (-not (Test-Path $meta)) {
        if (-not (Test-Path $broot)) { New-Item -ItemType Directory -Path $broot -Force | Out-Null }
        $obj = [ordered]@{
            created = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            version = $manifest.version
            game    = $game
            files   = @($manifest.files | ForEach-Object { $_.target })
        }
        $obj | ConvertTo-Json -Depth 4 | Set-Content -Path $meta -Encoding UTF8
    }
    return $made
}

# ---------------- 安装 ----------------
function Invoke-Install {
    $manifest = Get-Manifest
    Write-Title ("Prominence Poker 简体中文汉化  v" + $manifest.version)

    if ($manifest.PSObject.Properties.Name -contains 'sourceMode' -and $manifest.sourceMode) {
        Write-Info '运行于源码包模式（使用仓库 assets/ 现场组装）。'
    }

    if (Test-GameRunning) {
        Write-Err '游戏正在运行，请先完全退出游戏（包括后台进程）再安装。'
        Pause-Any
        return $false
    }

    $game = Resolve-Game
    if (-not $game) {
        Write-Err '未能确定游戏目录，安装已取消。'
        Pause-Any
        return $false
    }
    Write-Info "游戏目录：$game"

    # 版本校验
    $lc = Join-Path $game 'Prominence\Content\Localization\Game\en\Game.locres'
    $curMd5 = (Get-FileHash -LiteralPath $lc -Algorithm MD5).Hash.ToLower()
    if ($curMd5 -eq $manifest.locres_md5.ToLower()) {
        Write-Info '检测到已安装本汉化，将执行覆盖重装。'
    } elseif ($manifest.original_locres_md5 -and $curMd5 -ne $manifest.original_locres_md5.ToLower()) {
        Write-Warn2 '当前 Game.locres 与预期版本不一致，可能是游戏已更新或装过其他汉化。'
        Write-Info '继续安装一般没问题，但若游戏新增了文本，新增部分可能不显示中文。'
        if (-not $Yes) {
            $ans = Read-Host '  仍要继续吗？(y/N)'
            if ($ans -notmatch '^(y|Y)') { Write-Info '已取消。'; return $false }
        }
    }

    # 校验补丁文件完整性
    Write-Host ''
    Write-Host '  正在校验补丁文件…' -ForegroundColor DarkGray
    $bad = @()
    foreach ($f in $manifest.files) {
        if (-not (Test-Path $f.source)) { $bad += $f.target; continue }
        $h = (Get-FileHash -LiteralPath $f.source -Algorithm SHA256).Hash.ToLower()
        if ($h -ne $f.sha256.ToLower()) { $bad += $f.target }
    }
    if ($bad.Count -gt 0) {
        Write-Err ("补丁文件校验失败（" + $bad.Count + " 个），文件可能损坏，请重新下载。")
        $bad | Select-Object -First 5 | ForEach-Object { Write-Info $_ }
        Pause-Any
        return $false
    }
    Write-Ok ("补丁文件校验通过（" + $manifest.files.Count + " 个文件）")

    # 备份
    $n = Invoke-Backup $game $manifest
    if ($n -gt 0) { Write-Ok "已备份原始文件 $n 个 → $BackupName" }
    else { Write-Info '原始文件已备份过，跳过。' }

    # 复制
    $ok = 0
    foreach ($f in $manifest.files) {
        $dst  = Join-Path $game $f.target
        $ddir = Split-Path -Parent $dst
        if (-not (Test-Path $ddir)) { New-Item -ItemType Directory -Path $ddir -Force | Out-Null }
        Copy-Item -LiteralPath $f.source -Destination $dst -Force
        $ok++
    }

    $stamp = [ordered]@{
        version   = $manifest.version
        installed = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        game      = $game
        fileCount = $ok
    }
    $stamp | ConvertTo-Json | Set-Content -Path (Join-Path (Get-BackupRoot $game) 'installed.json') -Encoding UTF8

    Write-Host ''
    Write-Ok ("安装完成，共写入 $ok 个文件。")
    Write-Host '  启动游戏即可看到中文界面。' -ForegroundColor Green
    Write-Host '  如需还原英文，再次运行本程序选择「还原英文」。' -ForegroundColor Gray
    Pause-Any
    return $true
}

# ---------------- 还原 ----------------
function Invoke-Restore {
    $manifest = Get-Manifest
    Write-Title '还原英文原版'

    if (Test-GameRunning) {
        Write-Err '游戏正在运行，请先完全退出游戏。'
        Pause-Any
        return $false
    }

    $game = ''
    if ($GamePath) { $game = $GamePath } else { $game = Find-GamePath }
    if (-not $game) { $game = Ask-GamePath }
    if (-not $game) { Write-Err '未能确定游戏目录。'; Pause-Any; return $false }

    $broot = Get-BackupRoot $game
    $meta  = Join-Path $broot 'backup.json'
    if (-not (Test-Path $meta)) {
        Write-Err "没有找到备份（$BackupName），无法还原。"
        Write-Info '如果之前用 Steam「验证文件完整性」还原过，就不需要再执行本操作。'
        Pause-Any
        return $false
    }

    $b = Get-Content $meta -Raw -Encoding UTF8 | ConvertFrom-Json
    $n = 0
    foreach ($rel in $b.files) {
        $src = Join-Path $broot $rel
        $dst = Join-Path $game $rel
        if (Test-Path $src) {
            $ddir = Split-Path -Parent $dst
            if (-not (Test-Path $ddir)) { New-Item -ItemType Directory -Path $ddir -Force | Out-Null }
            Copy-Item -LiteralPath $src -Destination $dst -Force
            $n++
        }
    }
    Write-Ok "已还原 $n 个文件（备份时间：$($b.created)）"
    Write-Host '  游戏已恢复英文。' -ForegroundColor Green
    Pause-Any
    return $true
}

# ---------------- 状态 ----------------
function Invoke-Status {
    $manifest = Get-Manifest
    Write-Title '安装状态'

    $game = ''
    if ($GamePath) { $game = $GamePath } else { $game = Find-GamePath }
    if (-not $game) { Write-Warn2 '未找到游戏目录。'; Pause-Any; return }

    Write-Info "游戏目录：$game"
    $broot = Get-BackupRoot $game
    $inst  = Join-Path $broot 'installed.json'

    if (-not (Test-Path $inst)) {
        $lc = Join-Path $game 'Prominence\Content\Localization\Game\en\Game.locres'
        if (Test-Path $lc) {
            $h = (Get-FileHash -LiteralPath $lc -Algorithm MD5).Hash.ToLower()
            if ($h -eq $manifest.locres_md5.ToLower()) {
                Write-Warn2 '检测到汉化文件，但没有安装记录（可能是手动安装，或备份被删除）。'
                Write-Info '建议重新运行一次「安装汉化」，以生成可还原的备份。'
                Pause-Any
                return
            }
        }
        Write-Warn2 '当前未安装汉化。'
        Pause-Any
        return
    }
    $i = Get-Content $inst -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Ok "已安装汉化 v$($i.version)，时间：$($i.installed)"

    $match = 0
    foreach ($f in $manifest.files) {
        $dst = Join-Path $game $f.target
        if (Test-Path $dst) {
            $h = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLower()
            if ($h -eq $f.sha256.ToLower()) { $match++ }
        }
    }
    Write-Info ("文件匹配：$match / " + $manifest.files.Count)
    if ($match -lt $manifest.files.Count) {
        Write-Warn2 '部分文件与汉化包不一致，可能被游戏更新或 Steam 校验覆盖，建议重新安装。'
    }
    Pause-Any
}

# ---------------- 菜单 ----------------
function Show-Menu {
    while ($true) {
        Clear-Host
        $m = Get-Manifest
        Write-Host ''
        Write-Host '  ╔══════════════════════════════════════════════════╗' -ForegroundColor Cyan
        Write-Host '  ║   Prominence Poker  简体中文汉化补丁              ║' -ForegroundColor Cyan
        Write-Host ("  ║   v" + ([string]$m.version).PadRight(46) + '║') -ForegroundColor Cyan
        Write-Host '  ╚══════════════════════════════════════════════════╝' -ForegroundColor Cyan
        Write-Host ''
        Write-Host '    1  安装汉化'
        Write-Host '    2  还原英文原版'
        Write-Host '    3  检查安装状态'
        Write-Host '    0  退出'
        Write-Host ''
        $c = Read-Host '  请选择'
        switch ($c) {
            '1' { Invoke-Install | Out-Null }
            '2' { Invoke-Restore | Out-Null }
            '3' { Invoke-Status }
            '0' { return }
            default { }
        }
    }
}

switch ($Action) {
    'install' { Invoke-Install | Out-Null }
    'restore' { Invoke-Restore | Out-Null }
    'status'  { Invoke-Status }
    default   { Show-Menu }
}
