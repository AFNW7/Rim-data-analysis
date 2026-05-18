# 项目交接记录（2026-05-19）

本文档用于在下次继续开发时快速恢复上下文。

## 1. 当前项目定位

当前项目已经明确收敛为：

- `V1` 只支持 `RimWorld` 原版与已安装 DLC
- `Mod` 导入不是取消，而是延后到 V1 完成后的扩展阶段

V1 的目标不是完整还原所有游戏系统，而是先做出一个可实际使用的：

- 原版武器/护具导入器
- 白板小人战斗分析器
- 场景库与模板系统
- 批量比较与静态报告输出

## 2. 已完成内容

### 2.1 仓库与基础工程

已完成：

- Python 项目骨架
- Git 仓库初始化
- README、路线图、任务面板、数据说明文档
- 基础测试体系

关键文件：

- [README.md](/E:/Desktop/project/Rim-data-analysis/README.md)
- [pyproject.toml](/E:/Desktop/project/Rim-data-analysis/pyproject.toml)
- [docs/project-roadmap.md](/E:/Desktop/project/Rim-data-analysis/docs/project-roadmap.md)
- [docs/task-board.md](/E:/Desktop/project/Rim-data-analysis/docs/task-board.md)

### 2.2 元数据扫描器

已完成：

- Steam/RimWorld 路径发现
- `Core/DLC/本地 Mod/Workshop Mod` 包级元数据扫描
- `About.xml` 解析
- `Defs/Patches/Assemblies` 基础统计

说明：

- 这部分已可用，但当前 V1 主线不再继续扩展 Mod 导入

关键文件：

- [src/rim_data_analysis/paths.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/paths.py)
- [src/rim_data_analysis/scanner.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/scanner.py)
- [src/rim_data_analysis/reporting.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/reporting.py)

### 2.3 战斗分析引擎

已完成：

- 白板小人数据模型
- 特性支持：
  - `tough`
  - `careful_shooter`
  - `trigger_happy`
  - `brawler`
  - `nimble`
- 护具叠穿冲突检查
- 多层护甲期望结算
- 远程/近战命中率估算
- 单次期望伤害、理论 DPS、实战期望 DPS 计算

关键文件：

- [src/rim_data_analysis/combat_models.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/combat_models.py)
- [src/rim_data_analysis/combat_engine.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/combat_engine.py)
- [src/rim_data_analysis/combat_io.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/combat_io.py)

### 2.4 原版武器/护具导入

已完成：

- 从原版 `Data/Core + DLC` 的 `ThingDef` 里抽取：
  - 远程武器
  - 近战武器
  - 护具
- 生成原版目录和基础分析表

当前导入字段包括：

- 武器：
  - `defName`
  - `label`
  - `attack_mode`
  - `damage`
  - `damage_type`
  - `armor_penetration`
  - `warmup`
  - `cooldown`
  - `burst`
  - `accuracy`
- 护具：
  - `defName`
  - `label`
  - `layers`
  - `bodyPartGroups`
  - `ArmorRating_Sharp/Blunt/Heat`

关键文件：

- [src/rim_data_analysis/vanilla_models.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/vanilla_models.py)
- [src/rim_data_analysis/vanilla_parser.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/vanilla_parser.py)
- [src/rim_data_analysis/vanilla_reporting.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/vanilla_reporting.py)

### 2.5 场景库与模板系统

已完成：

- 小人模板定义
- 模板继承
- 通过原版装备 `defName` 选择武器/护具
- 场景保存
- 标签筛选
- 批量分析
- 横向对比矩阵导出

关键文件：

- [src/rim_data_analysis/scenario_library.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/scenario_library.py)
- [src/rim_data_analysis/scenario_library_reporting.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/scenario_library_reporting.py)
- [assets/scenario-libraries/sample-library.json](/E:/Desktop/project/Rim-data-analysis/assets/scenario-libraries/sample-library.json)

### 2.6 静态 HTML 对比页

已完成：

- `analyze-library` 输出静态 HTML
- 支持：
  - 标签筛选
  - 关键词筛选
  - 多场景横向比较

输出文件名：

- `comparison_report.html`

## 3. 当前 CLI 能力

### 3.1 包扫描

```powershell
rim-analysis inventory --output-dir .\artifacts\sample-scan
```

### 3.2 单场景分析

```powershell
rim-analysis analyze-scenario `
  --scenario .\assets\scenarios\sample-ranged-vs-armor.json `
  --output .\artifacts\combat\sample-ranged-vs-armor.json
```

### 3.3 原版目录分析

```powershell
rim-analysis analyze-vanilla `
  --game-data-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Data" `
  --output-dir .\artifacts\vanilla-analysis
```

### 3.4 场景库批量分析

```powershell
rim-analysis analyze-library `
  --library .\assets\scenario-libraries\sample-library.json `
  --game-data-root "C:\Program Files (x86)\Steam\steamapps\common\RimWorld\Data" `
  --output-dir .\artifacts\scenario-library
```

可选筛选：

- `--tag layered`
- `--scenario-id rifle_vs_vest`
- `--name-contains rifle`

## 4. 当前产物位置

### 4.1 原版目录分析样例

- [artifacts/vanilla-fixture-analysis](/E:/Desktop/project/Rim-data-analysis/artifacts/vanilla-fixture-analysis)

### 4.2 单场景分析样例

- [artifacts/combat](/E:/Desktop/project/Rim-data-analysis/artifacts/combat)

### 4.3 场景库分析样例

- [artifacts/library-fixture-analysis](/E:/Desktop/project/Rim-data-analysis/artifacts/library-fixture-analysis)
- [artifacts/library-fixture-layered](/E:/Desktop/project/Rim-data-analysis/artifacts/library-fixture-layered)

重点查看：

- [comparison_report.html](/E:/Desktop/project/Rim-data-analysis/artifacts/library-fixture-analysis/comparison_report.html)
- [scenario_results.csv](/E:/Desktop/project/Rim-data-analysis/artifacts/library-fixture-analysis/scenario_results.csv)
- [comparison_matrix.csv](/E:/Desktop/project/Rim-data-analysis/artifacts/library-fixture-analysis/comparison_matrix.csv)

## 5. 当前测试状态

最后一次验证结果：

- `python -m pytest`
- 结果：`15 passed`

测试文件：

- [tests/test_combat_engine.py](/E:/Desktop/project/Rim-data-analysis/tests/test_combat_engine.py)
- [tests/test_paths.py](/E:/Desktop/project/Rim-data-analysis/tests/test_paths.py)
- [tests/test_scanner.py](/E:/Desktop/project/Rim-data-analysis/tests/test_scanner.py)
- [tests/test_vanilla_parser.py](/E:/Desktop/project/Rim-data-analysis/tests/test_vanilla_parser.py)
- [tests/test_scenario_library.py](/E:/Desktop/project/Rim-data-analysis/tests/test_scenario_library.py)

## 6. 当前未提交改动

本次会话结束时，`git status --short` 显示仍有未提交改动：

- [README.md](/E:/Desktop/project/Rim-data-analysis/README.md)
- [src/rim_data_analysis/scenario_library_reporting.py](/E:/Desktop/project/Rim-data-analysis/src/rim_data_analysis/scenario_library_reporting.py)
- [tests/test_scenario_library.py](/E:/Desktop/project/Rim-data-analysis/tests/test_scenario_library.py)

说明：

- 这些改动是本轮新增的 HTML 报告支持与说明更新
- 功能已通过测试

## 7. 下次最优先继续做什么

建议的下一步优先级：

### 7.1 第一优先级：定稿 V1 场景库格式

原因：

- 当前 JSON 已可用，但还比较“工程内部格式”
- 需要收敛成稳定的用户侧数据规范

建议继续做：

- 明确模板字段规范
- 明确场景字段规范
- 明确“普通编辑”和“高级编辑”的 JSON 表达方式
- 为每个字段补文档示例

### 7.2 第二优先级：增强原版导入字段

建议继续做：

- 补更多原版武器属性
- 补更多护具属性
- 更准确地区分武器类别
- 为后续统计页补更多列

### 7.3 第三优先级：增强统计与对比页

建议继续做：

- 增加更多筛选项
- 增加排序
- 增加导出更适合人工阅读的汇总卡片
- 增加“按攻击方/防守方/武器/护具”分组视图

## 8. 当前重要决策

下次继续时不要忘记：

- `V1` 只做原版与 DLC
- `Mod` 导入延后，不是取消
- 当前优先级是把“原版分析工作流”做实
- 比起继续加底层公式，当前更重要的是：
  - 场景库格式稳定
  - 报表可用性提升
  - 用户操作流程清晰

