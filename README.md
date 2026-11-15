# Prominence Poker 简体中文汉化

> Steam 免费德州扑克游戏 [Prominence Poker](https://store.steampowered.com/app/384180/)（AppID 384180）的民间简体中文汉化补丁。
>
> 官方只提供英/法/德/意/西五种语言，本项目补上中文。

**1550 / 1550 条文本全部译完，含 244 条规则说明、198 段更新公告、全部 UI 与教程。**

---

## 给玩家：一键安装

1. 完全退出游戏（任务管理器里也确认没有 `Prominence-Win64-Shipping.exe`）
2. 解压后双击 **`一键汉化.bat`**
3. 选 `1` 安装汉化
4. 启动游戏

还原英文：再次运行，选 `2`。安装时原始文件会自动备份到游戏目录的 `_zhCN_backup`。

<details>
<summary>装不上 / 找不到游戏 / 其他问题</summary>

**提示找不到游戏目录**
游戏不在默认位置时，程序会弹窗让你手动选择，也可以命令行指定：

```bat
powershell -ExecutionPolicy Bypass -File patch.ps1 -GamePath "D:\你的路径\Prominence Poker"
```

**游戏更新后变成部分英文**
重新安装一次即可。若更新幅度大导致文本错位，请到 Releases 下载新版补丁。

**用过 Steam「验证文件完整性」**
会把文件还原成英文，重新安装一次汉化。

**杀毒软件报警**
安装脚本是明文 PowerShell（`patch.ps1`），可以直接打开审阅。个别杀软对 `-ExecutionPolicy Bypass` 敏感，属正常现象。

**装完字体变成方框**
说明字体文件没写入成功，通常是游戏没退干净。退出游戏后重装。
</details>

---

## 技术要点

这个游戏的汉化难度**远低于**一般 UE4 游戏，原因值得记下来：

| 项目 | 情况 |
|---|---|
| 引擎 | Unreal Engine 4 |
| 资源打包 | **完全不打包**，全部是散装 `.uasset` / `.uexp` / `.ufont` |
| 文本位置 | `Prominence/Content/Localization/Game/en/Game.locres` |
| 格式 | UE4 LocRes **v3**，明文，无加密、无压缩、无签名 |
| 反作弊 | 未发现 EasyAntiCheat / BattlEye |
| 字体 | 构建内自带 `NotoSansSC`，但 UI 主字体族缺中文字形 |

因为不打包，**不需要拆 pak、不需要 AES 密钥、不需要重打包**，直接替换 locres 即生效。

### 两个关键坑

**1. 编码必须 UTF-16**

UE 的 `FString` 序列化规则是「纯 ASCII 用正长度(ANSI)，含非 ASCII 用负长度(UTF-16LE)」。如果把中文按 UTF-8 正长度写入，游戏会逐字节当成 ANSI 字符，屏幕上会出现**和字节数一样多的问号**（4 个汉字 → 12 个 `?`）。

**2. 字体是子集，新增汉字必须重建**

补丁里的字体是从游戏自带 Noto Sans SC 裁出的子集（1307 字形 / 343 KB）。如果新增译文用到了字库里没有的字，就会出现方框。所以改完译文必须重跑 `tools/make_cjk_fonts.py`。

### LocRes v3 结构（实测）

```
header:
  magic             16 B
  version            1 B  (=3)
  stringTableOffset int64
  entryCount       uint32
  namespaceCount   uint32
每个命名空间（与条目交错存放）：
  hash uint32 | nameLen uint32 | name | entryCount uint32
  其条目 × N：
    hash uint32 | nameLen uint32 | name | sourceHash uint32 | strIndex uint32
字符串表（文件末尾）：
  count uint32
  × N：[len int32][bytes][refCount uint32]     len>0: UTF-8；len<0: UTF-16LE
```

**条目按「字符串表下标」引用，不是字节偏移**——所以译文长度可以任意变化，不需要回填任何指针。

---

## 给开发者：构建自己的汉化

```bash
# 0. 需要 Python 3.9+，游戏装在默认位置（否则设 PROMINENCE_DIR）
set PROMINENCE_DIR=D:\steam\steamapps\common\Prominence Poker

# 1. 从游戏当前 locres 重建（改完 translation/ 后执行）
python tools/apply_zh.py backup/Localization_original/Game/en/Game.locres build/Game.locres --report

# 2. 按译文用字重新生成字体子集（新增汉字后必须做）
python tools/make_cjk_fonts.py

# 3. 质检（应输出 0 处问题）
python tools/qa.py

# 4. 打包发布
python tools/build_release.py 1.0.1
```

输出在 `dist/ProminencePoker-zhCN-v1.0.1.zip`。

### 目录结构

```
translation/        译文（唯一真相源）
  zh_btn.py         ┐
  zh_title.py       │ 按 UI 分类拆分的字典，键 = 字符串表下标
  zh_lbl1/2.py      │
  zh_fue.py         │
  zh_msg.py         │
  zh_desc1/2.py     │
  zh_notes.py       ┘
  术语表.md          术语决策与理由
tools/
  locres_tool.py    LocRes 读写（info / verify / export）
  apply_zh.py       合并译文写入 locres，带富文本标记校验
  make_cjk_fonts.py 生成并替换字体子集
  qa.py             17 项质量检查
  make_review.py    生成对照审查页
  build_release.py  打包安装器
  config.py         路径解析
installer/          安装器（bat + ps1）
docs/               技术报告
LICENSES/           OFL 字体许可
```

### 质检做了什么

`tools/qa.py` 覆盖 17 项：

- **结构**：占位符数量/顺序、8 类富文本标记（`**` `##` `&&` `$$` `<<` `>>` `[Tag]` `{Line#}`）、换行数、空译文
- **文本**：半角标点、三个点代替省略号、多余空格、残留英文
- **语义**：数字丢失、句末语气
- **一致**：同一原文译法、术语统一
- **排版**：短文本长度膨胀
- **中文规范**：括号/引号配对、连续标点、叠字

写译文时曾靠它抓出 7 处漏掉 `[Bet]` 按键图标、丢失加粗标记的问题——这类错误在游戏里会直接表现为「按键提示消失」，肉眼极难发现。

### 贡献翻译

1. 在 `translation/zh_*.py` 里改对应下标的值（下标见 `out/en_full.csv`，或运行 `python tools/make_review.py` 后打开 `review/汉化对照表.html` 查找）
2. 跑一遍 `apply_zh.py` 和 `qa.py`
3. 若用到新汉字，**务必**跑 `make_cjk_fonts.py`
4. 提交 PR

**请先读 `translation/术语表.md`**，牌型与系统名词都有既定译法（`Ring Game`→现金局、`Full House`→葫芦、`Muck`→埋牌……），混用会破坏一致性。

---

## 翻译说明

- 1550 条唯一字符串，1718 个键（有复用），英文 78,082 字符 → 中文 26,159 字符
- 玩家昵称、聊天、服务器推送消息由服务端下发，无法汉化
- 图片里烘焙的英文（Logo、部分宣传图）未处理
- 更新公告是 2021–2025 的完整更新日志，含大量工程术语，已全译

---

## 免责声明

- 本项目为**非官方**民间汉化，与 Pipeworks Studios、505 Games、Jagex 无关
- 补丁仅替换文本与字体文件，**不修改游戏逻辑，不含任何作弊功能**
- 修改客户端文件可能违反游戏用户协议，使用风险自负
- 仓库**不包含**游戏本体、美术资源、音频资源
- 请支持正版（本作为免费游戏，本体可直接在 Steam 获取）

## 许可

| 内容 | 许可 |
|---|---|
| 代码（`tools/`、`installer/`） | MIT |
| 译文（`translation/`） | CC BY-NC-SA 4.0 |
| 字体（`payload/fonts/`） | SIL Open Font License 1.1 |

字体基于游戏自带的 Noto Sans SC（Google，OFL 1.1）做子集裁剪，许可全文见 `LICENSES/OFL.txt`。
