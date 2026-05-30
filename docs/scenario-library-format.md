# 场景库格式（V1）

本文档定义 `analyze-library` 使用的场景库 JSON 格式。

当前只支持 `format_version: 1`。

## 目标

场景库格式服务于两个使用层次：

- 普通编辑：优先复用原版 `defName`，只写模板、武器选择和测试场景。
- 高级编辑：在普通编辑基础上，补充手工武器、手工护具和单场景覆盖。

## 根对象

```json
{
  "format_version": 1,
  "name": "sample-vanilla-library",
  "templates": [],
  "scenarios": []
}
```

字段说明：

- `format_version`
  - 必填，当前固定为 `1`
- `name`
  - 可选，场景库名称
- `templates`
  - 必填，模板数组
- `scenarios`
  - 必填，场景数组

## 模板

每个模板必须提供唯一 `id`。

```json
{
  "id": "baseline_shooter",
  "name": "Baseline Shooter",
  "shooting_skill": 12,
  "melee_skill": 4
}
```

支持字段：

- `id`
- `name`
- `extends`
- `species`
- `shooting_skill`
- `melee_skill`
- `body_size`
- `capacities`
- `traits`
- `add_traits`
- `remove_traits`
- `modifiers`
- `apparel_def_names`
- `add_apparel_def_names`
- `remove_apparel_def_names`
- `manual_apparel`
- `shooting_accuracy_per_tile_override`
- `melee_hit_chance_override`
- `melee_dodge_chance_override`
- `notes`

模板合并规则：

- 没有 `extends` 时，从默认白板小人基线开始。
- 有 `extends` 时，先解析父模板，再应用当前模板。
- `traits` 和 `apparel_def_names` 会直接重设当前列表。
- `add_traits` / `remove_traits`、`add_apparel_def_names` / `remove_apparel_def_names` 在当前列表上增删。
- `manual_apparel` 和 `modifiers` 会追加到继承结果末尾。
- 数值字段未填写时继承父模板值。

### 普通编辑推荐字段

普通使用优先只写：

- `shooting_skill`
- `melee_skill`
- `traits`
- `apparel_def_names`
- `extends`

示例：

```json
{
  "id": "vest_target",
  "extends": "baseline_target",
  "name": "Vest Target",
  "apparel_def_names": ["Apparel_TestVest"]
}
```

### 高级编辑字段

当原版目录不足以表达场景时，可以使用：

- `manual_apparel`
- `modifiers`
- `shooting_accuracy_per_tile_override`
- `melee_hit_chance_override`
- `melee_dodge_chance_override`

示例：

```json
{
  "id": "custom_target",
  "extends": "baseline_target",
  "manual_apparel": [
    {
      "name": "Prototype Jacket",
      "layers": ["Shell"],
      "covers": ["Torso", "Arms"],
      "armor_sharp": 42,
      "armor_blunt": 12
    }
  ],
  "modifiers": [
    {
      "name": "injury_penalty",
      "incoming_damage_multiplier": 1.1
    }
  ]
}
```

## 场景

每个场景必须提供唯一 `id`，并指向一个攻击模板和一个防守模板。

```json
{
  "id": "rifle_vs_vest",
  "name": "Rifle vs Vest",
  "attacker_template": "baseline_shooter",
  "defender_template": "vest_target",
  "weapon_def_name": "Gun_TestRifle",
  "tags": ["ranged", "vest"],
  "context": {
    "distance_cells": 18,
    "target_body_region": "Torso"
  }
}
```

支持字段：

- `id`
- `name`
- `attacker_template`
- `defender_template`
- `weapon_def_name`
- `manual_weapon`
- `attacker_override`
- `defender_override`
- `context`
- `tags`
- `notes`

规则：

- `weapon_def_name` 和 `manual_weapon` 必须二选一。
- `attacker_override` / `defender_override` 只做“局部覆盖”，不能再写 `extends`。
- `tags` 用于 `--tag` 过滤。

### 普通编辑推荐字段

普通使用优先只写：

- `attacker_template`
- `defender_template`
- `weapon_def_name`
- `tags`
- `context`

### 高级编辑字段

高级场景可以使用：

- `manual_weapon`
- `attacker_override`
- `defender_override`

示例：

```json
{
  "id": "custom_smg_test",
  "name": "Custom SMG Test",
  "attacker_template": "baseline_shooter",
  "defender_template": "vest_target",
  "manual_weapon": {
    "name": "Prototype SMG",
    "attack_mode": "ranged",
    "damage_type": "Sharp",
    "damage": 9,
    "armor_penetration": 14,
    "warmup_seconds": 1.1,
    "cooldown_seconds": 1.8,
    "burst_shot_count": 3,
    "burst_shot_interval_seconds": 0.15,
    "accuracy_close": 0.84,
    "accuracy_short": 0.78,
    "accuracy_medium": 0.62,
    "accuracy_long": 0.42
  },
  "defender_override": {
    "add_traits": ["tough"]
  },
  "context": {
    "distance_cells": 14,
    "target_body_region": "Torso"
  }
}
```

## 子对象字段

### capacities

支持字段：

- `sight`
- `manipulation`
- `moving`

### context

支持字段：

- `distance_cells`
- `target_body_region`
- `target_is_aiming_or_firing`
- `hit_chance_multiplier`
- `cover_block_chance`

### manual_weapon

必填字段：

- `name`
- `attack_mode`
- `damage_type`
- `damage`

可选字段：

- `armor_penetration`
- `warmup_seconds`
- `cooldown_seconds`
- `burst_shot_count`
- `burst_shot_interval_seconds`
- `accuracy_close`
- `accuracy_short`
- `accuracy_medium`
- `accuracy_long`

其中 `attack_mode` 当前只允许：

- `ranged`
- `melee`

### manual_apparel

必填字段：

- `name`

可选字段：

- `source`
- `layers`
- `covers`
- `armor_sharp`
- `armor_blunt`
- `armor_heat`
- `layer_priority_override`

### modifiers

支持字段与 `CombatStatModifier` 一致，例如：

- `shooting_skill_offset`
- `shooting_accuracy_per_tile_offset`
- `shooting_accuracy_multiplier`
- `aiming_time_multiplier`
- `ranged_cooldown_multiplier`
- `melee_hit_score_offset`
- `melee_hit_chance_offset`
- `melee_hit_chance_multiplier`
- `melee_dodge_score_offset`
- `melee_dodge_chance_offset`
- `melee_dodge_chance_multiplier`
- `melee_damage_multiplier`
- `armor_penetration_multiplier`
- `incoming_damage_multiplier`

## 当前加载器会直接报错的情况

- 缺少 `templates` 或 `scenarios`
- 重复的模板 `id`
- 重复的场景 `id`
- 模板继承引用不存在的模板
- 模板继承形成环
- `weapon_def_name` 和 `manual_weapon` 同时出现
- `attacker_override` 或 `defender_override` 中写 `extends`
- 拼错字段名或出现未知字段

## 参考文件

- [sample-library.json](../assets/scenario-libraries/sample-library.json)
- [shooting-test-library.json](../assets/scenario-libraries/shooting-test-library.json)
- [README.md](../README.md)
