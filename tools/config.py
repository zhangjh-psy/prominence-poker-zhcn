#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径解析。优先读环境变量，其次探测常见 Steam 安装位置。

    PROMINENCE_DIR  游戏根目录（含 Prominence 子文件夹的那一层）

贡献者如果没有把游戏装在默认位置：
    set PROMINENCE_DIR=D:\\Steam\\steamapps\\common\\Prominence Poker
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_COMMON = [
    r"D:\steam\steamapps\common\Prominence Poker",
    r"C:\Program Files (x86)\Steam\steamapps\common\Prominence Poker",
    r"C:\Program Files\Steam\steamapps\common\Prominence Poker",
    r"E:\Steam\steamapps\common\Prominence Poker",
    r"F:\Steam\steamapps\common\Prominence Poker",
]


def _find_game():
    env = os.environ.get("PROMINENCE_DIR", "").strip('"')
    if env and _valid(env):
        return env
    for c in _COMMON:
        if _valid(c):
            return c
    return ""


def _valid(p):
    return os.path.isfile(os.path.join(
        p, "Prominence", "Content", "Localization", "Game", "en", "Game.locres"))


GAME_DIR = _find_game()
GAME_LOCRES = (os.path.join(GAME_DIR, "Prominence", "Content", "Localization",
                            "Game", "en", "Game.locres") if GAME_DIR else "")
GAME_FONTS = (os.path.join(GAME_DIR, "Prominence", "Content", "UI", "FONTS")
              if GAME_DIR else "")

# 原始英文备份优先（用于对比/回滚），没有就用游戏里的当前文件
_BAK = os.path.join(ROOT, "backup", "Localization_original", "Game", "en", "Game.locres")
ORIGINAL_LOCRES = _BAK if os.path.isfile(_BAK) else GAME_LOCRES

BUILD_LOCRES = os.path.join(ROOT, "build", "Game.locres")
TRANSLATION_DIR = os.path.join(ROOT, "translation")


def require_game():
    if not GAME_DIR:
        raise SystemExit(
            "未找到游戏目录。请设置环境变量 PROMINENCE_DIR 指向游戏根目录，例如：\n"
            '  set PROMINENCE_DIR=D:\\steam\\steamapps\\common\\Prominence Poker'
        )
    return GAME_DIR
