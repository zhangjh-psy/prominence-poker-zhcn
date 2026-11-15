#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汉化质量检查器。

A 结构：占位符数量/顺序、富文本标记、换行、空译文
B 文本：半角标点、省略号、多余空格、残留英文
C 一致：同一原文译法、术语统一
D 排版：长度膨胀（仅报真正可能溢出的）
E 中文规范：括号/引号配对、连续标点、叠字、标点前空格

用法: python qa.py [--verbose]
"""
import sys
import os
import re
import csv
import collections
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from locres_tool import LocRes

ALLOW_EN = {
    "REP", "VR", "PS4", "STEAM", "XBOX", "PLAYSTATION", "PC", "AI", "UTC", "EULA",
    "GFUEL", "CUORI", "WEBMESSAGEROUTER", "ROM", "CONFIG", "T", "SONY", "ID", "AA", "ELO", "SIENE", "UNICODE",
}
PROPER = re.compile(
    r"Sony Interactive Entertainment Network Europe Limited|"
    r"PlayStation™Network|PlayStation™Store|PlayStation®Store|"
    r"Sony Interactive Entertainment America", re.I)
ALLOW_URL = re.compile(r"[a-z0-9.\-]+\.(?:com|net|org)(?:/[a-z0-9\-/]*)?", re.I)
TAG = r"\[(?!Boost\])[A-Za-z]+\]"
MARKUP = {
    "**": r"\*\*", "##": r"##", "&&": r"&&", "$$": r"\$\$", "<<": r"<<",
    ">>": r">>", "[Tag]": TAG, "{Line#}": r"\{Line#[A-Za-z]*\}",
}
HALF_PUNCT = re.compile(r"[\u4e00-\u9fff][,;:!?]|[,;:!?][\u4e00-\u9fff]")


def load_zh():
    zh = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "translation"))):
        if fn.startswith("zh_") and fn.endswith(".py"):
            p = os.path.join(ROOT, "translation", fn)
            spec = importlib.util.spec_from_file_location(fn[:-3], p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            for n in dir(m):
                if n.isupper() and isinstance(getattr(m, n), dict):
                    zh.update(getattr(m, n))
    return zh


def width(s):
    return sum(2 if ord(c) > 0x2000 else 1 for c in s)


def strip_markup(s):
    """去掉标记，但占位符/标签替换成 X，避免删空后产生假的双空格"""
    s = re.sub(r"\{[^}]*\}", "■", s)
    s = re.sub(TAG, "■", s)
    s = s.replace("**", "").replace("##", "").replace("&&", "").replace("$$", "")
    s = s.replace("<<", "").replace(">>", "")
    s = ALLOW_URL.sub("■", s)
    s = PROPER.sub("■", s)
    return s


def main():
    verbose = "--verbose" in sys.argv
    import config
    en = LocRes.load(config.ORIGINAL_LOCRES)
    zhmap = load_zh()
    rep = {}
    for _, _key, _, _si in en.entries:
        rep.setdefault(_si, _key)

    issues = collections.defaultdict(list)
    notes = collections.defaultdict(list)

    for i in range(len(en.strings)):
        e, z, key = en.strings[i].text, zhmap.get(i, ""), rep.get(i, "")

        # A1 占位符数量
        pe = re.findall(r"\{[^}]*\}|%[sd]", e)
        pz = re.findall(r"\{[^}]*\}|%[sd]", z)
        if collections.Counter(pe) != collections.Counter(pz):
            issues["A1 占位符数量不一致"].append((i, key, f"{pe} vs {pz}"))
        elif pe != pz:
            # 中文语序不同属正常；仅当涉及 %s/%d（按位置取值）时才报错
            if any(p.startswith("%") for p in pe):
                issues["A2 位置型占位符顺序被改"].append((i, key, f"{pe} vs {pz}"))
            else:
                notes["A2 {n} 占位符顺序调整（中文语序，正常）"].append((i, key, f"{pe} vs {pz}"))

        for name, pat in MARKUP.items():
            ce, cz = len(re.findall(pat, e)), len(re.findall(pat, z))
            if ce != cz:
                issues[f"A3 标记 {name} 数量不一致"].append((i, key, f"{ce} vs {cz}"))

        ne, nz = e.count("\n"), z.count("\n")
        if ne != nz:
            issues["A4 换行数不一致"].append((i, key, f"{ne} vs {nz}"))

        if e.strip() and not z.strip():
            issues["A5 译文为空"].append((i, key, repr(e[:40])))

        # B 文本
        plain = strip_markup(z)
        if HALF_PUNCT.search(plain):
            issues["B1 中文里的半角标点"].append((i, key, z[:50]))
        if "..." in plain:
            issues["B2 用了三个点而非省略号"].append((i, key, z[:50]))
        pe_plain = strip_markup(e)
        if re.search(r"[ \t]{2,}", plain) and not re.search(r"[ \t]{2,}", pe_plain):
            issues["B3 多余空格"].append((i, key, repr(z[:50])))
        for w in re.findall(r"(?<![A-Za-z0-9])[A-Za-z]{2,}(?![A-Za-z0-9])", plain):
            if w.upper() in ALLOW_EN:
                continue
            issues["B4 残留英文单词"].append((i, key, f"{w} | {z[:40]}"))
            break
        num_e = set(re.findall(r"\d+", strip_markup(e)))
        num_z = set(re.findall(r"\d+", plain))
        if num_e - num_z:
            # 已人工核对的合理转换：12/24 小时制、中文数字、亿/万单位
            MANUAL = {58, 59, 60, 61, 62, 63, 111, 752, 1162, 1258, 1259, 1539}
            bucket = notes if i in MANUAL else issues
            tag = "B6 数字转为中文表达（已核对）" if i in MANUAL else "B6 数字丢失"
            bucket[tag].append((i, key, f"{sorted(num_e - num_z)} | {z[:45]}"))
        if re.search(r"[，。！？：；、][ \t]+[\u4e00-\u9fff]", plain):
            issues["B5 中文标点后多空格"].append((i, key, z[:50]))

        # D 排版：只报真正可能溢出的（宽度差 >= 10 且原文不算长）
        if e.strip() and z.strip():
            we, wz = width(e), width(z)
            if we <= 20 and wz - we >= 10:
                issues["D1 短文本明显变长"].append((i, key, f"{we}->{wz} | {e[:26]} => {z[:26]}"))

        # E 中文规范
        ee, zz = e.rstrip(), z.rstrip()
        if ee and zz:
            if ee.endswith("?") != zz.endswith("？"):
                issues["B7 句末问号不匹配"].append((i, key, f"{ee[-12:]!r} => {zz[-12:]!r}"))
            elif ee.endswith("!") and not zz.endswith(("！", "。", "？")):
                notes["B8 菜单类标签省略感叹号（中文惯例）"].append(
                    (i, key, f"{ee[-12:]!r} => {zz[-12:]!r}"))
        if plain.count("（") != plain.count("）"):
            issues["E1 全角括号不配对"].append((i, key, z[:60]))
        if plain.count("“") != plain.count("”"):
            issues["E2 引号不配对"].append((i, key, z[:60]))
        if re.search(r"[，。：；]{2,}|[！？]{3,}", plain):
            issues["E3 连续标点"].append((i, key, z[:60]))
        if re.search(r"(的的|了了|是是|个个|地地)", plain):
            issues["E4 叠字"].append((i, key, z[:60]))

    # C 一致性
    by_en = collections.defaultdict(set)
    for i in range(len(en.strings)):
        by_en[en.strings[i].text].add(zhmap.get(i, ""))
    for e, zs in by_en.items():
        if len(zs) > 1:
            issues["C1 同一原文译法不一致"].append((0, e[:36], " / ".join(sorted(zs)[:3])))

    joined = "".join(zhmap.values())
    variants = {
        "声望": ["声誉", "名望值"], "筹码": ["筹马"], "现金局": ["环形游戏"],
        "派系": ["阵营", "帮派"], "每日分成": ["每日抽成"], "战利品箱": ["战利品盒"],
        "悬赏": ["赏金任务"], "桌面道具": ["台子道具"],
    }
    for good, bads in variants.items():
        for b in bads:
            if b in joined:
                issues["C2 术语不统一"].append((0, good, b))

    print("=" * 64)
    print(f"检查 {len(en.strings)} 条 / 译文 {len(zhmap)} 条")
    print("=" * 64)
    total = 0
    for cat in sorted(issues):
        lst = issues[cat]
        total += len(lst)
        print(f"\n[{cat}]  {len(lst)} 处")
        for item in (lst if verbose else lst[:6]):
            print("   ", item)
        if not verbose and len(lst) > 6:
            print(f"    … 另有 {len(lst)-6} 处")
    if notes and verbose:
        print("\n--- 以下属正常现象，不计为问题 ---")
        for cat in sorted(notes):
            print(f"[{cat}] {len(notes[cat])} 处")
            for item in notes[cat][:4]:
                print("   ", item)
    print(f"\n合计 {total} 处问题")
    return total


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
