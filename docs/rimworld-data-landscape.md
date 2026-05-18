# RimWorld 数据版图

本文档用于记录当前项目对 `RimWorld` 数据来源的理解，作为后续分析实现的基础。

## 1. 当前确认的数据对象

### 1.1 游戏安装目录数据

`RimWorld` 的安装目录下存在 `Data` 文件夹，其中至少包含：

- `Core`
- 各 DLC 包目录

这些目录本质上都可以视作“游戏包”，结构与 Mod 十分接近，通常包含：

- `About/`
- `Defs/`
- `Patches/`
- `Languages/`
- `Textures/`
- `Assemblies/`

对分析项目来说，这些数据可以作为：

- 原版内容基线
- DLC 与社区 Mod 的结构对照样本
- Def 类型字典来源

### 1.2 Mod 数据

目前至少有两类 Mod 来源：

- 本地 Mod：通常放在游戏安装目录的 `Mods` 下
- Steam Workshop Mod：通常位于 Steam Workshop 对应 `RimWorld` 的内容目录

每个 Mod 通常包含：

- `About/About.xml`
- `Defs/`
- `Patches/`
- `Assemblies/`
- `LoadFolders.xml`（可选）

`About/About.xml` 是最关键的元数据入口，常见字段包括：

- `name`
- `author`
- `packageId`
- `supportedVersions`
- `description`
- `modDependencies`
- `loadBefore`
- `loadAfter`

### 1.3 Def 数据

RimWorld 的核心内容定义大量保存在 XML Def 中。对数据分析项目而言，Def 是最自然的结构化对象之一。

第一阶段建议重点统计：

- 每个包包含多少个 XML 文件
- 每个包包含多少种 Def 类型
- 各 Def 类型数量分布
- 新增 Def 与补丁 Def 的比例

例如常见顶层 Def 类型可能包括：

- `ThingDef`
- `RecipeDef`
- `ResearchProjectDef`
- `PawnKindDef`
- `HediffDef`
- `IncidentDef`
- `JobDef`

### 1.4 存档与配置数据

项目后续还应覆盖：

- 存档文件：XML 格式
- `ModsConfig.xml`：当前激活 Mod 列表与加载顺序
- 场景、预设、日志等用户侧数据

这些数据的价值在于：

- 分析“玩家真实启用的 Mod 组合”
- 分析存档与 Mod 的耦合程度
- 从世界、地图、角色、物品等维度做更细粒度统计

## 2. 目前的工程判断

### 2.1 第一阶段最稳妥的数据入口

优先级建议如下：

1. `Data/Core/DLC` 包扫描
2. 本地与 Workshop Mod 的目录扫描
3. `About/About.xml` 元数据解析
4. `Defs` 顶层节点统计
5. `ModsConfig.xml` 与存档 XML 解析

原因：

- 目录结构稳定
- 不需要侵入游戏运行过程
- 不依赖网络 API
- 可以直接在本地复现并分享到 GitHub

### 2.2 版本漂移风险

以下内容存在明显版本漂移：

- DLC 数量与名称
- Workshop Mod 的目录内容与兼容版本
- 某些 `About.xml` 字段是否存在
- Def 类型与补丁写法

因此本项目的实现原则应为：

- 不硬编码 DLC 名称
- 不依赖单一固定字段
- 对未知 XML 标签保持宽容
- 优先做“统计与抽取”，少做脆弱的强校验

### 2.3 路径风险

不同用户机器上的路径可能不同，原因包括：

- Steam 安装在不同盘符
- 使用多个 Steam Library
- 通过启动参数重定向了 `save data folder`

因此路径发现策略应为：

- 先读环境变量
- 再尝试常见默认路径
- 再解析 Steam `libraryfolders.vdf`
- 最后允许用户手动传参

## 3. 第一阶段建议产出

为了做成一个可分享的 GitHub 项目，第一阶段产出建议控制在下面几个结果：

- 一个可安装、可运行的 Python CLI
- 一份可复现的路径发现与扫描流程
- 一组结构化输出（JSON/CSV）
- 一套最小测试用例
- 一份记录数据版图与限制的文档

## 4. 当前未解决的问题

下面这些问题不是阻塞项，但后续需要尽快确认：

- 你的本机 `RimWorld` 安装目录实际在哪里
- 你的 Steam Workshop 库是否在默认盘符
- 你是否希望优先分析“原版 + DLC”，还是“你自己的 Mod 组合”
- 是否需要把“具体某个 Mod 集合”的订阅清单也纳入项目样例

## 5. 参考来源

以下来源用于确认当前实现阶段的数据假设。路径细节仍以本机实际目录为准。

- Steam 商店页（确认 `RimWorld` 的 Steam App ID 与 Workshop 支持）  
  https://store.steampowered.com/app/294100/RimWorld/?l=english
- Steam 社区 Workshop 页（确认 `RimWorld` 的 Workshop 存在）  
  https://steamcommunity.com/app/294100/workshop/
- RimWorld Wiki: XML Defs  
  https://rimworldwiki.com/wiki/Modding_Tutorials/XML_Defs
- RimWorld Wiki: Mod Folder Structure  
  https://rimworldwiki.com/wiki/Modding_Tutorials/Mod_folder_structure
- RimWorld Wiki: Save file  
  https://rimworldwiki.com/wiki/Save_file
- Ludeon 论坛：可通过游戏内 `Open save data folder` 查找保存目录  
  https://ludeon.com/forums/index.php?topic=14522.0
- Ludeon 论坛：`-savedatafolder` 启动参数可重定向用户数据目录  
  https://ludeon.com/forums/index.php?topic=23751.0

