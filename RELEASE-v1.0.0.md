# Rim Data Analysis v1.0.0

这是第一个面向普通用户使用流程整理的 v1.0 版本。

## 发布内容

- Windows 桌面应用：`RimDataAnalysis.exe`
- 用户使用说明：`USER-GUIDE.txt`
- 项目说明：`README.md`

## 本地构建

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -Version 1.0.0
```

构建产物：

```text
dist\release\RimDataAnalysis-v1.0.0-windows.zip
```

## v1.0 支持范围

- 支持导入《RimWorld》原版 `Data` 目录。
- 支持创建人物模板。
- 支持选择武器、衣着、特性、特殊装备和植入体。
- 支持设计单个或批量攻防场景。
- 支持结果对比表和简要结论。
- 支持资源管理、重命名、删除和重复场景清理。

## v1.0 暂不支持

- 暂不支持 Steam 创意工坊 Mod 数据分析。
- 暂不支持 Combat Extended 等重写战斗系统的 Mod。
- 暂不提供逐 tick 战斗模拟。

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
- 计算模型以原版规则为目标，但仍应视作分析工具输出。
