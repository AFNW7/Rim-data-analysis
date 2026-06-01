# Rim Data Analysis

`Rim Data Analysis` 是一个面向《RimWorld》的 v1.0 桌面分析工具，用于在游戏外创建小人模板、设计攻防测试场景，并对比不同武器、装备和护甲条件下的输出与承伤结果。

v1.0 只支持原版游戏数据分析，暂不支持 Steam 创意工坊 Mod 或其他 Mod 数据分析。

## 适用场景

- 不想在游戏内反复刷高品质装备、搭建测试环境、手动记录随机测试结果。
- 想快速比较不同武器、品质、特性、植入体和防具条件下的输出差异。
- 想批量生成多个攻击方和防守方组合，并在表格中横向比较。
- 想把《RimWorld》的复杂攻防数据放到游戏外软件里分析。

## 主要功能

- 人物创建：创建攻击方或防守方模板，配置基础模板、特性、射击等级、武器、衣着、特殊装备和植入体。
- 场景设计：选择攻击方和防守方，设置双方距离和最终命中率；支持多选后自动生成多组测试场景。
- 结果对比：以表格方式对比命中率、期望 DPS、理论 DPS、护甲减伤、承伤倍率等指标，并给出简要结论。
- 数据导入：读取本机《RimWorld》原版 `Data` 目录中的武器、衣着和植入体数据。
- 资源管理：管理已保存的人物和场景，支持载入、重命名、删除和重复场景清理。

## 当前限制

- v1.0 暂不支持 Mod 数据分析。
- 需要本机安装 Python 3.11 或更高版本。
- 当前还没有 Windows `.exe` 安装包。
- 计算模型以原版规则为目标，但仍属于游戏外分析模型，不是逐 tick 战斗模拟器。

## 安装

如果你下载的是 Windows 发布压缩包：

1. 解压 `RimDataAnalysis-v1.0.0-windows.zip`。
2. 双击 `RimDataAnalysis.exe`。

如果你下载的是源码，再按下面方式安装。

在项目根目录执行：

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

如果你要运行测试或参与开发，安装开发依赖：

```powershell
python -m pip install -e .[dev]
```

## 启动

源码安装后的桌面启动方式：

```powershell
rim-analysis app
```

如果 PowerShell 提示找不到 `rim-analysis`，请确认已经在项目根目录激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

也可以直接运行：

```powershell
.\.venv\Scripts\rim-analysis.exe app
```

## 使用流程

1. 打开“数据导入”页，选择或自动检测《RimWorld》的 `Data` 目录。
2. 导入成功后，进入“人物创建”页，保存攻击方和防守方模板。
3. 进入“场景设计”页，选择攻防人物，设置距离和最终命中率，保存测试场景。
4. 进入“结果对比”页，把一个或多个场景加入对比表，按列排序查看结果。
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

## 开发命令

运行测试：

```powershell
python -B -m pytest -q
```

运行 Ruff 检查：

```powershell
python -m ruff check .
```

## 项目结构

```text
src/rim_data_analysis/
  desktop_user_app.py              # 桌面应用入口
  desktop_user_app_character.py    # 人物创建页
  desktop_user_app_scenario.py     # 场景设计页
  desktop_user_app_pages.py        # 结果对比、数据导入、资源管理页
  combat_engine.py                 # 战斗计算核心
  user_app_*.py                    # 用户应用数据、存储、分析拼装
  vanilla_parser.py                # 原版 XML 数据解析
tests/                             # 单元测试
docs/                              # 项目文档
```

## 许可证

本项目使用 MIT License。详见 [LICENSE](LICENSE)。
