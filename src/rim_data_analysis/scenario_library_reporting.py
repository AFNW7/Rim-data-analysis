from __future__ import annotations

import csv
import json
from statistics import mean
from pathlib import Path

from rim_data_analysis.scenario_library import ScenarioRecord


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    resolved_fieldnames = fieldnames or sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _comparison_matrix(records: list[ScenarioRecord]) -> list[dict[str, object]]:
    if not records:
        return []

    matrix_rows: list[dict[str, object]] = []
    scenario_columns = [record.scenario_id for record in records]
    metric_extractors = [
        ("scenario_name", lambda record: record.scenario_name),
        ("tags", lambda record: "|".join(record.tags)),
        ("attacker_template", lambda record: record.attacker_template),
        ("defender_template", lambda record: record.defender_template),
        ("weapon_def_name", lambda record: record.weapon_def_name or ""),
        ("attack_mode", lambda record: record.attack_mode),
        ("can_wear_outfit", lambda record: str(record.analysis.can_wear_outfit)),
        ("final_hit_chance", lambda record: record.analysis.accuracy.final_hit_chance),
        ("expected_damage_on_hit", lambda record: record.analysis.damage.expected_damage_on_hit_after_defense),
        ("expected_damage_per_attack_cycle", lambda record: record.analysis.damage.expected_damage_per_attack_cycle),
        ("expected_dps", lambda record: record.analysis.damage.expected_dps),
        ("theoretical_dps", lambda record: record.analysis.damage.theoretical_dps),
        ("realized_dps_ratio", lambda record: record.analysis.damage.realized_dps_ratio),
        ("armor_reduction_rate", lambda record: record.analysis.armor.reduction_rate_from_armor),
        ("incoming_damage_multiplier", lambda record: record.analysis.armor.total_damage_taken_multiplier),
    ]

    for metric_name, extractor in metric_extractors:
        row: dict[str, object] = {"metric": metric_name}
        for scenario_id, record in zip(scenario_columns, records):
            row[scenario_id] = extractor(record)
        matrix_rows.append(row)
    return matrix_rows


def _record_field_order() -> list[str]:
    return [
        "library_name",
        "scenario_id",
        "scenario_name",
        "tags",
        "attacker_template",
        "defender_template",
        "weapon_def_name",
        "attack_mode",
        "can_wear_outfit",
        "final_hit_chance",
        "expected_damage_on_hit",
        "expected_damage_per_attack_cycle",
        "expected_dps",
        "theoretical_dps",
        "realized_dps_ratio",
        "armor_reduction_rate",
        "incoming_damage_multiplier",
    ]


def _metric_labels() -> list[tuple[str, str]]:
    return [
        ("scenario_name", "场景名称"),
        ("tags", "标签"),
        ("attacker_template", "攻击方模板"),
        ("defender_template", "防守方模板"),
        ("weapon_def_name", "武器 DefName"),
        ("attack_mode", "攻击模式"),
        ("can_wear_outfit", "穿戴合法"),
        ("final_hit_chance", "最终命中率"),
        ("expected_damage_on_hit", "命中期望伤害"),
        ("expected_damage_per_attack_cycle", "单轮期望伤害"),
        ("expected_dps", "期望 DPS"),
        ("theoretical_dps", "理论 DPS"),
        ("realized_dps_ratio", "DPS 实现率"),
        ("armor_reduction_rate", "护甲减伤率"),
        ("incoming_damage_multiplier", "最终承伤倍率"),
    ]


def _build_html_report(records: list[ScenarioRecord]) -> str:
    unique_tags = sorted({tag for record in records for tag in record.tags})
    summary = {
        "scenario_count": len(records),
        "ranged_count": sum(1 for record in records if record.attack_mode == "ranged"),
        "melee_count": sum(1 for record in records if record.attack_mode == "melee"),
        "avg_expected_dps": mean([record.analysis.damage.expected_dps for record in records]) if records else 0.0,
    }

    payload = {
        "summary": summary,
        "records": [record.to_flat_dict() for record in records],
        "metric_labels": [{"key": key, "label": label} for key, label in _metric_labels()],
        "tags": unique_tags,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RimWorld Scenario Comparison</title>
  <style>
    :root {{
      --bg: #f3efe5;
      --panel: #fffaf1;
      --panel-strong: #f0e4cf;
      --ink: #1f2a2b;
      --muted: #586367;
      --line: #d7c7aa;
      --accent: #9b5a1a;
      --accent-soft: #f3d2a9;
      --good: #2b6e49;
      --bad: #8f3c2f;
      --shadow: 0 18px 40px rgba(42, 34, 18, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Bahnschrift, "Segoe UI Variable Text", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(155, 90, 26, 0.12), transparent 22rem),
        linear-gradient(180deg, #f7f2e9 0%, var(--bg) 100%);
    }}
    .page {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }}
    .hero-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }}
    .hero-card {{
      padding: 28px;
      position: relative;
      overflow: hidden;
    }}
    .hero-card::after {{
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: linear-gradient(135deg, rgba(155, 90, 26, 0.18), rgba(155, 90, 26, 0));
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 36px;
      line-height: 1.05;
    }}
    .sub {{
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
      max-width: 48rem;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      padding: 20px;
    }}
    .summary-item {{
      background: var(--panel-strong);
      border-radius: 16px;
      padding: 16px;
      min-height: 110px;
    }}
    .summary-value {{
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
      margin-bottom: 6px;
    }}
    .summary-label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 24px;
    }}
    .panel {{
      padding: 20px;
    }}
    .panel h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}
    .filter-group {{
      margin-bottom: 18px;
    }}
    .filter-group label {{
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    input[type="search"] {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #fffdf9;
      color: var(--ink);
      font: inherit;
    }}
    .tag-list, .scenario-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .tag-chip, .scenario-chip {{
      border: 1px solid var(--line);
      background: #fffdf8;
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
      transition: 120ms ease;
    }}
    .tag-chip.active, .scenario-chip.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff8f0;
    }}
    .scenario-chip small {{
      color: inherit;
      opacity: 0.85;
    }}
    .table-wrap {{
      overflow: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fffefb;
    }}
    thead th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #efe4d2;
      color: var(--ink);
      text-align: left;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid #e8dcc7;
      vertical-align: top;
      white-space: nowrap;
    }}
    tbody tr:nth-child(odd) {{
      background: rgba(255, 248, 238, 0.65);
    }}
    .metric-cell {{
      font-weight: 700;
      position: sticky;
      left: 0;
      background: #f7efe1;
    }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    .status-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 13px;
    }}
    .good {{ color: var(--good); }}
    .bad {{ color: var(--bad); }}
    @media (max-width: 1080px) {{
      .hero, .layout {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 30px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <article class="hero-card">
        <div class="eyebrow">V1 Vanilla Comparison</div>
        <h1>场景库横向对比</h1>
        <div class="sub">这个页面基于场景库计算结果生成。你可以按标签或名称筛选场景，并将多个测试场景并列比较输出、命中和承伤指标。</div>
      </article>
      <aside class="hero-card">
        <div class="summary-grid" id="summaryGrid"></div>
      </aside>
    </section>

    <section class="layout">
      <aside class="panel">
        <h2>筛选</h2>
        <div class="filter-group">
          <label for="searchInput">按名称 / 模板 / 武器搜索</label>
          <input id="searchInput" type="search" placeholder="例如 rifle / layered / tough">
        </div>
        <div class="filter-group">
          <label>标签</label>
          <div class="tag-list" id="tagList"></div>
        </div>
        <div class="filter-group">
          <label>场景选择</label>
          <div class="scenario-list" id="scenarioList"></div>
        </div>
        <div class="hint">默认会展示筛选结果中的全部场景。点击场景胶囊可以进一步做手动多选对比。</div>
      </aside>

      <main class="panel">
        <h2>对比表</h2>
        <div class="status-line">
          <span id="visibleCounter"></span>
          <span>提示：命中率和 DPS 越高通常越偏输出；减伤率越高、最终承伤倍率越低通常越偏防御。</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr id="tableHeadRow"></tr>
            </thead>
            <tbody id="tableBody"></tbody>
          </table>
        </div>
      </main>
    </section>
  </div>

  <script>
    const data = {payload_json};
    const selectedTags = new Set();
    const manualScenarioSelection = new Set();

    const summaryGrid = document.getElementById("summaryGrid");
    const tagList = document.getElementById("tagList");
    const scenarioList = document.getElementById("scenarioList");
    const searchInput = document.getElementById("searchInput");
    const tableHeadRow = document.getElementById("tableHeadRow");
    const tableBody = document.getElementById("tableBody");
    const visibleCounter = document.getElementById("visibleCounter");

    function formatValue(key, value) {{
      if (typeof value !== "number") return String(value);
      if (["final_hit_chance", "realized_dps_ratio", "armor_reduction_rate", "incoming_damage_multiplier"].includes(key)) {{
        return value.toFixed(4);
      }}
      if (["expected_damage_on_hit", "expected_damage_per_attack_cycle", "expected_dps", "theoretical_dps"].includes(key)) {{
        return value.toFixed(4);
      }}
      return String(value);
    }}

    function renderSummary() {{
      const items = [
        ["场景数", data.summary.scenario_count],
        ["远程场景", data.summary.ranged_count],
        ["近战场景", data.summary.melee_count],
        ["平均期望 DPS", Number(data.summary.avg_expected_dps).toFixed(4)]
      ];
      summaryGrid.innerHTML = items.map(([label, value]) => `
        <div class="summary-item">
          <div class="summary-value">${{value}}</div>
          <div class="summary-label">${{label}}</div>
        </div>
      `).join("");
    }}

    function renderTags() {{
      const allChip = document.createElement("button");
      allChip.className = "tag-chip" + (selectedTags.size === 0 ? " active" : "");
      allChip.textContent = "全部";
      allChip.addEventListener("click", () => {{
        selectedTags.clear();
        renderTags();
        render();
      }});
      tagList.innerHTML = "";
      tagList.appendChild(allChip);

      data.tags.forEach((tag) => {{
        const chip = document.createElement("button");
        chip.className = "tag-chip" + (selectedTags.has(tag) ? " active" : "");
        chip.textContent = tag;
        chip.addEventListener("click", () => {{
          if (selectedTags.has(tag)) {{
            selectedTags.delete(tag);
          }} else {{
            selectedTags.add(tag);
          }}
          renderTags();
          render();
        }});
        tagList.appendChild(chip);
      }});
    }}

    function filterRecords() {{
      const keyword = searchInput.value.trim().toLowerCase();
      return data.records.filter((record) => {{
        const tagSet = new Set(String(record.tags || "").split("|").filter(Boolean));
        const matchesTags = [...selectedTags].every((tag) => tagSet.has(tag));
        if (!matchesTags) return false;

        if (!keyword) return true;
        const haystack = [
          record.scenario_name,
          record.attacker_template,
          record.defender_template,
          record.weapon_def_name,
          record.tags
        ].join(" ").toLowerCase();
        return haystack.includes(keyword);
      }});
    }}

    function selectedRecords(filteredRecords) {{
      if (manualScenarioSelection.size === 0) return filteredRecords;
      const selected = filteredRecords.filter((record) => manualScenarioSelection.has(record.scenario_id));
      return selected.length > 0 ? selected : filteredRecords;
    }}

    function renderScenarioList(filteredRecords) {{
      scenarioList.innerHTML = "";
      filteredRecords.forEach((record) => {{
        const chip = document.createElement("button");
        chip.className = "scenario-chip" + (manualScenarioSelection.has(record.scenario_id) ? " active" : "");
        chip.innerHTML = `${{record.scenario_name}} <small>${{record.scenario_id}}</small>`;
        chip.addEventListener("click", () => {{
          if (manualScenarioSelection.has(record.scenario_id)) {{
            manualScenarioSelection.delete(record.scenario_id);
          }} else {{
            manualScenarioSelection.add(record.scenario_id);
          }}
          render();
        }});
        scenarioList.appendChild(chip);
      }});
    }}

    function renderComparison(records) {{
      tableHeadRow.innerHTML = "";
      const metricHead = document.createElement("th");
      metricHead.textContent = "指标";
      tableHeadRow.appendChild(metricHead);

      records.forEach((record) => {{
        const th = document.createElement("th");
        th.innerHTML = `<div>${{record.scenario_name}}</div><div style="font-size:12px;color:var(--muted)">${{record.scenario_id}}</div>`;
        tableHeadRow.appendChild(th);
      }});

      tableBody.innerHTML = "";
      data.metric_labels.forEach((metric) => {{
        const row = document.createElement("tr");
        const metricCell = document.createElement("td");
        metricCell.className = "metric-cell";
        metricCell.textContent = metric.label;
        row.appendChild(metricCell);

        records.forEach((record) => {{
          const td = document.createElement("td");
          const value = record[metric.key];
          td.textContent = formatValue(metric.key, value);
          if (metric.key === "can_wear_outfit") {{
            td.className = value === true ? "good" : "bad";
          }}
          row.appendChild(td);
        }});
        tableBody.appendChild(row);
      }});
    }}

    function render() {{
      const filtered = filterRecords();
      renderScenarioList(filtered);
      const finalRecords = selectedRecords(filtered);
      visibleCounter.textContent = `当前显示 ${{finalRecords.length}} / ${{data.records.length}} 个场景`;
      renderComparison(finalRecords);
    }}

    searchInput.addEventListener("input", render);
    renderSummary();
    renderTags();
    render();
  </script>
</body>
</html>
"""


def write_scenario_library_report(output_dir: Path, records: list[ScenarioRecord]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    records_json = output_dir / "scenario_results.json"
    records_csv = output_dir / "scenario_results.csv"
    comparison_csv = output_dir / "comparison_matrix.csv"
    comparison_html = output_dir / "comparison_report.html"

    records_json.write_text(
        json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    record_rows = [record.to_flat_dict() for record in records]
    _write_csv(records_csv, record_rows or [{"empty": ""}], fieldnames=_record_field_order() if record_rows else None)
    comparison_rows = _comparison_matrix(records)
    comparison_fieldnames = ["metric"] + [record.scenario_id for record in records]
    _write_csv(
        comparison_csv,
        comparison_rows or [{"metric": "no_data"}],
        fieldnames=comparison_fieldnames if comparison_rows else None,
    )
    comparison_html.write_text(_build_html_report(records), encoding="utf-8")

    return {
        "scenario_results_json": records_json,
        "scenario_results_csv": records_csv,
        "comparison_matrix_csv": comparison_csv,
        "comparison_report_html": comparison_html,
    }
