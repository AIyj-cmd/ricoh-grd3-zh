# Agent 项目入口

本项目为 **2009 年日版 Ricoh GR DIGITAL III / GRD3** 生成简体中文菜单补丁。不是 2019 年 GR III，也不是通用理光刷机工具。

## 帮机主使用

执行前读取 [操作技能](.agents/skills/ricoh-grd3-zh/SKILL.md)、[README](README.md) 和[恢复边界](docs/recovery.md)。平台入口及可复制提示词见 [Agent 使用指南](docs/agents.md)。

- 默认工作是在电脑上生成、校验文件。工具不检测相机、不读取机身版本、不执行刷写。
- 复用用户在本次会话中已提供的版本和授权，只询问缺失信息；本项目的历史试刷记录不能代替另一台机身的信息。
- 生成文件、复制到存储卡、机身刷写是不同操作。按用户实际授权范围推进，不把本地生成成功说成刷机成功。
- 固定哈希、四字节差异和 EXTD 1.18 限制必须保留。遇到不匹配就停止，不提高版本号或绕过校验。
- `stock/` 是原版升级文件；刷回原版和故障救砖均未经过本项目实机验证。

## 修改项目

补丁实现集中在 `patch_grd3.py`，只用 Python 3.10+ 标准库。开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
python3 -m unittest discover -s tests -v
```

未设置 `GRD3_STOCK` 时，真实固件测试会跳过。Windows 可使用 `py -3`。不把固件、机身备份、照片、设备标识或本机绝对路径提交到仓库。

共享使用流程只维护在 `.agents/skills/ricoh-grd3-zh/SKILL.md`；Claude Code 和 WorkBuddy 的技能文件负责引导读取它。更新入口时检查相对路径，保留完整仓库即可使用，不要求安装全局技能。
