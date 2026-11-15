#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 translation/zh_*.py 中的译文合并写入 locres。

用法:
    python apply_zh.py <原始locres> <输出locres> [--report]
"""
import sys
import os
import re
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from locres_tool import LocRes

PLACEHOLDER = re.compile(
    r"\{[^}]*\}|%[sd]|\\n|\*\*|##|&&|\$\$|<<|>>|\[(?!Boost\])[A-Za-z]+\]")


def load_all():
    zh = {}
    dup = {}
    tr_dir = os.path.join(ROOT, "translation")
    for fn in sorted(os.listdir(tr_dir)):
        if not (fn.startswith("zh_") and fn.endswith(".py")):
            continue
        path = os.path.join(tr_dir, fn)
        spec = importlib.util.spec_from_file_location(fn[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in dir(mod):
            if not name.isupper():
                continue
            d = getattr(mod, name)
            if not isinstance(d, dict):
                continue
            for k, v in d.items():
                if k in zh and zh[k] != v:
                    dup.setdefault(k, [zh[k]]).append(v)
                zh[k] = v
    return zh, dup


def main():
    src, dst = sys.argv[1], sys.argv[2]
    report = "--report" in sys.argv
    lr = LocRes.load(src)
    zh, dup = load_all()
    print(f"译文条目: {len(zh)}")

    bad_idx = [k for k in zh if not (0 <= k < len(lr.strings))]
    if bad_idx:
        print(f"[错误] 下标越界: {bad_idx[:10]}")

    bad_ph = []
    applied = 0
    for k, v in zh.items():
        if not (0 <= k < len(lr.strings)):
            continue
        en = lr.strings[k].text
        if sorted(PLACEHOLDER.findall(en)) != sorted(PLACEHOLDER.findall(v)):
            bad_ph.append((k, en, v))
            continue
        lr.strings[k].text = v
        lr.strings[k].enc = "u16" if any(ord(c) > 0x7F for c in v) else "u8"
        applied += 1

    if bad_ph:
        print(f"[跳过] {len(bad_ph)} 条占位符不一致:")
        for k, en, v in bad_ph[:8]:
            print(f"   [{k}] {en!r}\n        -> {v!r}")
    if dup:
        print(f"[注意] {len(dup)} 条下标被多个文件定义且译文不同")

    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    data = lr.save(dst)
    total = len(lr.strings)
    print(f"已写入 {applied} / {total} 条，剩余 {total - applied} 条未翻译")
    print(f"输出: {dst}  {len(data):,} bytes")

    if report:
        left = [(i, lr.strings[i].text) for i in range(total)
                if i not in zh and len(lr.strings[i].text) > 0]
        print(f"\n未翻译 {len(left)} 条，字符数合计 {sum(len(t) for _, t in left):,}")
        with open(os.path.join(ROOT, "out", "untranslated.txt"), "w", encoding="utf-8") as f:
            for i, t in left:
                f.write(f"{i}\t{len(t)}\t{t}\n")


if __name__ == "__main__":
    main()
