# 开发与反馈

本项目仅使用 Python 3.10+ 标准库。主要文件为 `patch_grd3.py`，固定哈希和偏移在文件开头定义。

## 单元测试

```bash
python3 -m unittest discover -s tests -v
```

CI 在 Linux、macOS 和 Windows 运行合成数据测试，不下载理光固件。没有 `GRD3_STOCK` 时，真实固件集成测试会明确跳过。

## 本地真实固件集成测试

先自行从理光官网下载原版文件，随后：

```bash
GRD3_STOCK="/path/to/gr3-250.zip" python3 -m unittest discover -s tests -v
```

PowerShell：

```powershell
$env:GRD3_STOCK = "C:\Downloads\gr3-250.zip"
py -3 -m unittest discover -s tests -v
```

集成测试检查生成哈希、精确四字节差异、原版配套文件保留、输入拒绝和输出篡改检测。它们使用临时目录，不操作相机。

## 提交内容

- 不提交固件文件、NAND/资源区转储、FAT 表、照片、校准参数或设备标识。
- 新增机型或版本必须作为独立研究处理，不删除现有哈希限制来“支持”未知输入。
- 新增测试结果注明实机数量、模块版本、实际完成的检查和未测试部分。
- 不把“正常升级成功”“能刷回原版”和“无法开机后的恢复成功”混为一谈。
- 变更补丁输出时，同步更新预期哈希、字节差异、技术说明及测试证据；不能沿用旧实机成功记录。

提交问题时请只附必要错误原文或去除个人信息的截图，不上传私有备份。
