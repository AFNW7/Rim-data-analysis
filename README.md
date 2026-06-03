# Rim Data Analysis

`Rim Data Analysis` 是一个面向《RimWorld》原版数据的 v1.0 桌面分析工具，用于在游戏外创建小人模板、设计攻防测试场景，并对比不同武器、装备、植入体和护甲条件下的输出与承伤结果。

v1.0 当前只支持原版游戏数据分析，暂不支持 Steam 创意工坊 Mod 或其他 Mod 数据分析。

## 适用场景

- 不想在游戏内反复刷高品质装备、搭建测试环境、手动记录随机战斗结果。
- 想快速比较不同武器、品质、特性、特殊装备、植入体和防具条件下的输出差异。
- 想批量生成多个攻击方和防守方组合，并在表格中横向比较结果。
- 想把《RimWorld》的复杂攻防数据放到游戏外软件里，用更直观的方式分析。

## 主要功能

- 人物创建：创建攻击方或防守方模板，配置基础模板、特性、射击等级、武器、衣着、特殊装备和植入体。
- 场景设计：选择攻击方和防守方，设置双方距离和最终命中率修正，支持多选后自动生成多组测试场景。
- 结果对比：以表格方式对比命中率、期望 DPS、理论 DPS、护甲减伤、承伤倍率等指标。
- 数据导入：读取本机《RimWorld》原版 `Data` 目录中的武器、衣着和植入体数据。
- 资源管理：管理已保存的人物和场景，支持删除并同步更新其他页面数据。

## 当前限制

- v1.0 暂不支持 Mod 数据分析。
- 当前发布包是 Windows x64 压缩包，不是安装器。
- 发布包暂未做代码签名，首次运行时 Windows 可能提示安全风险。
- 计算模型以原版规则为目标，但仍属于游戏外分析工具，不是逐 tick 战斗模拟器。

## 下载发布包

普通用户建议从 GitHub Releases 页面下载：

```text
RimDataAnalysis-v1.0.0-windows-x64.zip
```

发布压缩包属于构建产物，不随源码仓库提交。开发者本地构建后，压缩包会生成在：

```text
desktop\app\release\RimDataAnalysis-v1.0.0-windows-x64.zip
```

## 普通用户使用

如果你下载的是 Windows 发布压缩包：

1. 解压 `RimDataAnalysis-v1.0.0-windows-x64.zip`。
2. 进入解压后的文件夹。
3. 双击 `RimDataAnalysis.exe`。

发布包已内置桌面界面和本地计算后端，普通用户不需要安装 Python、Node.js，也不需要打开浏览器或访问 `127.0.0.1:8765`。

## 使用流程

1. 打开“数据导入”页，选择《RimWorld》的 `Data` 目录。
2. 导入成功后，进入“人物创建”页，保存攻击方和防守方模板。
3. 进入“场景设计”页，选择攻防人物，设置距离和最终命中率修正，保存测试场景。
4. 进入“结果对比”页，把一个或多个场景加入对比表，查看并排序对比结果。
5. 在“资源管理”页管理已保存的人物和场景。

Windows 上常见的原版数据目录示例：

```text
E:\SteamLibrary\steamapps\common\RimWorld\Data
```

## 应用数据目录

人物、场景、导入设置和对比结果会自动保存在系统用户数据目录。

Windows 默认位置：

```text
%APPDATA%\RimDataAnalysis
```

如需指定保存位置，可设置环境变量：

```powershell
$env:RIM_DATA_ANALYSIS_APP_STATE_DIR="E:\Your\Custom\AppState"
```

旧版本使用的 `artifacts/app-state` 会在首次启动新版应用时自动迁移。

## 开发运行

源码开发需要同时准备 Python 和 Node.js 环境。

在项目根目录执行：

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]

cd desktop\app
npm install
npm start
```

`npm start` 会构建 Electron 前端并启动桌面窗口，Electron 主进程会自动启动 Python 本地 API。

旧的 `rim-analysis app` Python/Tkinter 桌面入口仍保留用于兼容旧导入路径，但不再作为当前推荐的用户界面。

## 本地构建 Windows 发布包

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows-release.ps1 -Version 1.0.0
```

构建产物：

```text
desktop\app\release\RimDataAnalysis-v1.0.0-windows-x64.zip
```

## 验证命令

运行 Python 测试：

```powershell
python -B -m pytest -q
```

运行 Electron 类型检查：

```powershell
cd desktop\app
npm run typecheck
```

## 项目结构

```text
desktop/app/                      # Electron + TypeScript 桌面端
src/rim_data_analysis/
  web_api.py                       # Electron 调用的本地 JSON API
  combat_engine.py                 # 战斗计算核心
  user_app_*.py                    # 用户应用数据、存储、分析拼装
  vanilla_parser.py                # 原版 XML 数据解析
tests/                             # 单元测试
scripts/build-windows-release.ps1  # Windows 发布包构建脚本
```

## 许可证

本项目使用 MIT License。详见 [LICENSE](LICENSE)。
