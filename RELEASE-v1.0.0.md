# Rim Data Analysis v1.0.0

这是第一个以 Electron 桌面端作为正式用户界面的 v1.0 版本。

## GitHub Release 描述

这是 Rim Data Analysis 的 v1.0 Windows 桌面版本。普通用户下载 `RimDataAnalysis-v1.0.0-windows-x64.zip`，解压后双击 `RimDataAnalysis.exe` 即可使用；发布包已内置 Electron 桌面界面和 Python 本地计算后端，不需要额外安装 Python 或 Node.js。

当前版本面向《RimWorld》原版数据分析，支持人物创建、场景设计、结果对比、数据导入和资源管理。v1.0 暂不支持 Steam 创意工坊 Mod 数据分析，也不是逐 tick 战斗模拟器。

发布附件：

```text
desktop\app\release\RimDataAnalysis-v1.0.0-windows-x64.zip
```

该压缩包体积超过 100MB，不应提交进 Git 源码仓库；发布时应作为 GitHub Release 附件上传。

## 发布内容

- Windows x64 桌面应用压缩包：`RimDataAnalysis-v1.0.0-windows-x64.zip`
- 桌面主程序：`RimDataAnalysis.exe`
- 内置 Python 本地计算后端：`resources/backend/rim-analysis-web-api.exe`
- 用户说明：`README.md`、`USER-GUIDE.txt`

## 构建产物

```text
desktop\app\release\RimDataAnalysis-v1.0.0-windows-x64.zip
```

用户解压后双击 `RimDataAnalysis.exe` 即可运行。发布包已经内置计算后端，普通用户不需要安装 Python 或 Node.js。

## 本地构建

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -Version 1.0.0
```

构建脚本会依次执行：

- 安装 Python 开发依赖。
- 运行 Python 测试。
- 使用 PyInstaller 构建本地 API 后端 exe。
- 安装 Electron 依赖。
- 运行 Electron 类型检查。
- 构建 Electron 桌面应用并压缩为 zip 发布包。

## v1.0 支持范围

- 支持导入《RimWorld》原版 `Data` 目录。
- 支持创建人物模板。
- 支持选择武器、衣着、特性、特殊装备和植入体。
- 支持设计单个或批量攻防场景。
- 支持结果对比表。
- 支持资源管理和删除后跨页面数据同步。

## v1.0 暂不支持

- 暂不支持 Steam 创意工坊 Mod 数据分析。
- 暂不支持 Combat Extended 等重写战斗系统的 Mod。
- 暂不提供逐 tick 战斗模拟。
- 暂未提供安装器和代码签名。

## 首次使用

1. 解压压缩包。
2. 双击 `RimDataAnalysis.exe`。
3. 在“数据导入”页选择 RimWorld 的 `Data` 目录。
4. 依次完成人物创建、场景设计和结果对比。

常见数据目录示例：

```text
E:\SteamLibrary\steamapps\common\RimWorld\Data
```

## 已知限制

- 第一次导入数据需要用户正确选择游戏目录。
- 软件数据默认保存到 `%APPDATA%\RimDataAnalysis`。
- 未签名发布包可能触发 Windows 安全提示。
- 计算结果应视作游戏外分析工具输出。
