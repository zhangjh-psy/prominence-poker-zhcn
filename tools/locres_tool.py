#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UE4 LocRes (version 3 / Optimized_ReplaceDiffWithEntryArray) 读写工具
针对 Prominence Poker 的散装 .locres 文件实测验证。

文件结构
--------
header:
    magic           16 bytes  (GUID)
    version          1 byte   = 3
    stringTableOffset int64   (从文件起始算)
    entryCount       uint32   (所有命名空间条目总和)
    namespaceCount   uint32

namespace 记录 * namespaceCount 次:
    hash        uint32
    nameLen     uint32   (含结尾 \0)
    name        bytes
    entryCount  uint32   (该命名空间的条目数)

entry 记录 (紧跟在所属 namespace 之后) * entryCount 次:
    hash        uint32
    nameLen     uint32   (含结尾 \0)
    name        bytes
    sourceHash  uint32
    strIndex    uint32   (字符串表下标, 不是字节偏移)

string table @ stringTableOffset:
    count       uint32
    count 次:  len int32   (>0: UTF-8, 含 \0 ; <0: UTF-16LE, 长度 = -len 个码元)
               bytes
               refCount uint32
"""
import struct
import sys

MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")


class Str:
    __slots__ = ("text", "enc", "ref")

    def __init__(self, text, enc="u8", ref=1):
        self.text = text      # 不含结尾 \0
        self.enc = enc        # 'u8' | 'u16'
        self.ref = ref


class LocRes:
    def __init__(self):
        self.version = 3
        self.namespaces = []   # [(hash, name, entry_count)]
        self.entries = []      # [(hash, key, source_hash, str_index)]  —— 顺序即文件顺序
        self.strings = []      # [Str]
        self.header_extra = 0

    # ---------- 解析 ----------
    @classmethod
    def load(cls, path):
        d = open(path, "rb").read()
        if d[:16] != MAGIC:
            raise ValueError(f"magic 不匹配: {d[:16].hex()}")
        self = cls()
        self.version = d[16]
        st_off = struct.unpack_from("<q", d, 17)[0]
        entry_cnt = struct.unpack_from("<I", d, 25)[0]
        ns_cnt = struct.unpack_from("<I", d, 29)[0]
        self.header_extra = ns_cnt

        cur = 33
        for _ in range(ns_cnt):
            h = struct.unpack_from("<I", d, cur)[0]; cur += 4
            L = struct.unpack_from("<I", d, cur)[0]; cur += 4
            name = d[cur:cur + L - 1].decode("utf-8"); cur += L
            c = struct.unpack_from("<I", d, cur)[0]; cur += 4
            self.namespaces.append((h, name, c))
            for _ in range(c):
                h2 = struct.unpack_from("<I", d, cur)[0]; cur += 4
                L2 = struct.unpack_from("<I", d, cur)[0]; cur += 4
                key = d[cur:cur + L2 - 1].decode("utf-8"); cur += L2
                sh = struct.unpack_from("<I", d, cur)[0]; cur += 4
                si = struct.unpack_from("<I", d, cur)[0]; cur += 4
                self.entries.append((h2, key, sh, si))

        assert len(self.entries) == entry_cnt, f"条目数 {len(self.entries)} != {entry_cnt}"

        assert cur == st_off, f"条目区结束于 {cur}, 但字符串表声称在 {st_off}"

        n = struct.unpack_from("<I", d, st_off)[0]
        cur = st_off + 4
        for _ in range(n):
            L = struct.unpack_from("<i", d, cur)[0]; cur += 4
            if L >= 0:
                raw = d[cur:cur + L]; cur += L
                self.strings.append(Str(raw[:-1].decode("utf-8"), "u8"))
            else:
                cnt = -L
                raw = d[cur:cur + cnt * 2]; cur += cnt * 2
                self.strings.append(Str(raw[:-2].decode("utf-16-le"), "u16"))
            self.strings[-1].ref = struct.unpack_from("<I", d, cur)[0]; cur += 4
        self._src_path = path
        self._src_size = len(d)
        return self

    # ---------- 序列化 ----------
    def dumps(self):
        # 命名空间记录与其条目交错写出
        out = bytearray()
        out += MAGIC
        out += bytes([self.version])
        out += b"\x00" * 8
        out += struct.pack("<I", len(self.entries))
        out += struct.pack("<I", len(self.namespaces))
        idx = 0
        for h, name, c in self.namespaces:
            b = name.encode("utf-8") + b"\x00"
            out += struct.pack("<II", h, len(b)) + b + struct.pack("<I", c)
            for _ in range(c):
                h2, key, sh, si = self.entries[idx]; idx += 1
                kb = key.encode("utf-8") + b"\x00"
                out += struct.pack("<II", h2, len(kb)) + kb + struct.pack("<II", sh, si)
        st_off = len(out)
        struct.pack_into("<q", out, 17, st_off)

        out += struct.pack("<I", len(self.strings))
        for s in self.strings:
            if s.enc == "u16":
                b = s.text.encode("utf-16-le") + b"\x00\x00"
                out += struct.pack("<i", -(len(b) // 2)) + b
            else:
                b = s.text.encode("utf-8") + b"\x00"
                out += struct.pack("<i", len(b)) + b
            out += struct.pack("<I", s.ref)
        return bytes(out)

    def save(self, path):
        data = self.dumps()
        with open(path, "wb") as f:
            f.write(data)
        return data

    # ---------- 校验 ----------
    def validate(self):
        assert self.dumps() == open(self._src_path, "rb").read(), "序列化未做到字节级还原"
        return True


def main():
    if len(sys.argv) < 3:
        print("用法: locres_tool.py info|verify|export|import <locres> [csv]")
        return
    cmd, path = sys.argv[1], sys.argv[2]
    lr = LocRes.load(path)

    if cmd == "info":
        print(f"version      : {lr.version}")
        print(f"namespaces   : {len(lr.namespaces)}  {[n for _, n, _ in lr.namespaces]}")
        print(f"entries      : {len(lr.entries)}")
        print(f"strings      : {len(lr.strings)}")
        print(f"chars(total) : {sum(len(s.text) for s in lr.strings)}")
    elif cmd == "verify":
        lr.validate()
        print("OK: 解析 + 重新序列化 与原始文件字节级一致")
    elif cmd == "export":
        import csv
        out = sys.argv[3]
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["str_index", "key", "text_en", "text_zh", "refcount", "enc"])
            for h, key, sh, si in lr.entries:
                s = lr.strings[si]
                w.writerow([si, key, s.text.replace("\n", "\\n"), "", s.ref, s.enc])
        print(f"导出 {len(lr.entries)} 行 -> {out}")
    else:
        print("未知命令")


if __name__ == "__main__":
    main()
