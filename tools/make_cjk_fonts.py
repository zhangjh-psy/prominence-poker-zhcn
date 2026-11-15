#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成含中文的 UI 字体，并替换游戏内各字体族的 .ufont。

思路:
  Noto Sans SC 已在游戏构建中（NotoSansSC-Regular.ufont，CFF/OTTO），
  以其为底，按实际用到的字符子集化，再覆盖到 UI 各字体族的 .ufont。
  路径不变 -> .uexp 里的相对引用依然有效，无需改任何 uasset。

用法:
    python make_cjk_fonts.py [--dry-run]
"""
import sys
import os
import glob
import csv
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

GAME_FONTS = config.GAME_FONTS or config.require_game()
SRC_FONT = os.path.join(GAME_FONTS, "NotoSansSC-Regular.ufont")
SRC_FONT_BOLD = os.path.join(GAME_FONTS, "NotoSansSC-Bold.ufont")
BUILD = os.path.join(ROOT, "build")

BOLD_HINT = ("Bold", "Heavy", "Semi", "XtraBold", "ExtraBold", "CondensedBold")

# 不替换：这些本身已是 CJK / emoji / 其他文字专用的回退字体
SKIP_PREFIX = (
    "NotoSansSC", "NotoSansTC", "NotoSansHK", "NotoSansJP", "NotoSansKR",
    "NotoColorEmoji", "OpenMoji", "NotoKufiArabic", "NotoSansMyanmar",
    "NotoSansThai", "NotoSans-",  # 通用拉丁回退，保留
)


def collect_chars():
    chars = set()
    # 1) 旧式 CSV
    for p in glob.glob(os.path.join(ROOT, "translation", "*.csv")):
        for r in csv.DictReader(open(p, encoding="utf-8-sig")):
            t = (r.get("text_zh") or "").strip()
            if t:
                chars.update(t)
    # 2) zh_*.py 译文模块（主用）
    import importlib.util
    for p in glob.glob(os.path.join(ROOT, "translation", "zh_*.py")):
        spec = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in dir(mod):
            if not name.isupper():
                continue
            d = getattr(mod, name)
            if isinstance(d, dict):
                for v in d.values():
                    chars.update(v)
    # ASCII 可见字符 + 常用中文标点 + 数学/货币符号
    chars.update(chr(c) for c in range(0x20, 0x7F))
    chars.update("　、。〈〉《》「」『』【】〔〕・ー…—–‘’“”·×÷±°％＆＃＠")
    chars.discard("\n")
    return chars


def subset(chars, src=None, out_name="ui_cjk_subset.otf"):
    os.makedirs(BUILD, exist_ok=True)
    charfile = os.path.join(BUILD, "ui_charset.txt")
    with open(charfile, "w", encoding="utf-8") as f:
        f.write("".join(sorted(chars)))
    out = os.path.join(BUILD, out_name)
    cmd = [sys.executable, "-m", "fontTools.subset", src or SRC_FONT,
           f"--text-file={charfile}", f"--output-file={out}",
           "--layout-features=*", "--glyph-names", "--symbol-cmap", "--legacy-cmap"]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main(dry=False):
    chars = collect_chars()
    print(f"字符集: {len(chars)} 个（含 ASCII 与中文标点）")
    sub_reg = subset(chars)
    sub_bold = subset(chars, SRC_FONT_BOLD, "ui_cjk_subset_bold.otf")
    reg = open(sub_reg, "rb").read()
    bold = open(sub_bold, "rb").read()
    print(f"子集字体: 常规 {len(reg):,} B / 粗体 {len(bold):,} B")

    targets = []
    for p in sorted(glob.glob(os.path.join(GAME_FONTS, "*.ufont"))):
        name = os.path.basename(p)
        if name.startswith(SKIP_PREFIX):
            continue
        targets.append((p, name))
    print(f"待替换字体: {len(targets)} 个")

    total_before = total_after = 0
    nb = 0
    for p, name in targets:
        total_before += os.path.getsize(p)
        is_bold = any(h in name for h in BOLD_HINT)
        data = bold if is_bold else reg
        if is_bold:
            nb += 1
        if not dry:
            with open(p, "wb") as f:
                f.write(data)
        total_after += len(data)
    print(f"其中粗体 {nb} 个；体积 {total_before:,} -> {total_after:,} bytes")
    if dry:
        print("(dry-run，未写入)")
    else:
        print("完成")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
