# 让 Agent 帮你使用

本仓库提供 Codex、Claude Code、腾讯 WorkBuddy 的项目级 Skill，以及其他助手可直接读取的 [AGENTS.md](../AGENTS.md)。助手会调用现有 Python 工具核对输入、生成补丁、校验文件，再报告结果。

需要助手能够读取工作目录、运行终端命令，以及 **Python 3.10+**。本项目不需要额外的 API Key、MCP 服务或 Python 第三方依赖；助手本身仍按各产品要求登录和授权。普通网页聊天不能仅凭仓库链接访问你的电脑或 USB 相机。

## 直接复制给助手

```text
请使用 https://github.com/AIyj-cmd/ricoh-grd3-zh 帮我准备理光 GRD3 简体中文补丁。
先将仓库克隆到本地（如果已有工作副本就使用它），读取 AGENTS.md 和
.agents/skills/ricoh-grd3-zh/SKILL.md，并按其中流程执行。
请核对我的实际机型和模块版本，只询问本次会话中尚未提供的信息。
我会提供从理光官网下载的原版固件路径；不要猜测版本或路径。
本次先在电脑上生成并运行 verify，不向存储卡写入或启动机身刷写。
完成后给出输出目录、校验结果和补丁 SHA-256。
```

已经知道信息时，可在后面追加实际值，避免来回询问：

```text
型号及销售地区：填写机身实际型号、是否日版
机身读数：MAIN=…，BKUP=…，MONI=…，EXTD=…，CPU1=…
官方 ZIP / 解压目录的绝对路径：…
电脑上的新输出目录：…
```

不确定的项目保留未知，让助手引导核对。支持的版本组合、风险及官方查询方法见 [README](../README.md)。

## 按助手调用

先获取完整仓库。当前 Agent 入口随 `main` 分支提供；旧版 v0.1.0 Release 工具包没有这些入口。

```bash
git clone https://github.com/AIyj-cmd/ricoh-grd3-zh.git
cd ricoh-grd3-zh
```

也可下载 [main 分支 ZIP](https://github.com/AIyj-cmd/ricoh-grd3-zh/archive/refs/heads/main.zip) 并解压。保留 `.agents`、`.claude`、`.codebuddy` 这些隐藏目录，把包含 `patch_grd3.py` 的目录选为助手的工作目录。

| 助手 | 仓库提供的入口 | 调用方法 |
| --- | --- | --- |
| Codex CLI / IDE | [`.agents/skills/ricoh-grd3-zh/SKILL.md`](../.agents/skills/ricoh-grd3-zh/SKILL.md) | 在仓库内启动，输入 `$ricoh-grd3-zh`，或从 `/skills` 选择 |
| Claude Code | [`CLAUDE.md`](../CLAUDE.md) 和 [`.claude/skills/ricoh-grd3-zh/SKILL.md`](../.claude/skills/ricoh-grd3-zh/SKILL.md) | 在仓库内启动，输入 `/ricoh-grd3-zh` |
| 腾讯 WorkBuddy | [`.codebuddy/skills/ricoh-grd3-zh/SKILL.md`](../.codebuddy/skills/ricoh-grd3-zh/SKILL.md) | 选择仓库为本地工作目录，发送“请使用 ricoh-grd3-zh 技能帮我准备 GRD3 中文补丁” |
| 其他有文件和终端能力的助手 | [AGENTS.md](../AGENTS.md) | 发送上方通用提示词，让助手显式读取入口 |

目录与发现方式依据 [Codex Skills 官方文档](https://learn.chatgpt.com/docs/build-skills)、[Claude Code Skills 官方文档](https://code.claude.com/docs/en/skills)及 [WorkBuddy 项目配置官方文档](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)。Claude 的 `CLAUDE.md` 通过 `@AGENTS.md` 复用项目说明，使用其[官方导入机制](https://code.claude.com/docs/en/memory)。

如果技能没有出现在列表，先确认打开的是完整仓库根目录，再新建该目录下的会话；也可直接要求读取共享 Skill 文件。企业策略或客户端版本可能限制自动发现。本项目提供的是**仓库内调用**，不要只把某个 Skill 子目录复制到全局目录，否则会缺少脚本和共享文档。

## Agent 实际执行什么

在机型、版本和路径确认后，助手调用以下命令，逐条检查退出码：

```bash
python3 patch_grd3.py build "/path/to/gr3-250.zip" "build/grd3-zh" --extd-version 1.18
python3 patch_grd3.py verify "build/grd3-zh"
```

Windows 可以将 `python3` 换为 `py -3` 并使用本机路径。`--extd-version` 是用户从机身读到的版本，工具不会查询相机。输出目录必须尚不存在，且位于电脑上；工具不提供覆盖或跳过校验的选项。

已有文件包只需执行 `verify`，无需重新生成或重新查询机身版本。完整输出结构见 [README](../README.md)，可供程序读取的结果在 `manifest.json`、`SHA256SUMS.txt` 中。退出码：`0` 成功，`1` 校验或读写失败，`2` 参数错误。清单中的机型和版本字段描述目标及传入值，不构成硬件检测结果。

成功交付应包含以下信息：

```text
已在电脑上生成并校验补丁。
输出目录：实际绝对路径
verify：退出码 0
中文 GLAUNCH3 SHA-256：从已校验文件清单读取的值
相机状态：本次未操作相机
```

`patched/` 是中文更新文件，`stock/` 是原版更新文件。原版回退和故障救砖均未经过本项目实机验证。若后续要求协助刷写，助手需按 README 使用已确认的设备信息、目标卡和授权，引导机主完成物理按键操作并等待反馈，不能把本地校验通过说成“已刷机”。

## 维护与验证范围

共享流程只维护在 [Codex 目录下的 Skill](../.agents/skills/ricoh-grd3-zh/SKILL.md)，Claude Code 和 WorkBuddy 入口引用同一文件，避免三份刷写说明各自演变。入口均为普通文本文件，不依赖跨平台符号链接。

本次接入验证包括 Skill 元数据格式、仓库内引用，以及真实官方固件的本地 `build` / `verify` 流程。尚未分别启动三个客户端完成端到端验收；实际自动发现受客户端及配置影响。补丁的实机证据仍是 [1 台 GRD3 的原有试刷记录](testing.md)，新增 Agent 入口不增加机型兼容性证据。
