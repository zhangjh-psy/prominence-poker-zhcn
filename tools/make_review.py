#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成汉化对照审查页（自包含 HTML，可搜索/筛选）"""
import sys
import os
import csv
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from locres_tool import LocRes

CAT = [
    ("LBL_", "标签"), ("BTN_", "按钮"), ("TITLE_", "标题"), ("DESC_", "说明"),
    ("FORMAT_", "格式串"), ("MSG_", "消息"), ("FUE_", "教程"), ("NICKNAME_", "称号"),
    ("PRES_", "预设"), ("DIRECTEDPOPUP", "弹窗"), ("ERROR_", "错误"),
]


def cat_of(key):
    for p, name in CAT:
        if key.startswith(p):
            return name
    return "其他"


def main():
    import config
    src = config.ORIGINAL_LOCRES
    cur = config.GAME_LOCRES
    en = LocRes.load(src)
    zh = LocRes.load(cur)

    # 每个下标挑一个代表键（直接取自 locres 条目）
    rep = {}
    for _, _key, _, _si in en.entries:
        rep.setdefault(_si, _key)

    data = []
    for i in range(len(en.strings)):
        e = en.strings[i].text
        z = zh.strings[i].text
        data.append({
            "i": i,
            "k": rep.get(i, ""),
            "c": cat_of(rep.get(i, "")),
            "e": e,
            "z": z,
            "done": 1 if z != e else 0,
        })

    stats = {}
    for d in data:
        s = stats.setdefault(d["c"], [0, 0, 0])
        s[0] += 1
        s[2] += len(d["e"])
        if d["done"]:
            s[1] += 1

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    stat_html = "".join(
        f'<span class="chip"><b>{k}</b> {v[1]}/{v[0]} 条 · {v[2]:,} 字符</span>'
        for k, v in sorted(stats.items(), key=lambda kv: -kv[1][2])
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prominence Poker 汉化对照审查表</title>
<style>
  :root {{ --bd:#e3e1da; --tx:#26251f; --mu:#6f6d64; --bg:#faf9f5; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--tx);
         font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }}
  header {{ position:sticky; top:0; background:#fff; border-bottom:1px solid var(--bd);
            padding:16px 24px; z-index:9; }}
  h1 {{ margin:0 0 4px; font-size:16px; font-weight:600; }}
  .sub {{ color:var(--mu); font-size:12px; }}
  .chips {{ margin:10px 0 12px; display:flex; flex-wrap:wrap; gap:6px; }}
  .chip {{ background:#f1efe8; border-radius:999px; padding:3px 10px; font-size:12px; color:#444; }}
  .bar {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  input[type=search] {{ flex:1 1 260px; padding:7px 12px; border:1px solid var(--bd);
                        border-radius:8px; font-size:13px; outline:none; background:#fff; }}
  input[type=search]:focus {{ border-color:#8aa6c8; }}
  button {{ padding:6px 12px; border:1px solid var(--bd); background:#fff; border-radius:8px;
            font-size:12px; cursor:pointer; color:#444; }}
  button.on {{ background:#26251f; color:#fff; border-color:#26251f; }}
  table {{ width:100%; border-collapse:collapse; }}
  th,td {{ text-align:left; padding:8px 12px; vertical-align:top;
           border-bottom:1px solid #eeebe3; font-size:13px; }}
  th {{ position:sticky; top:132px; background:#fff; font-weight:600; font-size:12px;
        color:var(--mu); border-bottom:1px solid var(--bd); }}
  td.i {{ color:#a8a69c; font-variant-numeric:tabular-nums; width:56px; }}
  td.k {{ color:#7a7870; font-family:ui-monospace,Consolas,monospace; font-size:11.5px;
          width:190px; word-break:break-all; }}
  td.e {{ color:#5f5e58; width:36%; }}
  td.z {{ width:36%; }}
  td.z.empty {{ color:#c4c1b6; }}
  td.c {{ width:64px; color:#8a887f; font-size:12px; }}
  tr.undone td.z::after {{ content:"未翻译"; color:#c4c1b6; }}
  mark {{ background:#fff2a8; padding:0 1px; }}
  .count {{ margin-left:auto; color:var(--mu); font-size:12px; }}
</style></head>
<body>
<header>
  <h1>Prominence Poker 汉化对照审查表</h1>
  <div class="sub">共 {len(data)} 条唯一字符串 · 已译 {sum(d['done'] for d in data)} 条 ·
    英文合计 {sum(len(d['e']) for d in data):,} 字符</div>
  <div class="chips">{stat_html}</div>
  <div class="bar">
    <input type="search" id="q" placeholder="搜索英文或中文，也可搜键名…">
    <button class="on" data-f="all">全部</button>
    <button data-f="done">已翻译</button>
    <button data-f="todo">未翻译</button>
    <span class="count" id="cnt"></span>
  </div>
</header>
<table>
  <thead><tr><th>#</th><th>键名</th><th>分类</th><th>英文原文</th><th>中文译文</th></tr></thead>
  <tbody id="tb"></tbody>
</table>
<script>
const DATA = {payload};
const tb = document.getElementById('tb'), q = document.getElementById('q'), cnt = document.getElementById('cnt');
let filt = 'all';
function esc(s) {{ return s.replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c])); }}
function hl(s, term) {{
  if (!term) return esc(s);
  const re = new RegExp('(' + term.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
  return esc(s).replace(re, '<mark>$1</mark>');
}}
function render() {{
  const term = q.value.trim();
  const low = term.toLowerCase();
  const out = [];
  let n = 0;
  for (const d of DATA) {{
    if (filt === 'done' && !d.done) continue;
    if (filt === 'todo' && d.done) continue;
    if (low && !(d.e.toLowerCase().includes(low) || d.z.toLowerCase().includes(low)
                 || d.k.toLowerCase().includes(low))) continue;
    n++;
    if (out.length < 600) {{
      out.push('<tr class="' + (d.done ? '' : 'undone') + '">'
        + '<td class="i">' + d.i + '</td>'
        + '<td class="k">' + esc(d.k) + '</td>'
        + '<td class="c">' + d.c + '</td>'
        + '<td class="e">' + hl(d.e.replace(/\\n/g, ' ⏎ '), term) + '</td>'
        + '<td class="z' + (d.done ? '' : ' empty') + '">'
        + (d.done ? hl(d.z.replace(/\\n/g, ' ⏎ '), term) : '') + '</td></tr>');
    }}
  }}
  tb.innerHTML = out.join('');
  cnt.textContent = n + ' 条' + (n > 600 ? '（仅显示前 600 条）' : '');
}}
q.addEventListener('input', render);
document.querySelectorAll('button[data-f]').forEach(b => b.onclick = () => {{
  document.querySelectorAll('button[data-f]').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); filt = b.dataset.f; render();
}});
render();
</script>
</body></html>"""

    out = os.path.join(ROOT, "review", "汉化对照表.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    print(f"已生成: {out}  ({len(html):,} bytes)")
    print("分类统计:")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1][2]):
        print(f"   {k:6s} {v[1]:4d}/{v[0]:4d} 条   英文 {v[2]:6,} 字符")


if __name__ == "__main__":
    main()
