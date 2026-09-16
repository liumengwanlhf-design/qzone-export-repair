# qzone-export-repair

An offline, standard-library Python tool for repairing selected defects in legacy HTML exports from [GetQzonehistory](https://github.com/ll0v0ll/GetQzonehistory). It works on an existing export and its local `pic/` folder; it does not log in, make network requests, or fetch data from QQ.

The underlying exporter fixes were merged upstream in [GetQzonehistory PR #21](https://github.com/ll0v0ll/GetQzonehistory/pull/21). This utility is for older exports already stored on disk.

## 修复范围

| 现象 | 脚本实际处理方式 |
| --- | --- |
| `nickname`、`time`、`message` 节点中出现连续的 `tttt...` | 清除这些指定节点中的长 `t` 串 |
| 指向 `qq.com` 的失效图片 | 按导出内容和文件名关键词尝试引用同级 `pic/` 中的图片；找不到时写入占位图，并在 `data-original-src` 保留原 URL |
| `<div>` 闭合不足 | 按 `.post` 边界补齐闭合标签；写入前检查 `<div>` 数量和说说数量 |
| 四种已知的 GBK 误转码注释 | 替换为对应中文注释 |

这不是通用 HTML 修复器。图片匹配依赖相邻约 800 个字符中的关键词和 GetQzonehistory 常见下载文件名；重复、纯图片或文字不具辨识度的内容可能无法正确匹配。

## 使用方法

需要 Python 3.8+，无需安装第三方包。以下命令用 `-X utf8` 启用 Python UTF-8 模式，避免 Windows 旧代码页无法显示状态符号；只更换终端并不能保证 Python 使用 UTF-8。

先预演，确认输出：

```bash
python -X utf8 fix_qzone.py "你的_说说网页版.html"
```

确认后再写回。`--apply` 会覆盖输入 HTML；虽然脚本会检查 `<div>` 平衡和说说数量，仍建议先手动复制一份原文件。

```bash
python -X utf8 fix_qzone.py "你的_说说网页版.html" --apply

# 图片目录不在 HTML 同级时
python -X utf8 fix_qzone.py "你的_说说网页版.html" --pic "某文件夹/pic" --apply
```

默认图片目录为 HTML 同级的 `pic/`。输入文件必须是 UTF-8 编码。

## 测试

仓库中的样例使用虚构用户名和假图片字节，不包含真实导出数据。可运行：

```bash
# PowerShell
$env:PYTHONUTF8=1; python tests/test_fix_qzone.py

# POSIX shell
PYTHONUTF8=1 python tests/test_fix_qzone.py
```

## 隐私

- 所有处理都在本地完成；
- 不要把个人导出文件、图片或登录数据提交到公开仓库或 Issue；
- 本工具只处理已有文件，不能补回没有保存在本地的图片。

## License

GPL-3.0，沿用上游 [GetQzonehistory](https://github.com/ll0v0ll/GetQzonehistory) 的许可证。
