# Rim Data Analysis

`Rim Data Analysis` 是一个面向 `RimWorld` 及其 `Mod` 生态的数据分析项目骨架。

当前阶段目标：

- 建立一个可公开分享在 GitHub 的、结构清晰的 Python 项目
- 先完成 `RimWorld` 本体、DLC 的元数据扫描与原版装备分析
- 为后续的存档分析、Mod 依赖分析、Def 统计分析打基础
- 建立“白板小人 + 武器 + 护具”的第一版战斗分析核心
- 优先做出 `V1 = 只支持原版` 的可用分析流程

## 当前能力

- 自动发现常见 Windows 下的 `Steam` 与 `RimWorld` 路径
- 扫描以下数据源：
  - 游戏安装目录下的 `Data` 包（如 `Core`、各 DLC）
  - 本地 `Mods` 目录
  - Steam Workshop `294100` 目录
- 解析 `About/About.xml`
- 统计 `Defs`、`Patches`、`Languages`、`Assemblies` 等目录中的文件数量
- 统计 XML Def 顶层节点类型数量，例如 `ThingDef`、`RecipeDef`、`ResearchProjectDef`
- 导出：
  - `inventory.json`
  - `packages.csv`
  - `def_counts.csv`
  - `summary.json`
- 支持基于 JSON 场景文件运行第一版战斗分析：
  - 白板小人
  - 特性与自定义修正
  - 护具叠穿检查
  - 多层护甲期望结算
  - 远程/近战命中与 DPS 估算
- 支持从原版 `Data/Core + DLC` 直接导入武器与护具目录并生成基础分析表

## 项目结构

```text
src/
  rim_data_analysis/
tests/
  fixtures/
docs/
scripts/
assets/
```

## 快速开始

建议使用 Python 3.11+。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pytest
```

安装后运行扫描：

```powershell
rim-analysis inventory --output-dir .\artifacts\sample-scan
```

运行战斗分析示例：

```powershell
rim-analysis analyze-scenario `
  --scenario .\assets\scenarios\sample-ranged-vs-armor.json `
  --output .\artifacts\combat\sample-ranged-vs-armor.json
```

运行原版装备分析：

```powershell
rim-analysis analyze-vanilla `
  --game-data-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Data" `
  --output-dir .\artifacts\vanilla-analysis
```

运行场景库批量对比：

```powershell
rim-analysis analyze-library `
  --library .\assets\scenario-libraries\sample-library.json `
  --game-data-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Data" `
  --output-dir .\artifacts\scenario-library
```

如果自动发现失败，可以显式传入路径：

```powershell
rim-analysis inventory `
  --game-data-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Data" `
  --local-mods-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Mods" `
  --workshop-root "D:\SteamLibrary\steamapps\workshop\content\294100" `
  --output-dir .\artifacts\sample-scan
```

也支持环境变量：

- `RIMWORLD_GAME_DATA_ROOT`
- `RIMWORLD_LOCAL_MODS_ROOT`
- `RIMWORLD_WORKSHOP_ROOT`
- `RIMWORLD_SAVE_DATA_ROOT`

## 第一版战斗分析器

第一版战斗分析器目前支持：

- 默认以原版智人为白板小人
- 使用特性：
  - `tough`
  - `careful_shooter`
  - `trigger_happy`
  - `brawler`
  - `nimble`
- 通过 `layers + covers` 检查衣物/护甲是否冲突
- 在指定身体区域上做多层护甲结算
- 计算：
  - 远程命中率
  - 近战命中率
  - 单次命中期望伤害
  - 单次攻击期望伤害
  - 理论 DPS
  - 实战期望 DPS
- 护甲减伤率

## V1 使用流程

当前推荐的 V1 使用流程是：

1. 先用 `analyze-vanilla` 生成原版武器与护具目录。
2. 在场景库 JSON 中定义：
   - 小人模板
   - 装备组合
   - 测试场景
3. 用 `analyze-library` 批量计算场景。
4. 在导出的表格中横向对比多个场景的输出与承伤结果。

场景库当前支持：

- 模板继承，例如“基于基础小人增加特性或护具”
- 通过原版装备 `defName` 选择武器与护具
- 单场景标签
- 按标签、场景 ID、名称过滤分析结果
- 导出：
  - `scenario_results.json`
  - `scenario_results.csv`
  - `comparison_matrix.csv`
  - `comparison_report.html`

当前限制：

- 当前 `V1` 只针对原版与 DLC
- 还没有支持 Mod 装备自动导入
- 还没有做全身命中部位分布
- 还没有做 Combat Extended 兼容

## 结果示例

扫描输出主要包含两层信息：

- 包级别：每个 `Core/DLC/Mod` 的名称、包 ID、作者、来源、支持版本、目录结构统计
- Def 级别：每个包里定义了多少种 Def、各类型数量如何分布

这足以支撑第一阶段的数据分析问题，例如：

- 常见 Mod 使用了哪些 Def 类型？
- 某个大型 Mod 包含多少 XML 和 DLL？
- DLC 与社区 Mod 在内容结构上有什么差异？
- 一个 Mod 包是否依赖较多补丁而非新增 Def？

## 后续路线

- 存档 XML 分析：殖民地规模、角色、科技、事件、地图对象统计
- `ModsConfig.xml` 分析：实际启用 Mod 组合、加载顺序、依赖问题
- Workshop 扩展：结合订阅集合、更新时间、兼容版本做趋势分析
- 可视化报告：Jupyter Notebook 或静态 HTML 报告

## 文档

- [RimWorld 数据版图](docs/rimworld-data-landscape.md)
- [项目路线图](docs/project-roadmap.md)
- [任务面板](docs/task-board.md)
- [第一版战斗分析器设计](docs/phase1-combat-analyzer.md)
