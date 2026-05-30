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
- 场景库 JSON 已收敛为 `V1` 格式，并在加载时校验重复 ID、继承环和冲突字段
- 提供桌面工作台界面，可在应用窗口中执行包扫描、原版分析、单场景分析和场景库批量分析
- 桌面工作台已支持中文界面，并提供可编辑、可保存、可直接分析的单场景表单编辑器

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

启动桌面应用：

```powershell
.venv\Scripts\Activate.ps1
rim-analysis app
```

如果 PowerShell 提示找不到 `rim-analysis`，通常是因为当前还没有激活虚拟环境。这时可以直接运行：

```powershell
.\.venv\Scripts\rim-analysis-app.exe
```

也可以直接运行：

```powershell
.\.venv\Scripts\rim-analysis.exe app
```

桌面应用当前包含：

- 包扫描页
- 原版目录分析页
- 面向普通用户的单场景编辑页
- 面向普通用户的场景库批量分析页

## 桌面应用使用（推荐普通用户）

如果你不熟悉 JSON、defName 或命令行，推荐直接使用桌面界面。

### 1. 单场景分析

在“场景编辑”页按下面流程操作：

1. 点击“自动填入路径”或手动选择 `RimWorld Data` 路径。
2. 点击“载入原版装备目录”。
3. 填写攻击方和防守方名字、技能，并勾选特性。
4. 在武器列表里直接点选武器。
5. 在护具列表里点选护具，再点击“添加 >”。
6. 选择战斗距离、命中部位、掩体情况。
7. 点击“开始分析”。

这个页面默认不要求你输入内部代码名。武器、护具、特性都优先使用点选；只有在需要自定义内容时，才进入“高级设置”。

### 2. 场景库批量分析

在“场景库”页按下面流程操作：

1. 选择场景库文件。
2. 选择 `RimWorld Data` 路径。
3. 点击“读取库内容”。
4. 在页面里勾选标签，或直接选择要分析的场景。
5. 点击“批量分析”。

这个页面会先读取库内容，再把“标签”和“场景列表”显示出来。普通用户不需要手动输入场景 ID。

仓库自带一套“射击测试场景库”，适合先做项目测试：

- 文件：`assets/scenario-libraries/shooting-test-library.json`
- 桌面端入口：“场景库”页里的“载入射击测试库”
- 自动使用仓库内测试数据路径：`tests/fixtures/vanilla_game_data`
- 内容：
  - 12 个射手组合：`大师/传奇` × `乱开枪/无` × `射击专家/射击指令/无`
  - 3 个靶子：`衬衫长裤`、`防弹三件套`、`海军动力甲`
  - 共 36 个批量测试场景

### 3. 结果查看

无论是单场景还是场景库分析，右侧结果区都会显示：

- 关键结果卡片
- 结果说明
- 生成文件列表

你可以直接点击“打开选中文件”、“打开输出目录”或“打开 HTML 报告”。

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

1. 先启动桌面应用。
2. 在“场景编辑”页载入原版装备目录，用点选方式完成单场景分析。
3. 如果需要批量对比，再到“场景库”页读取场景库内容。
4. 勾选标签或场景后运行批量分析。
5. 在导出的表格和 HTML 报告里横向对比多个场景的输出与承伤结果。

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

场景库格式文档：

- [场景库格式（V1）](docs/scenario-library-format.md)

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
- [场景库格式（V1）](docs/scenario-library-format.md)
