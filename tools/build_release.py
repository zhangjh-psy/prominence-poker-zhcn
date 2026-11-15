#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包发布版。生成：
    dist/ProminencePoker-zhCN-v<版本>/
        ├─ 一键汉化.bat
        ├─ install.bat
        ├─ patch.ps1
        ├─ README.txt
        ├─ LICENSES/OFL.txt
        └─ payload/
             ├─ Game.locres
             ├─ fonts/*.ufont
             └─ manifest.json
    dist/ProminencePoker-zhCN-v<版本>.zip

用法: python build_release.py [版本号]
"""
import os
import sys
import json
import shutil
import hashlib
import zipfile
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
NAME = "ProminencePoker-zhCN"
FOLDER = f"{NAME}-v{VERSION}"

sys.path.insert(0, HERE)
import config  # noqa: E402

GAME = config.GAME_DIR
GAME_FONTS = config.GAME_FONTS
# 优先用仓库内已构建的产物（CI 无游戏环境也能打包）
_ASSET_LOCRES = os.path.join(ROOT, "assets", "Game.locres")
BUILT_LOCRES = _ASSET_LOCRES if os.path.exists(_ASSET_LOCRES) else config.BUILD_LOCRES
ORIGINAL_LOCRES = config.ORIGINAL_LOCRES
ORIGINAL_MD5 = "1719eb766ca30a7d625ad3f138b8d84f"

# 与 make_cjk_fonts.py 保持一致：排除本身已是 CJK / emoji / 其他文字的回退字体
SKIP_PREFIX = (
    "NotoSansSC", "NotoSansTC", "NotoSansHK", "NotoSansJP", "NotoSansKR",
    "NotoColorEmoji", "OpenMoji", "NotoKufiArabic", "NotoSansMyanmar",
    "NotoSansThai", "NotoSans-",
)

README_TXT = """Prominence Poker 简体中文汉化补丁 v{ver}
========================================

【怎么用】
  1. 先完全退出游戏（任务管理器里也别留着 Prominence-Win64-Shipping.exe）
  2. 双击「一键汉化.bat」
  3. 菜单里选 1（安装汉化），等它跑完
  4. 启动游戏，界面就是中文了

【怎么还原】
  再次运行「一键汉化.bat」，选 2（还原英文原版）。
  安装时会自动把原始文件备份到游戏目录下的 _zhCN_backup 文件夹。

【游戏更新了怎么办】
  Steam 更新游戏后，汉化会被覆盖或出现部分英文。
  重新运行一次「一键汉化.bat」选 1 即可。
  如果更新后出现错位或新文本不显示，说明游戏改动较大，请到项目主页下载新版补丁。

【Steam 验证完整性之后】
  同理会恢复英文，重新安装一次汉化即可。

【装不上 / 提示找不到游戏】
  说明游戏没装在默认位置。
  可以把游戏目录手动告诉程序：运行时它会弹出选择框；
  也可以在命令行执行：
      powershell -ExecutionPolicy Bypass -File patch.ps1 -GamePath "D:\\你的\\Prominence Poker"

【注意】
  · 本补丁只替换文本与字体文件，不修改游戏逻辑，不含任何作弊功能。
  · 修改客户端文件可能违反游戏用户协议，请自行判断并承担风险。
  · 本补丁为民间汉化，非官方出品，与 Pipeworks Studios / 505 Games 无关。

项目主页 / 问题反馈：见下载页说明
"""


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    if not os.path.exists(BUILT_LOCRES):
        sys.exit("缺少 build/Game.locres，请先运行 tools/apply_zh.py")

    dist = os.path.join(ROOT, "dist")
    out = os.path.join(dist, FOLDER)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "payload", "fonts"), exist_ok=True)
    os.makedirs(os.path.join(out, "LICENSES"), exist_ok=True)

    # ---- 载荷：locres ----
    shutil.copy2(BUILT_LOCRES, os.path.join(out, "payload", "Game.locres"))

    files = []
    files.append({
        "payload": "Game.locres",
        "target": "Prominence/Content/Localization/Game/en/Game.locres",
        "size": os.path.getsize(BUILT_LOCRES),
        "sha256": sha256(BUILT_LOCRES),
    })

    # ---- 载荷：字体 ----
    # 优先用仓库内 assets/ 的子集（无需安装游戏即可打包，CI 可用）
    reg  = os.path.join(ROOT, "assets", "ui_cjk_subset.otf")
    bold = os.path.join(ROOT, "assets", "ui_cjk_subset_bold.otf")
    targets_txt = os.path.join(ROOT, "assets", "font_targets.txt")
    BOLD_HINT = ("Bold", "Heavy", "Semi", "XtraBold", "ExtraBold", "CondensedBold")

    if os.path.exists(reg) and os.path.exists(bold) and os.path.exists(targets_txt):
        names = [l.strip() for l in open(targets_txt, encoding="utf-8") if l.strip()]
        for f in names:
            src = bold if any(h in f for h in BOLD_HINT) else reg
            dst = os.path.join(out, "payload", "fonts", f)
            shutil.copy2(src, dst)
            files.append({
                "payload": f"fonts/{f}",
                "target": f"Prominence/Content/UI/FONTS/{f}",
                "size": os.path.getsize(dst),
                "sha256": sha256(dst),
            })
        fonts = names
    else:
        # 回退：直接从本机游戏目录取（需已装游戏）
        config.require_game()
        fonts = sorted(f for f in os.listdir(GAME_FONTS)
                       if f.endswith(".ufont") and not f.startswith(SKIP_PREFIX))
        for f in fonts:
            src = os.path.join(GAME_FONTS, f)
            shutil.copy2(src, os.path.join(out, "payload", "fonts", f))
            files.append({
                "payload": f"fonts/{f}",
                "target": f"Prominence/Content/UI/FONTS/{f}",
                "size": os.path.getsize(src),
                "sha256": sha256(src),
            })

    # ---- 清单 ----
    manifest = {
        "name": "Prominence Poker 简体中文汉化",
        "version": VERSION,
        "game": "Prominence Poker",
        "appid": 384180,
        "built": datetime.date.today().isoformat(),
        "locres_md5": md5(BUILT_LOCRES),
        "original_locres_md5": ORIGINAL_MD5,
        "files": files,
    }
    with open(os.path.join(out, "payload", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # ---- 安装器 ----
    for f in ("一键汉化.bat", "install.bat", "patch.ps1"):
        shutil.copy2(os.path.join(ROOT, "installer", f), os.path.join(out, f))

    with open(os.path.join(out, "README.txt"), "w", encoding="utf-8-sig") as f:
        f.write(README_TXT.format(ver=VERSION))

    ofl = os.path.join(ROOT, "LICENSES", "OFL.txt")
    if os.path.exists(ofl):
        shutil.copy2(ofl, os.path.join(out, "LICENSES", "OFL.txt"))

    # ---- 压缩 ----
    zip_path = os.path.join(dist, f"{FOLDER}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, names in os.walk(out):
            for n in names:
                full = os.path.join(root, n)
                rel = os.path.relpath(full, out)
                z.write(full, os.path.join(FOLDER, rel))

    total = sum(f["size"] for f in files)
    print(f"版本      : {VERSION}")
    print(f"文件数    : {len(files)}（1 个文本 + {len(fonts)} 个字体）")
    print(f"原始大小  : {total/1024/1024:.1f} MB")
    print(f"目录      : {out}")
    print(f"压缩包    : {zip_path}")
    print(f"压缩后    : {os.path.getsize(zip_path)/1024/1024:.1f} MB")
    print(f"zip SHA256: {sha256(zip_path)}")


if __name__ == "__main__":
    main()
