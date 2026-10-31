# Ricoh GRD3 简体中文补丁

[![Tests](https://github.com/AIyj-cmd/ricoh-grd3-zh/actions/workflows/tests.yml/badge.svg)](https://github.com/AIyj-cmd/ricoh-grd3-zh/actions/workflows/tests.yml)

让日版 **RICOH GR DIGITAL III（GRD3，2009 年 CCD 机型）** 的日语菜单选项显示机身内置的简体中文。**不适用于 2019 年的 GR III、GR IIIx、GR DIGITAL II/IV 或 GXR。**

目前已在 **1 台日版 GRD3** 上试刷成功：中文菜单、RAW＋JPEG 拍摄、回放、普通关机重启通过基本检查。这是实验性项目，尚未验证故障后的救砖恢复，也未遍历全部菜单和拍摄模式。修改固件可能导致相机无法启动，需要维修；请先读完本页和[恢复边界](docs/recovery.md)。

仓库提供 Python 补丁工具和研究记录。原版固件由使用者从[理光官网下载](https://www.ricoh-imaging.co.jp/english/r_dc/download/firmware/grd3/)，在自己的电脑上生成补丁。仓库及 Release 均不包含理光固件、机身 NAND 备份或照片。

## 效果与改动

- 将原日语槽指向机身已有的简体中文资源；英文槽保持原样。
- 主程序只改 **4 个字节**：2 个语言指针字节、2 个校验值字节。
- 版本号保持 **2.50**，不重写 EXTD 资源，不修改机身地区标记。
- 语言 ID 仍是日语，个别布局、日期表示或固定文本可能保留日文行为。

这是替换日语槽的显示内容，不是解锁完整语言列表。若当前选择 English，刷入后仍会显示英文；请切换到原日语对应的选项。

## 已验证的机身

| 项目 | 本次实机版本 |
| --- | --- |
| 型号 | 日版 GR DIGITAL III / GRD3 |
| MAIN | 2.50 |
| BKUP | 1.00 |
| MONI | 1.00 |
| EXTD | 1.18 |
| CPU1 | 1.00 |

**以这组配置为当前测试范围。其他版本请先停止，不要修改脚本里的校验值强行运行。** 若 MAIN 低于 2.50，应先按理光说明使用官方固件升级，再检查模块版本。

查询版本：关机后按住 **下方向／微距（花朵）键**，再长按 **回放 ▶** 约 2–3 秒。更新固件用的是 **上方向键**，两者不要混淆。参见[理光 GRD3 更新说明](https://www.ricoh-imaging.co.jp/english/r_dc/download/firmware/docs/grd3_fwup_en.pdf)。

## 在电脑上生成

需要 **Python 3.10 或以上**，无需安装第三方依赖。支持 Windows、macOS、Linux。

1. 下载本仓库的 [Release](https://github.com/AIyj-cmd/ricoh-grd3-zh/releases) 源码工具包并解压，或克隆仓库。
2. 从[理光 GRD3 官方页面](https://www.ricoh-imaging.co.jp/english/r_dc/download/firmware/grd3/)阅读下载条款并获取 **`gr3-250.zip`**。不要下载现代 GR III 的固件。
3. 在工具所在目录打开终端，执行以下命令。输入也可以是包含 `GLAUNCH3`、`GLAUNCH8` 的官方解压目录。

macOS / Linux：

```bash
python3 patch_grd3.py build "/path/to/gr3-250.zip" "build/grd3-zh" --extd-version 1.18
python3 patch_grd3.py verify "build/grd3-zh"
```

Windows（PowerShell）：

```powershell
py -3 patch_grd3.py build "C:\Downloads\gr3-250.zip" "build\grd3-zh" --extd-version 1.18
py -3 patch_grd3.py verify "build\grd3-zh"
```

`--extd-version 1.18` 是你从相机屏幕读到的版本，**工具不会读取相机，也不能核实另一台机身中的资源内容**。版本相同也不等于已验证所有机身。

工具会检查输入文件的长度、SHA-256、主程序头和校验和，再确认生成结果与本次试刷文件完全相同。错误版本、损坏文件、重复输入或已有输出目录都会报错；没有跳过校验的选项。它不会联网下载或自动给相机刷写。

生成目录如下：

```text
build/grd3-zh/
├── patched/
│   ├── GLAUNCH3       # 中文补丁
│   └── GLAUNCH8       # 未修改的官方配套文件
├── stock/
│   ├── GLAUNCH3       # 原版主程序
│   └── GLAUNCH8       # 原版配套文件
├── manifest.json
└── SHA256SUMS.txt
```

`stock/` 是原版回退文件，**不是已经验证的救砖包**。生成文件请放在电脑上，确认后再手动复制到存储卡。

## 刷入与检查

以下是本机成功使用的流程，请同时核对[官方更新说明](https://www.ricoh-imaging.co.jp/english/r_dc/download/firmware/docs/grd3_fwup_en.pdf)。

1. 备份卡上照片，充满电池。使用相机能正常读写的存储卡；如需格式化，务必先备份。
2. 只把 **`patched/` 内的 `GLAUNCH3`、`GLAUNCH8` 两个文件**复制到存储卡根目录，替换卡上已有的同名升级文件。不要混入其他固件或调试脚本。
3. 安全弹出存储卡／相机，拔掉 USB，关闭相机。
4. 按住 **上方向 ↑**，再长按 **回放 ▶** 约 2–3 秒。
5. 确认是更新界面后，选择 **はい／Yes**，按 **MENU/OK**。本机接受了 **2.50 → 2.50** 的更新；不要为绕过提示擅自提高版本号。
6. 保持供电，等待完成并自动重启，期间不要拔电池或卡。若报错或无法进入更新界面，停止操作并记录原文，不反复强行更新。
7. 检查中文菜单，试拍 RAW＋JPEG、回放，并普通关机再开机。通过后删除卡上的 `GLAUNCH3`、`GLAUNCH8`，保留电脑上的原版和补丁包。

如果显示“错误的改写文件”，不要跳过工具校验。检查型号、完整文件和复制结果。若刷入后仍是英文，先查看当前语言选项。

## 版本与校验

| 文件 | SHA-256 |
| --- | --- |
| 官方 GLAUNCH3 | `e8ec9488eab4fcf7664568ad046eca5abc796d965499a5e99a1f6dd5718dbfbd` |
| 中文 GLAUNCH3 | `2b71668028999022828ffe36d910df10b1cbbc36d1004feed6f837e4e8875236` |
| 官方 GLAUNCH8（保持不变） | `6515c49f0b43a99af3546801d69290a6c4c947e141a209c2542c2d38481cf843` |

这是工具 **v0.1.0**；相机固件版本仍是 **2.50**。

## 证据、贡献与许可

- [本机试刷记录与未测试项目](docs/testing.md)
- [指针、校验算法与资源分析](docs/technical.md)
- [正常回退与故障恢复的区别](docs/recovery.md)
- [开发测试与反馈规范](CONTRIBUTING.md)

补丁工具及原创说明采用 [MIT License](LICENSE)。理光固件的权利归原权利人所有，不属于本项目 MIT 许可范围。本项目与理光官方无关联。

研究过程中参考了 [siususiusiusu/gxr-firmware-mods](https://github.com/siususiusiusu/gxr-firmware-mods) 对理光固件结构及语言资源的分析；本项目的偏移、校验和输出均在 GRD3 文件上单独核实。GXR 的测试结果不作为 GRD3 的兼容性或恢复证明。

## English overview

This experimental, standard-library-only Python tool redirects the Japanese menu slot to the built-in Simplified Chinese resources on the **2009 Ricoh GR DIGITAL III**, not the 2019 GR III. One Japanese-market camera with MAIN 2.50 / EXTD 1.18 passed basic shooting, playback and reboot checks. Only four bytes change, including the checksum. Firmware is not distributed: supply Ricoh's original 2.50 ZIP locally. Exact input and output hashes are enforced. No unbrick procedure has been verified.
