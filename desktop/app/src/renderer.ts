import "./styles.css";

declare global {
  interface Window {
    rimBridge?: {
      apiBaseUrl: string;
      getApiStatus: () => Promise<string>;
    };
  }
}

type OptionDetail = [string, string];

type PawnOption = {
  id?: string;
  name: string;
  label?: string;
  defName?: string;
  supportsMaterial?: boolean;
  defaultFullBodyArmorPercent?: number;
  detail?: OptionDetail[];
  choice?: {
    def_name: string;
    label: string;
    quality_id: string;
    material_id?: string | null;
  };
};

type PawnModule = "base" | "traits" | "specials" | "implants" | "weapon" | "apparel";

type SelectOption = {
  id: string;
  label: string;
};

type PawnCatalog = Record<
  PawnModule,
  {
    title: string;
    desc: string;
    mode: "single" | "multi";
    action: string;
    placeholder: string;
    options: PawnOption[];
  }
>;

type ApiImportSettings = {
  gameDataRoot: string;
  workshopRoot: string;
  catalogWeaponCount: number;
  catalogApparelCount: number;
  catalogImplantCount: number;
  lastImportedAt: string;
};

type ApiPawn = DetailItem & {
  name: string;
  speciesId: string;
  speciesLabel: string;
  shootingSkill: number;
  fullBodyArmorPercent: number;
  weaponName: string;
};

type ApiScenario = DetailItem & {
  name: string;
  attackerPawnId: string;
  defenderPawnId: string;
  attackerName: string;
  defenderName: string;
  distanceCells: number;
  hitChancePercent: number;
};

type ApiResourcesPayload = {
  pawns: ApiPawn[];
  scenarios: ApiScenario[];
  settings: ApiImportSettings;
};

type ApiComparisonRow = {
  scenarioId: string;
  scenarioName: string;
  attackerName: string;
  defenderName: string;
  weaponName: string;
  expectedDps: number;
  theoreticalDps: number;
  hitChancePercent: number;
  expectedDamageOnHit: number;
  armorReductionPercent: number;
  damageTakenMultiplier: number;
  distanceCells: number;
  outfitValid: boolean;
};

type ApiScenarioPreview = {
  row: ApiComparisonRow;
  metrics: {
    weaponName: string;
    hitChancePercent: number;
    expectedDps: number;
    theoreticalDps: number;
    expectedDamageOnHit: number;
    armorEfficiencyPercent: number;
    damageTakenMultiplier: number;
    distanceCells: number;
    outfitValid: boolean;
  };
};

const apiBaseUrl = window.rimBridge?.apiBaseUrl ?? "http://127.0.0.1:8765";
const root = document.querySelector("#root");

let activePage = "pawn";
let activeModule: PawnModule = "base";
let pawnNameValue = "";
let pawnShootingValue = "14";
let pawnQualityOptions: SelectOption[] = [{ id: "normal", label: "一般" }];
let pawnMaterialOptions: SelectOption[] = [{ id: "steel", label: "钢铁" }];
const selected: Record<PawnModule, string[]> = {
  base: [],
  traits: [],
  specials: [],
  implants: [],
  weapon: [],
  apparel: []
};

const pawnCatalog: PawnCatalog = {
  base: {
    title: "基础模板",
    desc: "决定这个预设是普通小人，还是用于测试承伤的简化靶子。",
    mode: "single",
    action: "应用基础模板",
    placeholder: "搜索基础模板",
    options: [{ id: "human_baseliner", name: "人类", defaultFullBodyArmorPercent: 0 }]
  },
  traits: {
    title: "特性",
    desc: "特性可以多选。",
    mode: "multi",
    action: "加入选中特性",
    placeholder: "搜索特性",
    options: []
  },
  specials: {
    title: "特殊装备",
    desc: "特殊装备用于模拟射击相关装备增益。",
    mode: "multi",
    action: "加入选中特殊装备",
    placeholder: "搜索特殊装备",
    options: []
  },
  implants: {
    title: "植入体",
    desc: "植入体可以多选。",
    mode: "multi",
    action: "加入选中植入体",
    placeholder: "搜索植入体",
    options: []
  },
  weapon: {
    title: "武器选择",
    desc: "武器为单选，重新选择会替换当前人物武器。",
    mode: "single",
    action: "替换当前武器",
    placeholder: "搜索武器",
    options: []
  },
  apparel: {
    title: "衣着选择",
    desc: "衣着可以多选。",
    mode: "multi",
    action: "加入选中衣着",
    placeholder: "搜索衣着",
    options: []
  }
};

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || "API 请求失败");
  }
  return payload as T;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    const map: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    };
    return map[char];
  });
}

function formatFixed(value: unknown, digits = 2): string {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
}

function optionByName(module: PawnModule, name: string): PawnOption | undefined {
  return pawnCatalog[module].options.find((option) => option.name === name);
}

function selectedOptions(module: PawnModule): PawnOption[] {
  return selected[module].map((name) => optionByName(module, name)).filter(Boolean) as PawnOption[];
}

function setText(selector: string, value: string): void {
  const node = document.querySelector(selector);
  if (node) node.textContent = value;
}

function closeFloatingPopovers(except?: Element | null): void {
  document.querySelectorAll<HTMLElement>(".scene-popover.open").forEach((popover) => {
    if (except && popover === except) return;
    popover.classList.remove("open");
    popover.style.removeProperty("left");
    popover.style.removeProperty("top");
    popover.style.removeProperty("visibility");
  });
}

function openFloatingPopover(trigger: HTMLElement, popover: HTMLElement): void {
  const wasOpen = popover.classList.contains("open");
  closeFloatingPopovers(popover);
  if (wasOpen) {
    popover.classList.remove("open");
    return;
  }

  popover.classList.add("open");
  popover.style.visibility = "hidden";

  const margin = 8;
  const triggerRect = trigger.getBoundingClientRect();
  const popoverRect = popover.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const popoverWidth = Math.min(popoverRect.width, viewportWidth - margin * 2);
  const popoverHeight = Math.min(popoverRect.height, viewportHeight - margin * 2);

  let left = triggerRect.right + margin;
  let top = triggerRect.top;

  if (left + popoverWidth > viewportWidth - margin) {
    left = triggerRect.left;
    top = triggerRect.bottom + margin;
  }
  if (left + popoverWidth > viewportWidth - margin) {
    left = viewportWidth - popoverWidth - margin;
  }
  if (top + popoverHeight > viewportHeight - margin) {
    top = viewportHeight - popoverHeight - margin;
  }

  popover.style.left = `${Math.max(margin, left)}px`;
  popover.style.top = `${Math.max(margin, top)}px`;
  popover.style.visibility = "visible";
}

function filterListRows(listSelector: string, keyword: string): void {
  const normalized = keyword.trim().toLowerCase();
  const list = document.querySelector(listSelector);
  list?.querySelectorAll<HTMLElement>(".list-row").forEach((row) => {
    row.classList.toggle(
      "is-filtered-out",
      normalized.length > 0 && !row.textContent?.toLowerCase().includes(normalized),
    );
  });
}

function renderShell(): void {
  if (!root) return;
  const tabs = [
    ["pawn", "人物创建"],
    ["scene", "场景设计"],
    ["compare", "结果对比"],
    ["import", "数据导入"],
    ["resources", "资源管理"]
  ];
  root.innerHTML = `
    <main class="app">
      <header class="titlebar">
        <nav class="tabs">${tabs
          .map(
            ([id, label]) =>
              `<button class="${activePage === id ? "active" : ""}" data-page="${id}">${label}</button>`
          )
          .join("")}</nav>
      </header>
      <section id="page-root" class="page-root"></section>
    </main>
  `;
  document.querySelectorAll<HTMLButtonElement>("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      activePage = button.dataset.page ?? "pawn";
      renderShell();
      renderPage();
    });
  });
}

function renderPage(): void {
  if (activePage === "pawn") {
    renderPawnPage();
    return;
  }
  if (activePage === "scene") {
    renderScenePage();
    return;
  }
  if (activePage === "compare") {
    renderComparePage();
    return;
  }
  if (activePage === "import") {
    renderImportPage();
    return;
  }
  if (activePage === "resources") {
    renderResourcePage();
  }
}

function slotHtml(module: PawnModule): string {
  const values = selected[module].length > 0 ? selected[module].map((value) => selectedSlotLabel(module, value)) : ["无"];
  return values
    .map(
      (value, index) =>
        `<span data-slot-module="${module}" data-slot-value="${escapeHtml(
          selected[module][index] ?? ""
        )}">${escapeHtml(value)}</span>`
    )
    .join("");
}

function selectedSlotLabel(module: PawnModule, value: string): string {
  const option = optionByName(module, value);
  if (!option) return value;
  if ((module !== "weapon" && module !== "apparel") || !option.choice) return option.name;
  const quality = pawnQualityOptions.find((item) => item.id === option.choice?.quality_id)?.label ?? "一般";
  const material =
    option.supportsMaterial && option.choice.material_id
      ? pawnMaterialOptions.find((item) => item.id === option.choice?.material_id)?.label ?? option.choice.material_id
      : "";
  return material ? `${option.name} / ${quality} / ${material}` : `${option.name} / ${quality}`;
}

function renderPawnPage(): void {
  const pageRoot = document.querySelector("#page-root");
  if (!pageRoot) return;
  pageRoot.innerHTML = `
    <section class="pawn-page">
      <aside class="pawn-current">
        <section class="pawn-block">
          <h1>人物创建</h1>
          <p>像组装装备一样创建测试小人。先选模板，再添加特性、武器、衣着和植入体。</p>
        </section>
        <label class="pawn-field">
          <span>小人模板名称</span>
          <input id="pawnName" value="${escapeHtml(pawnNameValue)}" />
        </label>
        <label class="pawn-field compact-input">
          <span>射击等级</span>
          <input id="pawnShooting" value="${escapeHtml(pawnShootingValue)}" />
        </label>
        <section class="pawn-module-stack">
          ${moduleButton("base", "基础模板")}
          <div class="pawn-selected-slot" id="pawn-slot-base">${slotHtml("base")}</div>
          ${moduleButton("traits", "特性")}
          <div class="pawn-selected-slot" id="pawn-slot-traits">${slotHtml("traits")}</div>
          ${moduleButton("specials", "特殊装备")}
          <div class="pawn-selected-slot" id="pawn-slot-specials">${slotHtml("specials")}</div>
          ${moduleButton("implants", "植入体")}
          <div class="pawn-selected-slot" id="pawn-slot-implants">${slotHtml("implants")}</div>
          ${moduleButton("weapon", "武器选择")}
          <div class="pawn-selected-slot" id="pawn-slot-weapon">${slotHtml("weapon")}</div>
          ${moduleButton("apparel", "衣着选择")}
          <div class="pawn-selected-slot" id="pawn-slot-apparel">${slotHtml("apparel")}</div>
        </section>
        <section class="button-grid one pawn-actions">
          <button class="confirm" id="pawn-save">保存为新人物</button>
          <div class="scene-menu-anchor pawn-output-anchor">
            <button id="pawn-output-toggle">实时输出能力</button>
            <div class="scene-popover pawn-output-popover" id="pawn-output-popover" aria-label="实时输出能力">
              <div class="pawn-output-head">
                <h2>实时输出能力</h2>
              </div>
              <section class="pawn-output-grid">
                ${outputCard("当前武器", "pawn-output-weapon", "等待计算")}
                ${outputCard("最佳精度档", "pawn-output-best-distance", "-")}
                ${outputCard("最佳距离命中", "pawn-output-best-hit", "-")}
                ${outputCard("0% 护甲 DPS", "pawn-output-dps-0", "-")}
                ${outputCard("20% 护甲 DPS", "pawn-output-dps-20", "-")}
                ${outputCard("40% 护甲 DPS", "pawn-output-dps-40", "-")}
                ${outputCard("70% 护甲 DPS", "pawn-output-dps-70", "-")}
                ${outputCard("100% 护甲 DPS", "pawn-output-dps-100", "-")}
                ${outputCard("瞄准时间", "pawn-output-warmup", "-")}
                ${outputCard("冷却时间", "pawn-output-cooldown", "-")}
              </section>
            </div>
          </div>
        </section>
        <div class="status-line" id="pawn-status"></div>
      </aside>
    </section>
  `;
  bindPawnPage();
}

function moduleButton(module: PawnModule, label: string): string {
  const catalog = pawnCatalog[module];
  return `
    <div class="scene-menu-anchor pawn-menu-anchor">
      <button class="pawn-module-button ${activeModule === module ? "selected" : ""}" data-module="${module}" data-target="pawn-popover-${module}">${label}</button>
      <div class="scene-popover pawn-popover" id="pawn-popover-${module}" aria-label="${escapeHtml(label)}选择菜单">
        <div class="pawn-popover-head">
          <h2>${escapeHtml(catalog.title)}</h2>
          <p>${escapeHtml(catalog.desc)}</p>
        </div>
        <label class="search-box">
          <span>搜索</span>
          <input class="pawn-option-search" data-module="${module}" data-target="pawn-option-list-${module}" type="search" placeholder="${escapeHtml(catalog.placeholder)}" />
        </label>
        ${equipmentControlsHtml(module)}
        <div class="pawn-picker-body">
          <div class="rim-list scene-menu-list pawn-option-list" id="pawn-option-list-${module}" data-module="${module}"></div>
          <div class="detail-card pawn-option-detail" id="pawn-option-detail-${module}"></div>
        </div>
      </div>
    </div>
  `;
}

function outputCard(label: string, id: string, value: string): string {
  return `<article class="pawn-output-card"><span>${label}</span><strong id="${id}">${value}</strong></article>`;
}

function equipmentControlsHtml(module: PawnModule): string {
  if (module !== "weapon" && module !== "apparel") return "";
  return `
    <section class="equipment-controls" data-module="${module}">
      <label>
        <span>品质</span>
        <select class="equipment-quality" data-module="${module}">
          ${selectOptionsHtml(pawnQualityOptions, "normal")}
        </select>
      </label>
      <label>
        <span>材质</span>
        <select class="equipment-material" data-module="${module}">
          ${selectOptionsHtml(pawnMaterialOptions, "steel")}
        </select>
      </label>
    </section>
  `;
}

function selectOptionsHtml(options: SelectOption[], selectedId: string): string {
  return options
    .map(
      (option) =>
        `<option value="${escapeHtml(option.id)}" ${
          option.id === selectedId ? "selected" : ""
        }>${escapeHtml(option.label)}</option>`
    )
    .join("");
}

function bindPawnPage(): void {
  document.querySelectorAll<HTMLButtonElement>(".pawn-module-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      activeModule = (button.dataset.module as PawnModule) ?? "base";
      renderOptionList(activeModule);
      renderOptionDetail(activeModule, selected[activeModule][0] ?? pawnCatalog[activeModule].options[0]?.name);
      syncEquipmentControls(activeModule, selected[activeModule][0] ?? pawnCatalog[activeModule].options[0]?.name);
      document.querySelectorAll(".pawn-module-button").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
      const popover = document.querySelector(`#${button.dataset.target}`);
      if (popover instanceof HTMLElement) {
        openFloatingPopover(button, popover);
      }
    });
  });

  document.querySelector(".pawn-current")?.addEventListener("click", (event) => {
    const item = (event.target as HTMLElement).closest<HTMLElement>(".pawn-selected-slot span");
    if (!item || item.textContent?.trim() === "无") return;
    item.classList.toggle("selected");
  });

  document.querySelectorAll<HTMLElement>(".pawn-option-list").forEach((list) => {
    list.addEventListener("click", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".list-row");
      if (!row?.dataset.name) return;
      event.stopPropagation();
      const module = (list.dataset.module as PawnModule | undefined) ?? activeModule;
      selectPawnOption(module, row.dataset.name);
    });
    list.addEventListener("dblclick", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".list-row");
      if (!row?.dataset.name) return;
      event.stopPropagation();
      const module = (list.dataset.module as PawnModule | undefined) ?? activeModule;
      selectPawnOption(module, row.dataset.name, { forceSelected: true });
      closeFloatingPopovers();
    });
  });

  document.querySelectorAll<HTMLInputElement>(".pawn-option-search").forEach((input) => {
    input.addEventListener("input", () => {
      const module = (input.dataset.module as PawnModule | undefined) ?? activeModule;
      renderOptionList(module, input.value);
    });
  });

  document.querySelectorAll(".pawn-popover").forEach((popover) => {
    popover.addEventListener("click", (event) => event.stopPropagation());
  });
  document.querySelector("#pawn-output-popover")?.addEventListener("click", (event) => event.stopPropagation());
  document.querySelector("#page-root")?.addEventListener("click", () => closeFloatingPopovers());

  document.querySelector<HTMLInputElement>("#pawnName")?.addEventListener("input", (event) => {
    pawnNameValue = (event.target as HTMLInputElement).value;
  });
  document.querySelector<HTMLInputElement>("#pawnShooting")?.addEventListener("input", (event) => {
    pawnShootingValue = (event.target as HTMLInputElement).value;
    refreshFirepowerPreview();
  });

  document.querySelector("#pawn-save")?.addEventListener("click", async () => {
    try {
      const result = await apiJson<{ pawn: ApiPawn; savedCount?: number; skippedCount?: number; message?: string }>("/api/pawns/save", {
        method: "POST",
        body: JSON.stringify({ ...currentPawnPayload(), saveAsNew: true }),
      });
      setText(
        "#pawn-status",
        result.message ??
          (result.skippedCount ? `已跳过 1 个重复人物：${result.pawn.name}` : `已保存为 ${result.pawn.name}`)
      );
    } catch (error) {
      setText("#pawn-status", error instanceof Error ? error.message : "保存人物失败。");
    }
  });

  document.querySelector("#pawn-output-toggle")?.addEventListener("click", (event) => {
    event.stopPropagation();
    const trigger = document.querySelector<HTMLElement>("#pawn-output-toggle");
    const popover = document.querySelector<HTMLElement>("#pawn-output-popover");
    if (trigger && popover) {
      openFloatingPopover(trigger, popover);
      refreshFirepowerPreview();
    }
  });

  document.querySelectorAll<HTMLSelectElement>(".equipment-quality, .equipment-material").forEach((select) => {
    select.addEventListener("change", () => {
      const module = (select.dataset.module as PawnModule | undefined) ?? activeModule;
      applyEquipmentChoice(module);
      updateSelectedSlot(module);
      refreshFirepowerPreview();
    });
  });

  refreshFirepowerPreview();
}

function selectPawnOption(
  module: PawnModule,
  name: string,
  options: { forceSelected?: boolean } = {},
): void {
  const catalog = pawnCatalog[module];
  if (catalog.mode === "single") {
    selected[module] = [name];
    applyEquipmentChoiceToOption(module, name);
  } else if (options.forceSelected) {
    selected[module] = Array.from(new Set([...selected[module], name]));
    applyEquipmentChoiceToOption(module, name);
  } else if (selected[module].includes(name)) {
    selected[module] = selected[module].filter((item) => item !== name);
  } else {
    selected[module] = Array.from(new Set([...selected[module], name]));
    applyEquipmentChoiceToOption(module, name);
  }
  renderOptionList(module);
  renderOptionDetail(module, name);
  syncEquipmentControls(module, name);
  updateSelectedSlot(module);
  refreshFirepowerPreview();
}

function renderOptionList(module: PawnModule, keyword = ""): void {
  const list = document.querySelector(`#pawn-option-list-${module}`);
  if (!list) return;
  const normalized = keyword.trim().toLowerCase();
  list.innerHTML = pawnCatalog[module].options
    .filter((option) => !normalized || option.name.toLowerCase().includes(normalized))
    .map(
      (option) =>
        `<button class="list-row ${selected[module].includes(option.name) ? "selected" : ""}" data-name="${escapeHtml(option.name)}">${escapeHtml(option.name)}</button>`
    )
    .join("");
}

function renderOptionDetail(module: PawnModule, name?: string): void {
  const detail = document.querySelector(`#pawn-option-detail-${module}`);
  const option = name ? optionByName(module, name) : undefined;
  const rows = option?.detail ?? [["说明", "选择左侧条目查看详情。"]];
  if (!detail) return;
  detail.innerHTML = `<dl>${rows
    .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("")}</dl>`;
}

function syncEquipmentControls(module: PawnModule, name?: string): void {
  if (module !== "weapon" && module !== "apparel") return;
  const option = name ? optionByName(module, name) : undefined;
  const quality = document.querySelector<HTMLSelectElement>(`#pawn-popover-${module} .equipment-quality`);
  const material = document.querySelector<HTMLSelectElement>(`#pawn-popover-${module} .equipment-material`);
  if (quality) quality.value = option?.choice?.quality_id ?? "normal";
  if (material) {
    material.value = option?.choice?.material_id ?? "steel";
    material.disabled = !option?.supportsMaterial;
  }
}

function applyEquipmentChoice(module: PawnModule): void {
  if (module !== "weapon" && module !== "apparel") return;
  selected[module].forEach((name) => applyEquipmentChoiceToOption(module, name));
}

function applyEquipmentChoiceToOption(module: PawnModule, name: string): void {
  if (module !== "weapon" && module !== "apparel") return;
  const option = optionByName(module, name);
  if (!option?.choice) return;
  const qualityId = document.querySelector<HTMLSelectElement>(`#pawn-popover-${module} .equipment-quality`)?.value ?? "normal";
  const materialId = document.querySelector<HTMLSelectElement>(`#pawn-popover-${module} .equipment-material`)?.value ?? "steel";
  option.choice.quality_id = qualityId;
  option.choice.material_id = option.supportsMaterial ? materialId : null;
}

function updateSelectedSlot(module: PawnModule): void {
  const slot = document.querySelector(`#pawn-slot-${module}`);
  if (slot) slot.innerHTML = slotHtml(module);
}

type DetailItem = {
  id: string;
  label: string;
  detail: OptionDetail[];
};

type ScenePawnOption = {
  name: string;
  roleText: string;
  detail: OptionDetail[];
};

type CompareSceneResult = {
  scene: string;
  attacker: string;
  defender: string;
  distance: string;
  hit: string;
  cycle: string;
  expectedDamage: string;
  theoryDps: string;
  realDps: string;
  armorEfficiency: string;
  note: string;
};

const resourcePawns: DetailItem[] = [
  {
    id: "pawn-1",
    label: "射击+大师狙 · 774595",
    detail: [
      ["名称", "射击+大师狙"],
      ["基础模板", "人类"],
      ["射击等级", "14"],
      ["全身护甲", "0%"],
      ["特性", "射击指令"],
      ["特殊装备", "无"],
      ["植入体", "无"],
      ["武器", "大师 狙击步枪/vanilla"],
      ["衣着", "无"]
    ]
  },
  {
    id: "pawn-2",
    label: "射击+大师狙+单仿生眼 · 484260",
    detail: [
      ["名称", "射击+大师狙+单仿生眼"],
      ["基础模板", "人类"],
      ["射击等级", "14"],
      ["植入体", "仿生眼"],
      ["武器", "大师 狙击步枪/vanilla"]
    ]
  },
  {
    id: "pawn-3",
    label: "射击+大师狙+单仿生眼+弹药带 · 331820",
    detail: [
      ["名称", "射击+大师狙+单仿生眼+弹药带"],
      ["基础模板", "人类"],
      ["射击等级", "14"],
      ["特殊装备", "重型弹药挎包"],
      ["植入体", "仿生眼"],
      ["武器", "大师 狙击步枪/vanilla"]
    ]
  },
  {
    id: "pawn-4",
    label: "射击+大师狙+双仿生眼 · 202797",
    detail: [
      ["名称", "射击+大师狙+双仿生眼"],
      ["基础模板", "人类"],
      ["射击等级", "14"],
      ["全身护甲", "0%"],
      ["特性", "射击指令"],
      ["特殊装备", "无"],
      ["植入体", "仿生眼、仿生眼"],
      ["武器", "大师 狙击步枪/vanilla"],
      ["衣着", "无"]
    ]
  },
  {
    id: "pawn-5",
    label: "射击+大师狙+双仿生眼+弹药带 · 944154",
    detail: [
      ["名称", "射击+大师狙+双仿生眼+弹药带"],
      ["基础模板", "人类"],
      ["射击等级", "14"],
      ["特殊装备", "重型弹药挎包"],
      ["植入体", "仿生眼、仿生眼"],
      ["武器", "大师 狙击步枪/vanilla"]
    ]
  },
  {
    id: "pawn-6",
    label: "靶70甲 · 588209",
    detail: [
      ["名称", "靶70甲"],
      ["基础模板", "重甲模板"],
      ["射击等级", "0"],
      ["全身护甲", "70%"],
      ["特性", "无"],
      ["特殊装备", "无"],
      ["植入体", "无"],
      ["武器", "无"],
      ["衣着", "无"]
    ]
  },
  {
    id: "pawn-7",
    label: "传奇速射机枪+射击指令 · 120544",
    detail: [
      ["名称", "传奇速射机枪+射击指令"],
      ["基础模板", "人类"],
      ["射击等级", "12"],
      ["特性", "射击指令"],
      ["武器", "传奇 速射机枪/vanilla"]
    ]
  },
  {
    id: "pawn-8",
    label: "大师速射机枪+乱开枪 · 982447",
    detail: [
      ["名称", "大师速射机枪+乱开枪"],
      ["基础模板", "人类"],
      ["射击等级", "12"],
      ["特性", "乱开枪"],
      ["武器", "大师 速射机枪/vanilla"]
    ]
  }
];

const resourceScenarios: DetailItem[] = [
  {
    id: "scenario-1",
    label: "射击+大师狙 VS 靶70甲 · 8526e0",
    detail: [
      ["场景名称", "射击+大师狙 VS 靶70甲"],
      ["攻击方", "射击+大师狙"],
      ["防守方", "靶70甲"],
      ["距离", "40"],
      ["最终命中率", "100%"],
      ["备注", "基础狙击测试场景。"]
    ]
  },
  {
    id: "scenario-2",
    label: "射击+大师狙+单仿生眼 VS 靶70甲 · 3d3f08",
    detail: [
      ["场景名称", "射击+大师狙+单仿生眼 VS 靶70甲"],
      ["攻击方", "射击+大师狙+单仿生眼"],
      ["防守方", "靶70甲"],
      ["距离", "40"],
      ["最终命中率", "100%"],
      ["备注", "单眼植入对照。"]
    ]
  },
  {
    id: "scenario-3",
    label: "射击+大师狙+单仿生眼+弹药带 VS 靶70甲 · b14fa2",
    detail: [
      ["场景名称", "射击+大师狙+单仿生眼+弹药带 VS 靶70甲"],
      ["攻击方", "射击+大师狙+单仿生眼+弹药带"],
      ["防守方", "靶70甲"],
      ["距离", "40"],
      ["最终命中率", "100%"],
      ["备注", "检查冷却缩短影响。"]
    ]
  },
  {
    id: "scenario-4",
    label: "射击+大师狙+双仿生眼 VS 靶70甲 · 1dd5a7",
    detail: [
      ["场景名称", "射击+大师狙+双仿生眼 VS 靶70甲"],
      ["攻击方", "射击+大师狙+双仿生眼"],
      ["防守方", "靶70甲"],
      ["距离", "40"],
      ["最终命中率", "100%"],
      ["备注", "用于检查远距离狙击武器打中甲目标的期望输出。"]
    ]
  },
  {
    id: "scenario-5",
    label: "射击+大师狙+双仿生眼+弹药带 VS 靶70甲 · f963c8",
    detail: [
      ["场景名称", "射击+大师狙+双仿生眼+弹药带 VS 靶70甲"],
      ["攻击方", "射击+大师狙+双仿生眼+弹药带"],
      ["防守方", "靶70甲"],
      ["距离", "40"],
      ["最终命中率", "100%"],
      ["备注", "高命中与低冷却组合。"]
    ]
  },
  {
    id: "scenario-6",
    label: "传奇速射机枪 VS 海军甲 · 0da732",
    detail: [
      ["场景名称", "传奇速射机枪 VS 海军甲"],
      ["攻击方", "传奇速射机枪+射击指令"],
      ["防守方", "海军动力甲靶"],
      ["距离", "25"],
      ["最终命中率", "100%"],
      ["备注", "重甲压制测试。"]
    ]
  },
  {
    id: "scenario-7",
    label: "大师速射机枪 VS 轻甲靶 · 4451ef",
    detail: [
      ["场景名称", "大师速射机枪 VS 轻甲靶"],
      ["攻击方", "大师速射机枪+乱开枪"],
      ["防守方", "轻甲靶20"],
      ["距离", "12"],
      ["最终命中率", "100%"],
      ["备注", "轻甲目标对照。"]
    ]
  }
];

let currentResourcePawns: DetailItem[] = resourcePawns;
let currentResourceScenarios: DetailItem[] = resourceScenarios;
let currentCompareScenarios: ApiScenario[] = [];
let selectedCompareSceneId = "sniper70";
let currentScenePawns: ApiPawn[] = [];

const compareSceneResults: Record<string, CompareSceneResult> = {
  sniper70: {
    scene: "狙击 VS 靶70甲",
    attacker: "大师狙击手",
    defender: "靶70甲",
    distance: "40",
    hit: "86%",
    cycle: "5.67秒",
    expectedDamage: "28.4",
    theoryDps: "5.91",
    realDps: "5.08",
    armorEfficiency: "76%",
    note: "远距离高穿甲参考"
  },
  minigun20: {
    scene: "大师速射机枪 VS 轻甲靶",
    attacker: "大师速射机枪手",
    defender: "靶20甲",
    distance: "12",
    hit: "72%",
    cycle: "3.18秒",
    expectedDamage: "14.6",
    theoryDps: "8.64",
    realDps: "6.22",
    armorEfficiency: "88%",
    note: "近中距离压制输出"
  },
  legendMinigun70: {
    scene: "传奇速射机枪 VS 靶70甲",
    attacker: "传奇速射机枪手",
    defender: "靶70甲",
    distance: "25",
    hit: "67%",
    cycle: "3.18秒",
    expectedDamage: "16.8",
    theoryDps: "9.52",
    realDps: "6.38",
    armorEfficiency: "71%",
    note: "高品质机枪对中甲"
  },
  chargeLanceMarine: {
    scene: "电荷长矛 VS 海军动力甲",
    attacker: "电荷长矛射手",
    defender: "海军动力甲",
    distance: "25",
    hit: "94%",
    cycle: "6.00秒",
    expectedDamage: "25.8",
    theoryDps: "4.58",
    realDps: "4.30",
    armorEfficiency: "69%",
    note: "高甲目标穿透测试"
  },
  rifleNaked: {
    scene: "突击步枪 VS 无甲靶",
    attacker: "突击步枪射手",
    defender: "无甲靶",
    distance: "12",
    hit: "98%",
    cycle: "2.80秒",
    expectedDamage: "11.0",
    theoryDps: "7.86",
    realDps: "7.70",
    armorEfficiency: "100%",
    note: "无甲输出基准"
  },
  sniper100: {
    scene: "狙击 VS 超重甲靶",
    attacker: "大师狙击手",
    defender: "靶100甲",
    distance: "40",
    hit: "86%",
    cycle: "5.67秒",
    expectedDamage: "20.3",
    theoryDps: "4.23",
    realDps: "3.64",
    armorEfficiency: "54%",
    note: "超重甲承伤参考"
  },
  minigunMarine: {
    scene: "大师速射机枪 VS 海军动力甲",
    attacker: "大师速射机枪手",
    defender: "海军动力甲",
    distance: "25",
    hit: "61%",
    cycle: "3.18秒",
    expectedDamage: "10.9",
    theoryDps: "6.46",
    realDps: "3.94",
    armorEfficiency: "52%",
    note: "重甲下的低穿甲衰减"
  },
  chargeRifle40: {
    scene: "电荷步枪 VS 中甲靶",
    attacker: "电荷步枪射手",
    defender: "靶40甲",
    distance: "25",
    hit: "88%",
    cycle: "2.90秒",
    expectedDamage: "13.1",
    theoryDps: "9.03",
    realDps: "7.94",
    armorEfficiency: "82%",
    note: "中距离稳定输出"
  },
  revolver20: {
    scene: "左轮手枪 VS 轻甲靶",
    attacker: "左轮手枪射手",
    defender: "靶20甲",
    distance: "12",
    hit: "63%",
    cycle: "2.10秒",
    expectedDamage: "8.7",
    theoryDps: "4.14",
    realDps: "2.61",
    armorEfficiency: "91%",
    note: "低级武器对照组"
  }
};

const compareSceneOrder = [
  "sniper70",
  "minigun20",
  "legendMinigun70",
  "chargeLanceMarine",
  "rifleNaked",
  "sniper100",
  "minigunMarine",
  "chargeRifle40",
  "revolver20"
];

const scenePawnOptions: ScenePawnOption[] = [
  {
    name: "射击+大师狙+双仿生眼",
    roleText: "攻击方候选",
    detail: [
      ["人物", "射击+大师狙+双仿生眼"],
      ["类型", "攻击方候选"],
      ["武器", "大师 狙击步枪 / vanilla"],
      ["射击", "14"],
      ["护甲", "0%"]
    ]
  },
  {
    name: "射击+大师狙+单仿生眼+弹药挎包",
    roleText: "攻击方候选",
    detail: [
      ["人物", "射击+大师狙+单仿生眼+弹药挎包"],
      ["类型", "攻击方候选"],
      ["武器", "大师 狙击步枪 / vanilla"],
      ["射击", "14"],
      ["特殊装备", "重型弹药挎包"]
    ]
  },
  {
    name: "传奇速射机枪+射击指令",
    roleText: "攻击方候选",
    detail: [
      ["人物", "传奇速射机枪+射击指令"],
      ["类型", "攻击方候选"],
      ["武器", "传奇 速射机枪 / vanilla"],
      ["射击", "12"],
      ["加成", "射击指令"]
    ]
  },
  {
    name: "大师速射机枪+弹药挎包",
    roleText: "攻击方候选",
    detail: [
      ["人物", "大师速射机枪+弹药挎包"],
      ["类型", "攻击方候选"],
      ["武器", "大师 速射机枪 / vanilla"],
      ["射击", "12"],
      ["特殊装备", "重型弹药挎包"]
    ]
  },
  {
    name: "电荷长矛射手",
    roleText: "攻击方候选",
    detail: [
      ["人物", "电荷长矛射手"],
      ["类型", "攻击方候选"],
      ["武器", "电荷长矛 / vanilla"],
      ["射击", "14"],
      ["护甲", "0%"]
    ]
  },
  {
    name: "无甲靶",
    roleText: "防守方候选",
    detail: [
      ["人物", "无甲靶"],
      ["类型", "防守方候选"],
      ["护甲", "0%"],
      ["衣着", "无"],
      ["用途", "无甲输出基准"]
    ]
  },
  {
    name: "轻甲靶20",
    roleText: "防守方候选",
    detail: [
      ["人物", "轻甲靶20"],
      ["类型", "防守方候选"],
      ["护甲", "20%"],
      ["衣着", "轻甲模板"],
      ["用途", "轻甲承伤参考"]
    ]
  },
  {
    name: "靶70甲",
    roleText: "防守方候选",
    detail: [
      ["人物", "靶70甲"],
      ["类型", "防守方候选"],
      ["护甲", "70%"],
      ["衣着", "中重甲模板"],
      ["用途", "重甲承伤参考"]
    ]
  },
  {
    name: "海军动力甲靶",
    roleText: "防守方候选",
    detail: [
      ["人物", "海军动力甲靶"],
      ["类型", "防守方候选"],
      ["护甲", "100%"],
      ["衣着", "海军动力甲、海军头盔"],
      ["用途", "超重甲承伤参考"]
    ]
  }
];

function detailHtml(rows: OptionDetail[]): string {
  return `<dl>${rows
    .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("")}</dl>`;
}

function listRowsHtml(items: DetailItem[], selectedId?: string): string {
  return items
    .map(
      (item) =>
        `<button class="list-row ${item.id === selectedId ? "selected" : ""}" data-detail="${escapeHtml(
          item.id
        )}">${escapeHtml(item.label)}</button>`
    )
    .join("");
}

function compareSceneButtonHtml(sceneId: string, selectedId?: string): string {
  const result = compareSceneResults[sceneId];
  const label = `${result.scene} · ${result.distance}格`;
  return `<button class="list-row compare-scene-row ${
    sceneId === selectedId ? "selected" : ""
  }" data-scene-id="${escapeHtml(sceneId)}" data-label="${escapeHtml(label)}">${escapeHtml(label)}</button>`;
}

function compareTableRowHtml(sceneId: string): string {
  const result = compareSceneResults[sceneId];
  return `
    <tr data-scene-id="${escapeHtml(sceneId)}">
      <td>${escapeHtml(result.scene)}</td>
      <td>${escapeHtml(result.attacker)}</td>
      <td>${escapeHtml(result.defender)}</td>
      <td>${escapeHtml(result.distance)}</td>
      <td>${escapeHtml(result.hit)}</td>
      <td>${escapeHtml(result.cycle)}</td>
      <td>${escapeHtml(result.expectedDamage)}</td>
      <td>${escapeHtml(result.theoryDps)}</td>
      <td>${escapeHtml(result.realDps)}</td>
      <td>${escapeHtml(result.armorEfficiency)}</td>
      <td>${escapeHtml(result.note)}</td>
    </tr>
  `;
}

function apiScenarioButtonHtml(scenario: ApiScenario, selectedId?: string): string {
  const label = `${scenario.name} · ${scenario.distanceCells}格`;
  return `<button class="list-row compare-scene-row ${
    scenario.id === selectedId ? "selected" : ""
  }" data-scene-id="${escapeHtml(scenario.id)}" data-label="${escapeHtml(label)}">${escapeHtml(label)}</button>`;
}

function apiCompareTableRowHtml(row: ApiComparisonRow): string {
  const armorEfficiency = Math.max(0, 100 - row.armorReductionPercent);
  return `
    <tr data-scene-id="${escapeHtml(row.scenarioId)}">
      <td>${escapeHtml(row.scenarioName)}</td>
      <td>${escapeHtml(row.attackerName)}</td>
      <td>${escapeHtml(row.defenderName)}</td>
      <td>${row.distanceCells}</td>
      <td>${formatFixed(row.hitChancePercent, 0)}%</td>
      <td>-</td>
      <td>${formatFixed(row.expectedDamageOnHit)}</td>
      <td>${formatFixed(row.theoreticalDps)}</td>
      <td>${formatFixed(row.expectedDps)}</td>
      <td>${formatFixed(armorEfficiency, 0)}%</td>
      <td>${row.outfitValid ? "穿戴合法" : "穿戴冲突"}</td>
    </tr>
  `;
}

function scenePawnRowsFromApiHtml(selectedId?: string): string {
  if (currentScenePawns.length === 0) {
    return scenePawnRowsHtml();
  }
  return currentScenePawns
    .map(
      (pawn) =>
        `<button class="list-row scene-pawn-row ${
          pawn.id === selectedId ? "selected" : ""
        }" data-pawn-id="${escapeHtml(pawn.id)}" data-name="${escapeHtml(pawn.name)}">${escapeHtml(
          `${pawn.name} · ${pawn.weaponName || pawn.speciesLabel}`
        )}</button>`
    )
    .join("");
}

function mobileScenePawnRowsFromApiHtml(role: "attacker" | "defender", selectedId?: string): string {
  if (currentScenePawns.length === 0) {
    return mobileScenePawnRowsHtml(role, role === "attacker" ? "射击+大师狙+双仿生眼" : "靶70甲");
  }
  const candidates =
    role === "attacker"
      ? currentScenePawns.filter((pawn) => pawn.weaponName && pawn.weaponName !== "无")
      : currentScenePawns;
  return candidates
    .map(
      (pawn) =>
        `<button class="list-row scene-mobile-pawn ${
          pawn.id === selectedId ? "selected" : ""
        }" data-role="${role}" data-pawn-id="${escapeHtml(pawn.id)}" data-name="${escapeHtml(
          pawn.name
        )}">${escapeHtml(pawn.name)}</button>`
    )
    .join("");
}

function renderResourcePage(): void {
  const pageRoot = document.querySelector("#page-root");
  if (!pageRoot) return;
  pageRoot.innerHTML = `
    <section class="resource-page">
      <section class="resource-column">
        <div class="panel-head">
          <div>
            <h1>已保存人物</h1>
            <p>支持载入编辑、重命名和删除预设。</p>
          </div>
          <label class="search-box">
            <span>搜索</span>
            <input class="resource-search" data-target="pawn-list" type="search" placeholder="人物名称" />
          </label>
        </div>
        <div class="rim-list" id="pawn-list" aria-label="已保存人物列表">
          ${listRowsHtml(resourcePawns, "pawn-4")}
        </div>
        <div class="detail-card" id="pawn-detail">${detailHtml(resourcePawns[3].detail)}</div>
        <div class="button-grid three">
          <button id="load-selected-pawn">载入到人物创建页</button>
          <button>重命名选中人物</button>
          <button class="danger" id="delete-selected-pawn">删除选中人物</button>
        </div>
        <div class="status-line resource-column-status" id="pawn-resource-status"></div>
      </section>

      <section class="resource-column">
        <div class="panel-head">
          <div>
            <h1>已保存场景</h1>
            <p>管理已经保存的人物对战和承伤测试场景。</p>
          </div>
          <label class="search-box">
            <span>搜索</span>
            <input class="resource-search" data-target="scenario-list" type="search" placeholder="场景名称" />
          </label>
        </div>
        <div class="rim-list" id="scenario-list" aria-label="已保存场景列表">
          ${listRowsHtml(resourceScenarios, "scenario-4")}
        </div>
        <div class="detail-card" id="scenario-detail">${detailHtml(resourceScenarios[3].detail)}</div>
        <div class="button-grid three">
          <button id="load-selected-scenario">载入到场景设计页</button>
          <button>重命名选中场景</button>
          <button class="danger" id="delete-selected-scenario">删除选中场景</button>
        </div>
        <div class="button-grid one">
          <button class="wide" id="delete-duplicate-scenarios">清理重复场景</button>
        </div>
        <div class="status-line resource-column-status" id="scenario-resource-status"></div>
      </section>
    </section>
  `;
  bindResourcePage();
  loadResourcePageData();
}

function bindResourcePage(): void {
  const selectedId = (listId: string): string | undefined =>
    document.querySelector<HTMLElement>(`#${listId} .list-row.selected`)?.dataset.detail;

  const bindList = (
    listId: string,
    detailId: string,
    itemsProvider: () => DetailItem[],
  ): void => {
    const list = document.querySelector(`#${listId}`);
    const detail = document.querySelector(`#${detailId}`);
    list?.addEventListener("click", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".list-row");
      if (!row?.dataset.detail) return;
      list.querySelectorAll(".list-row").forEach((item) => item.classList.remove("selected"));
      row.classList.add("selected");
      const item = itemsProvider().find((candidate) => candidate.id === row.dataset.detail);
      if (detail && item) detail.innerHTML = detailHtml(item.detail);
    });
  };

  bindList("pawn-list", "pawn-detail", () => currentResourcePawns);
  bindList("scenario-list", "scenario-detail", () => currentResourceScenarios);

  document.querySelectorAll<HTMLInputElement>(".resource-search").forEach((input) => {
    input.addEventListener("input", () => {
      const keyword = input.value.trim().toLowerCase();
      const list = document.querySelector(`#${input.dataset.target}`);
      list?.querySelectorAll<HTMLElement>(".list-row").forEach((row) => {
        row.hidden = keyword.length > 0 && !row.textContent?.toLowerCase().includes(keyword);
      });
    });
  });

  document.querySelector("#delete-selected-pawn")?.addEventListener("click", async () => {
    const id = selectedId("pawn-list");
    if (!id) {
      setText("#pawn-resource-status", "请先选择要删除的人物。");
      return;
    }
    try {
      await apiJson("/api/pawns/delete", {
        method: "POST",
        body: JSON.stringify({ id }),
      });
      setText("#pawn-resource-status", "已删除选中人物。");
      await loadResourcePageData();
    } catch (error) {
      setText("#pawn-resource-status", error instanceof Error ? error.message : "删除人物失败。");
    }
  });

  document.querySelector("#delete-selected-scenario")?.addEventListener("click", async () => {
    const id = selectedId("scenario-list");
    if (!id) {
      setText("#scenario-resource-status", "请先选择要删除的场景。");
      return;
    }
    try {
      await apiJson("/api/scenarios/delete", {
        method: "POST",
        body: JSON.stringify({ id }),
      });
      setText("#scenario-resource-status", "已删除选中场景。");
      await loadResourcePageData();
    } catch (error) {
      setText("#scenario-resource-status", error instanceof Error ? error.message : "删除场景失败。");
    }
  });

  document.querySelector("#delete-duplicate-scenarios")?.addEventListener("click", async () => {
    try {
      const result = await apiJson<{ deletedCount: number }>("/api/scenarios/delete-duplicates", {
        method: "POST",
        body: "{}",
      });
      setText("#scenario-resource-status", `已清理 ${result.deletedCount} 个重复场景。`);
      await loadResourcePageData();
    } catch (error) {
      setText(
        "#scenario-resource-status",
        error instanceof Error ? error.message : "清理重复场景失败。",
      );
    }
  });

  document.querySelector("#load-selected-pawn")?.addEventListener("click", () => {
    activePage = "pawn";
    renderShell();
    renderPage();
  });

  document.querySelector("#load-selected-scenario")?.addEventListener("click", () => {
    activePage = "scene";
    renderShell();
    renderPage();
  });
}

async function loadResourcePageData(): Promise<void> {
  try {
    const result = await apiJson<ApiResourcesPayload>("/api/resources");
    currentResourcePawns = result.pawns;
    currentResourceScenarios = result.scenarios;
    currentScenePawns = result.pawns;
    currentCompareScenarios = result.scenarios;
    const pawnList = document.querySelector("#pawn-list");
    const scenarioList = document.querySelector("#scenario-list");
    const pawnDetail = document.querySelector("#pawn-detail");
    const scenarioDetail = document.querySelector("#scenario-detail");
    if (pawnList) {
      pawnList.innerHTML =
        currentResourcePawns.length > 0
          ? listRowsHtml(currentResourcePawns, currentResourcePawns[0].id)
          : `<button class="list-row">暂无已保存人物</button>`;
    }
    if (scenarioList) {
      scenarioList.innerHTML =
        currentResourceScenarios.length > 0
          ? listRowsHtml(currentResourceScenarios, currentResourceScenarios[0].id)
          : `<button class="list-row">暂无已保存场景</button>`;
    }
    if (pawnDetail) {
      pawnDetail.innerHTML = detailHtml(
        currentResourcePawns[0]?.detail ?? [["说明", "还没有保存人物。"]]
      );
    }
    if (scenarioDetail) {
      scenarioDetail.innerHTML = detailHtml(
        currentResourceScenarios[0]?.detail ?? [["说明", "还没有保存场景。"]]
      );
    }
  } catch (error) {
    currentResourcePawns = resourcePawns;
    currentResourceScenarios = resourceScenarios;
  }
}

function renderImportPage(): void {
  const pageRoot = document.querySelector("#page-root");
  if (!pageRoot) return;
  pageRoot.innerHTML = `
    <section class="import-page">
      <aside class="import-sidebar">
        <section class="import-block">
          <h1>数据导入</h1>
        </section>

        <section class="path-stack">
          <div class="path-picker">
            <label for="gameDataPath">游戏 Data 目录</label>
            <div class="path-row">
              <input id="gameDataPath" value="E:\\SteamLibrary\\steamapps\\common\\RimWorld\\Data" />
              <button>选择</button>
            </div>
          </div>
          <div class="path-picker muted-path">
            <label for="workshopPath">Steam 创意工坊目录</label>
            <div class="path-row">
              <input id="workshopPath" value="E:\\SteamLibrary\\steamapps\\workshop\\content\\294100" />
              <button>选择</button>
            </div>
          </div>
        </section>

        <section class="button-grid two import-actions">
          <button>自动检测路径</button>
          <button class="confirm" id="import-vanilla-data">导入原版数据</button>
        </section>
        <div class="status-line">第一版仅支持原版游戏数据导入。</div>
      </aside>

      <section class="import-main">
        <section class="metric-strip" aria-label="导入摘要">
          <article class="metric-card"><span>当前目录</span><strong id="import-current-status">等待导入</strong></article>
          <article class="metric-card"><span>武器数量</span><strong id="import-weapon-count">-</strong></article>
          <article class="metric-card"><span>衣着数量</span><strong id="import-apparel-count">-</strong></article>
          <article class="metric-card"><span>植入体数量</span><strong id="import-implant-count">-</strong></article>
          <article class="metric-card"><span>导入时间</span><strong id="import-time">-</strong></article>
        </section>

      </section>
    </section>
  `;
  bindImportPage();
  loadImportSettings();
}

function bindImportPage(): void {
  document.querySelector("#import-vanilla-data")?.addEventListener("click", async () => {
    const gameDataRoot = document.querySelector<HTMLInputElement>("#gameDataPath")?.value ?? "";
    const workshopRoot = document.querySelector<HTMLInputElement>("#workshopPath")?.value ?? "";
    try {
      const result = await apiJson<{ settings: ApiImportSettings }>("/api/import/catalog", {
        method: "POST",
        body: JSON.stringify({ gameDataRoot, workshopRoot }),
      });
      updateImportSettings(result.settings);
      setText(".status-line", "导入成功。人物创建、场景设计和结果对比页现在都可以使用。");
    } catch (error) {
      setText(".status-line", error instanceof Error ? error.message : "导入失败。");
    }
  });
}

function updateImportSettings(settings: ApiImportSettings): void {
  const gameInput = document.querySelector<HTMLInputElement>("#gameDataPath");
  const workshopInput = document.querySelector<HTMLInputElement>("#workshopPath");
  if (gameInput && settings.gameDataRoot) gameInput.value = settings.gameDataRoot;
  if (workshopInput && settings.workshopRoot) workshopInput.value = settings.workshopRoot;
  setText("#import-current-status", settings.gameDataRoot ? "原版数据已导入" : "等待导入");
  setText("#import-weapon-count", String(settings.catalogWeaponCount || "-"));
  setText("#import-apparel-count", String(settings.catalogApparelCount || "-"));
  setText("#import-implant-count", String(settings.catalogImplantCount || "-"));
  setText("#import-time", settings.lastImportedAt || "-");
}

async function loadImportSettings(): Promise<void> {
  try {
    const result = await apiJson<{ settings: ApiImportSettings }>("/api/import/settings");
    updateImportSettings(result.settings);
  } catch (error) {
    setText(".status-line", "本地 API 未连接，暂时只能查看静态页面。");
  }
}

function renderComparePage(): void {
  const pageRoot = document.querySelector("#page-root");
  if (!pageRoot) return;
  pageRoot.innerHTML = `
    <section class="compare-page">
      <aside class="compare-sidebar">
        <div class="panel-head compact-head">
          <div>
            <h1>场景列表</h1>
            <p>从已保存场景中选择需要放入右侧表格比较的项目。</p>
          </div>
        </div>
        <label class="search-box">
          <span>搜索</span>
          <input class="compare-search" data-target="desktop-scene-list" type="search" placeholder="场景名称 / 攻击方 / 防守方" />
        </label>
        <div class="rim-list compare-scene-list" id="desktop-scene-list" aria-label="可导入场景列表">
          <button class="list-row">正在读取场景库...</button>
        </div>
        <div class="detail-card compare-detail">
          <dl>
            <div><dt>当前选中</dt><dd id="selected-scene-name">未选择场景</dd></div>
            <div><dt>用途</dt><dd>加入结果表后，用于横向比较命中、穿甲、期望伤害和 DPS。</dd></div>
            <div><dt>说明</dt><dd>这里读取资源管理中保存的真实场景。</dd></div>
          </dl>
        </div>
        <div class="button-grid two">
          <button class="confirm" id="add-selected-scene">加入对比表</button>
          <button class="danger" id="clear-compare-table">清空表格</button>
        </div>
      </aside>

      <section class="compare-main">
        <div class="mobile-import-bar scene-menu-anchor">
          <button id="scene-menu-toggle" class="confirm">导入场景</button>
          <button id="mobile-import-all-scenes">导入所有场景</button>
          <button id="mobile-clear-compare-table" class="danger">清空场景</button>
          <div class="scene-popover" id="scene-popover" aria-label="场景导入菜单">
            <label class="search-box">
              <span>搜索</span>
              <input class="compare-search" data-target="mobile-scene-list" type="search" placeholder="搜索场景" />
            </label>
            <div class="rim-list scene-menu-list" id="mobile-scene-list">
              <button class="list-row">正在读取场景库...</button>
            </div>
            <p class="popover-tip">单击加入比较表，再次单击取消。</p>
          </div>
        </div>

        <div class="compare-toolbar">
          <div>
            <h1>结果对比表</h1>
            <p>按场景横向比较输出与承伤结果，后续正式版支持按列升降序排序。</p>
          </div>
          <div class="metric-strip compare-metrics" aria-label="对比摘要">
            <article class="metric-card"><span>已加入</span><strong id="compare-count">0 个场景</strong></article>
            <article class="metric-card"><span>最高实战 DPS</span><strong id="best-dps">0.00</strong></article>
            <article class="metric-card"><span>最高命中率</span><strong id="best-hit">0%</strong></article>
          </div>
        </div>

        <div class="compare-table-wrap" aria-label="结果对比表">
          <table class="compare-table">
            <thead>
              <tr>
                <th>场景名称</th>
                <th>攻击方</th>
                <th>防守方</th>
                <th>距离</th>
                <th>命中率</th>
                <th>射击周期</th>
                <th>期望伤害</th>
                <th>理论 DPS</th>
                <th>实战 DPS</th>
                <th>穿甲效率</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody id="compare-table-body"></tbody>
          </table>
        </div>
      </section>
    </section>
  `;
  bindComparePage();
  loadCompareScenariosFromApi();
}

function bindComparePage(): void {
  const tableBody = document.querySelector("#compare-table-body");
  const scenePopover = document.querySelector("#scene-popover");
  selectedCompareSceneId =
    document.querySelector<HTMLElement>("#desktop-scene-list .compare-scene-row.selected")?.dataset
      .sceneId ?? "";
  if (!tableBody) return;

  const tableRowForScene = (sceneId: string): HTMLTableRowElement | undefined =>
    Array.from(tableBody.querySelectorAll<HTMLTableRowElement>("tr")).find((row) => row.dataset.sceneId === sceneId);

  const syncImportedSceneRows = (): void => {
    const importedSceneIds = new Set(
      Array.from(tableBody.querySelectorAll<HTMLTableRowElement>("tr"))
        .map((row) => row.dataset.sceneId)
        .filter((sceneId): sceneId is string => Boolean(sceneId))
    );
    document.querySelectorAll<HTMLButtonElement>("#mobile-scene-list .compare-scene-row").forEach((row) => {
      row.classList.toggle("selected", Boolean(row.dataset.sceneId && importedSceneIds.has(row.dataset.sceneId)));
    });
  };

  const updateSummary = (): void => {
    const rows = Array.from(tableBody.querySelectorAll("tr"));
    setText("#compare-count", `${rows.length} 个场景`);
    const dpsValues = rows
      .map((row) => Number.parseFloat(row.children[8]?.textContent ?? "0"))
      .filter(Number.isFinite);
    const hitValues = rows
      .map((row) => Number.parseFloat(row.children[4]?.textContent ?? "0"))
      .filter(Number.isFinite);
    setText("#best-dps", dpsValues.length > 0 ? Math.max(...dpsValues).toFixed(2) : "0.00");
    setText("#best-hit", hitValues.length > 0 ? `${Math.max(...hitValues).toFixed(0)}%` : "0%");
    syncImportedSceneRows();
  };

  const selectScene = (sceneId: string): void => {
    selectedCompareSceneId = sceneId;
    document.querySelectorAll<HTMLElement>("#desktop-scene-list .compare-scene-row").forEach((row) => {
      row.classList.toggle("selected", row.dataset.sceneId === sceneId);
    });
    const apiScenario = currentCompareScenarios.find((scenario) => scenario.id === sceneId);
    setText("#selected-scene-name", apiScenario?.name ?? "未选择场景");
  };

  const addScene = async (sceneId: string): Promise<void> => {
    if (tableRowForScene(sceneId)) return;
    if (!currentCompareScenarios.some((scenario) => scenario.id === sceneId)) {
      return;
    }
    const result = await apiJson<{ rows: ApiComparisonRow[]; errors: unknown[] }>("/api/compare/rows", {
      method: "POST",
      body: JSON.stringify({ scenarioIds: [sceneId] }),
    });
    if (result.rows[0]) {
      tableBody.insertAdjacentHTML("beforeend", apiCompareTableRowHtml(result.rows[0]));
      updateSummary();
    }
  };

  const toggleScene = async (sceneId: string): Promise<void> => {
    const existingRow = tableRowForScene(sceneId);
    if (existingRow) {
      existingRow.remove();
      updateSummary();
      return;
    }
    await addScene(sceneId);
  };

  const addAllScenes = async (): Promise<void> => {
    const sceneIds = currentCompareScenarios.map((scenario) => scenario.id);
    const missingSceneIds = sceneIds.filter((sceneId) => !tableRowForScene(sceneId));
    if (missingSceneIds.length === 0) {
      updateSummary();
      return;
    }
    const result = await apiJson<{ rows: ApiComparisonRow[]; errors: unknown[] }>("/api/compare/rows", {
      method: "POST",
      body: JSON.stringify({ scenarioIds: missingSceneIds }),
    });
    result.rows.forEach((row) => {
      if (!tableRowForScene(row.scenarioId)) {
        tableBody.insertAdjacentHTML("beforeend", apiCompareTableRowHtml(row));
      }
    });
    updateSummary();
  };

  const bindSceneList = (selector: string): void => {
    const list = document.querySelector(selector);
    list?.addEventListener("click", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".compare-scene-row");
      if (!row) return;
      const sceneId = row.dataset.sceneId;
      if (!sceneId) return;
      selectScene(sceneId);
      if (row.closest("#mobile-scene-list")) {
        event.stopPropagation();
        void toggleScene(sceneId);
      }
    });
    list?.addEventListener("dblclick", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".compare-scene-row");
      if (!row) return;
      event.stopPropagation();
      if (row.dataset.sceneId) void addScene(row.dataset.sceneId);
      if (row.closest("#mobile-scene-list")) {
        closeFloatingPopovers();
      }
    });
  };

  bindSceneList("#desktop-scene-list");
  bindSceneList("#mobile-scene-list");

  document.querySelectorAll<HTMLInputElement>(".compare-search").forEach((input) => {
    input.addEventListener("input", () => {
      if (input.dataset.target) {
        filterListRows(`#${input.dataset.target}`, input.value);
      }
    });
  });

  document.querySelector("#add-selected-scene")?.addEventListener("click", () => {
    if (selectedCompareSceneId) void addScene(selectedCompareSceneId);
  });
  document.querySelector("#clear-compare-table")?.addEventListener("click", () => {
    tableBody.innerHTML = "";
    updateSummary();
  });
  document.querySelector("#mobile-clear-compare-table")?.addEventListener("click", () => {
    tableBody.innerHTML = "";
    updateSummary();
  });
  document.querySelector("#mobile-import-all-scenes")?.addEventListener("click", () => {
    void addAllScenes();
  });
  document.querySelector("#scene-menu-toggle")?.addEventListener("click", (event) => {
    event.stopPropagation();
    const trigger = event.currentTarget as HTMLElement;
    if (scenePopover instanceof HTMLElement) {
      openFloatingPopover(trigger, scenePopover);
    }
  });
  scenePopover?.addEventListener("click", (event) => event.stopPropagation());
  document.querySelector("#page-root")?.addEventListener("click", () => closeFloatingPopovers());
  updateSummary();
}

async function loadCompareScenariosFromApi(): Promise<void> {
  const desktopList = document.querySelector("#desktop-scene-list");
  const mobileList = document.querySelector("#mobile-scene-list");
  const tableBody = document.querySelector("#compare-table-body");
  const showEmptyScenarios = (message: string): void => {
    currentCompareScenarios = [];
    selectedCompareSceneId = "";
    const emptyRow = `<button class="list-row">${escapeHtml(message)}</button>`;
    if (desktopList) desktopList.innerHTML = emptyRow;
    if (mobileList) mobileList.innerHTML = emptyRow;
    tableBody?.replaceChildren();
    setText("#selected-scene-name", message);
    setText("#compare-count", "0 个场景");
    setText("#best-dps", "0.00");
    setText("#best-hit", "0%");
  };
  try {
    const result = await apiJson<{ scenarios: ApiScenario[] }>("/api/scenarios");
    currentCompareScenarios = result.scenarios;
    if (currentCompareScenarios.length === 0) {
      showEmptyScenarios("暂无已保存场景");
      return;
    }
    const firstId = currentCompareScenarios[0].id;
    selectedCompareSceneId = firstId;
    if (desktopList) {
      desktopList.innerHTML = currentCompareScenarios
        .map((scenario) => apiScenarioButtonHtml(scenario, firstId))
        .join("");
    }
    if (mobileList) {
      mobileList.innerHTML = currentCompareScenarios.map((scenario) => apiScenarioButtonHtml(scenario)).join("");
    }
    setText("#selected-scene-name", currentCompareScenarios[0].name);
    tableBody?.replaceChildren();
    setText("#compare-count", "0 个场景");
    setText("#best-dps", "0.00");
    setText("#best-hit", "0%");
  } catch (error) {
    showEmptyScenarios("本地 API 未连接，无法读取场景库");
  }
}

function scenePawnRowsHtml(selectedName = "射击+大师狙+双仿生眼"): string {
  return scenePawnOptions
    .map(
      (pawn) =>
        `<button class="list-row scene-pawn-row ${
          pawn.name === selectedName ? "selected" : ""
        }" data-name="${escapeHtml(pawn.name)}" data-role-text="${escapeHtml(pawn.roleText)}">${escapeHtml(
          `${pawn.name} · ${pawn.roleText}`
        )}</button>`
    )
    .join("");
}

function mobileScenePawnRowsHtml(role: "attacker" | "defender", selectedName: string): string {
  const candidates = scenePawnOptions.filter((pawn) =>
    role === "attacker" ? pawn.roleText.includes("攻击") : pawn.roleText.includes("防守")
  );
  return candidates
    .map(
      (pawn) =>
        `<button class="list-row scene-mobile-pawn ${
          pawn.name === selectedName ? "selected" : ""
        }" data-role="${role}" data-name="${escapeHtml(pawn.name)}">${escapeHtml(pawn.name)}</button>`
    )
    .join("");
}

function renderScenePage(): void {
  const pageRoot = document.querySelector("#page-root");
  const defaultPawn = scenePawnOptions[0];
  if (!pageRoot) return;
  pageRoot.innerHTML = `
    <section class="scene-page">
      <aside class="scene-sidebar">
        <section class="scene-block">
          <h1>新建场景</h1>
          <p>选择一个或多个攻击方、防守方后，系统按组合生成测试场景。</p>
        </section>

        <label class="path-picker scene-field">
          <span>场景名称</span>
          <input id="sceneName" value="狙击 VS 靶70甲" />
        </label>

        <section class="scene-pick-stack desktop-scene-controls">
          <button class="scene-role-button confirm selected" data-role="attacker">攻击方人物</button>
          <div class="scene-selected-list" id="attacker-selected"><span>射击+大师狙+双仿生眼</span></div>
          <button class="danger scene-remove-selected" data-role="attacker">删除选中攻击方</button>
          <button class="scene-role-button" data-role="defender">防守方人物</button>
          <div class="scene-selected-list" id="defender-selected"><span>靶70甲</span></div>
          <button class="danger scene-remove-selected" data-role="defender">删除选中防守方</button>
        </section>

        <section class="scene-settings desktop-scene-controls">
          <label><span>双方距离</span><input id="sceneDistanceDesktop" value="40" /></label>
          <label><span>最终命中率修正</span><input id="sceneAccuracyDesktop" value="100%" /></label>
        </section>

        <section class="mobile-scene-controls">
          <div class="scene-menu-anchor">
            <button class="scene-mobile-toggle confirm" data-target="attacker-popover">攻击方：射击+大师狙+双仿生眼</button>
            <div class="scene-popover" id="attacker-popover" aria-label="攻击方选择菜单">
              <label class="search-box">
                <span>搜索</span>
                <input class="scene-pawn-search" data-target="attacker-mobile-list" type="search" placeholder="搜索攻击方" />
              </label>
              <div class="rim-list scene-menu-list multi-select-list" id="attacker-mobile-list">
                ${mobileScenePawnRowsHtml("attacker", "射击+大师狙+双仿生眼")}
              </div>
            </div>
          </div>
          <div class="scene-menu-anchor">
            <button class="scene-mobile-toggle" data-target="defender-popover">防守方：靶70甲</button>
            <div class="scene-popover" id="defender-popover" aria-label="防守方选择菜单">
              <label class="search-box">
                <span>搜索</span>
                <input class="scene-pawn-search" data-target="defender-mobile-list" type="search" placeholder="搜索防守方" />
              </label>
              <div class="rim-list scene-menu-list multi-select-list" id="defender-mobile-list">
                ${mobileScenePawnRowsHtml("defender", "靶70甲")}
              </div>
            </div>
          </div>
          <label class="mobile-scene-field"><span>双方距离</span><input id="sceneDistance" value="40" /></label>
          <label class="mobile-scene-field"><span>最终命中率修正</span><input id="sceneAccuracy" value="100%" /></label>
        </section>

        <div class="status-line" id="scene-status"></div>
        <button class="confirm wide scene-save">保存场景</button>
      </aside>

      <section class="scene-main">
        <section class="scene-picker desktop-scene-picker">
          <div class="scene-picker-head">
            <div>
              <h1>选择人物</h1>
              <p>先选择当前加入到攻击方还是防守方，再从列表中选择人物。</p>
            </div>
            <label class="search-box">
              <span>搜索</span>
              <input class="scene-pawn-search" data-target="scene-pawn-list" type="search" placeholder="搜索人物" />
            </label>
          </div>
          <div class="scene-picker-body">
            <div class="rim-list scene-pawn-list" id="scene-pawn-list" aria-label="可选人物列表">
              ${scenePawnRowsHtml()}
            </div>
            <div class="detail-card scene-pawn-preview" id="scene-pawn-preview">${detailHtml(defaultPawn.detail)}</div>
          </div>
          <button class="confirm" id="add-scene-pawn">加入当前栏位</button>
        </section>
      </section>
    </section>
  `;
  bindScenePage();
}

function bindScenePage(): void {
  let activeRole: "attacker" | "defender" = "attacker";
  let selectedPawnKey = "射击+大师狙+双仿生眼";
  const mobileSelections: Record<"attacker" | "defender", Set<string>> = {
    attacker: new Set(["射击+大师狙+双仿生眼"]),
    defender: new Set(["靶70甲"])
  };

  const apiPawnByKey = (key: string): ApiPawn | undefined =>
    currentScenePawns.find((pawn) => pawn.id === key || pawn.name === key);

  const pawnLabel = (key: string): string => apiPawnByKey(key)?.name ?? key;

  const mobileSceneControlsAreActive = (): boolean => {
    const controls = document.querySelector(".mobile-scene-controls");
    return controls instanceof HTMLElement && window.getComputedStyle(controls).display !== "none";
  };

  const updatePreview = (key: string): void => {
    selectedPawnKey = key;
    const apiPawn = apiPawnByKey(key);
    const staticPawn = scenePawnOptions.find((option) => option.name === key);
    const preview = document.querySelector("#scene-pawn-preview");
    if (preview) {
      preview.innerHTML = detailHtml(
        apiPawn?.detail ?? staticPawn?.detail ?? [["人物", pawnLabel(key)], ["说明", "静态原型占位数据"]]
      );
    }
  };

  const selectedRoleIds = (role: "attacker" | "defender"): string[] => {
    if (mobileSceneControlsAreActive()) {
      const ids = Array.from(mobileSelections[role]).filter((id) => currentScenePawns.some((pawn) => pawn.id === id));
      if (ids.length > 0) return Array.from(new Set(ids));
    }
    const target = document.querySelector(role === "attacker" ? "#attacker-selected" : "#defender-selected");
    const ids = Array.from(target?.querySelectorAll<HTMLElement>("span[data-pawn-id]") ?? [])
      .map((item) => item.dataset.pawnId)
      .filter((id): id is string => Boolean(id));
    if (ids.length > 0) return ids;
    return Array.from(mobileSelections[role]).filter((id) => currentScenePawns.some((pawn) => pawn.id === id));
  };

  const refreshScenePreview = async (): Promise<void> => {
    const attackerId = selectedRoleIds("attacker")[0];
    const defenderId = selectedRoleIds("defender")[0];
    if (!attackerId || !defenderId) return;
    const distance = Number.parseInt(document.querySelector<HTMLInputElement>("#sceneDistance")?.value ?? "12", 10);
    const hitText = document.querySelector<HTMLInputElement>("#sceneAccuracy")?.value ?? "100";
    const hitChance = Number.parseFloat(hitText.replace("%", ""));
    try {
      await apiJson<ApiScenarioPreview>("/api/scenario/preview", {
        method: "POST",
        body: JSON.stringify({
          name: document.querySelector<HTMLInputElement>("#sceneName")?.value || "预览场景",
          attackerPawnId: attackerId,
          defenderPawnId: defenderId,
          distanceCells: Number.isFinite(distance) ? distance : 12,
          hitChancePercent: Number.isFinite(hitChance) ? hitChance : 100,
        }),
      });
    } catch (error) {
      setText("#scene-status", error instanceof Error ? error.message : "场景预览计算失败。");
    }
  };

  const addPawnToRole = (role: "attacker" | "defender", key: string): void => {
    const target = document.querySelector(role === "attacker" ? "#attacker-selected" : "#defender-selected");
    if (!target) return;
    const apiPawn = apiPawnByKey(key);
    const name = apiPawn?.name ?? key;
    const exists = Array.from(target.querySelectorAll("span")).some((item) =>
      apiPawn ? item.dataset.pawnId === apiPawn.id : item.textContent?.trim() === name
    );
    if (!exists) {
      const item = document.createElement("span");
      item.textContent = name;
      if (apiPawn) item.dataset.pawnId = apiPawn.id;
      target.append(item);
    }
    void refreshScenePreview();
  };

  const updateMobileRoleButton = (role: "attacker" | "defender"): void => {
    const target = role === "attacker" ? "attacker-popover" : "defender-popover";
    const button = document.querySelector(`.scene-mobile-toggle[data-target="${target}"]`);
    if (!button) return;
    const names = Array.from(mobileSelections[role]).map(pawnLabel);
    const label = role === "attacker" ? "攻击方" : "防守方";
    button.textContent = names.length === 0 ? `${label}：未选择` : names.length === 1 ? `${label}：${names[0]}` : `${label}：已选 ${names.length} 个`;
  };

  document.querySelectorAll<HTMLButtonElement>(".scene-role-button").forEach((button) => {
    button.addEventListener("click", () => {
      activeRole = (button.dataset.role as "attacker" | "defender") ?? "attacker";
      document.querySelectorAll(".scene-role-button").forEach((item) => item.classList.remove("selected", "confirm"));
      button.classList.add("selected", "confirm");
    });
  });

  const scenePawnList = document.querySelector("#scene-pawn-list");
  scenePawnList?.addEventListener("click", (event) => {
    const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".scene-pawn-row");
    if (!row) return;
    const key = row.dataset.pawnId ?? row.dataset.name ?? row.textContent?.trim() ?? "";
      document.querySelectorAll(".scene-pawn-row").forEach((item) => item.classList.remove("selected"));
      row.classList.add("selected");
    updatePreview(key);
  });
  scenePawnList?.addEventListener("dblclick", (event) => {
    const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".scene-pawn-row");
    if (!row) return;
    addPawnToRole(activeRole, row.dataset.pawnId ?? row.dataset.name ?? selectedPawnKey);
  });

  document.querySelector("#add-scene-pawn")?.addEventListener("click", () => addPawnToRole(activeRole, selectedPawnKey));

  document.querySelectorAll(".scene-selected-list").forEach((list) => {
    list.addEventListener("click", (event) => {
      const item = (event.target as HTMLElement).closest("span");
      item?.classList.toggle("selected");
    });
  });

  document.querySelectorAll<HTMLButtonElement>(".scene-remove-selected").forEach((button) => {
    button.addEventListener("click", () => {
      const role = button.dataset.role === "defender" ? "defender" : "attacker";
      const target = document.querySelector(role === "attacker" ? "#attacker-selected" : "#defender-selected");
      target?.querySelectorAll("span.selected").forEach((item) => item.remove());
      void refreshScenePreview();
    });
  });

  document.querySelectorAll<HTMLInputElement>(".scene-pawn-search").forEach((input) => {
    input.addEventListener("input", () => {
      if (input.dataset.target) {
        filterListRows(`#${input.dataset.target}`, input.value);
      }
    });
  });

  document.querySelectorAll<HTMLButtonElement>(".scene-mobile-toggle").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const target = document.querySelector(`#${button.dataset.target}`);
      if (target instanceof HTMLElement) {
        openFloatingPopover(button, target);
      }
    });
  });

  ["#attacker-mobile-list", "#defender-mobile-list"].forEach((selector) => {
    const list = document.querySelector(selector);
    list?.addEventListener("click", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".scene-mobile-pawn");
      if (!row) return;
      event.stopPropagation();
      const role: "attacker" | "defender" = row.dataset.role === "defender" ? "defender" : "attacker";
      const key = row.dataset.pawnId ?? row.dataset.name ?? row.textContent?.trim() ?? "";
      row.classList.toggle("selected");
      if (row.classList.contains("selected")) {
        mobileSelections[role].add(key);
      } else {
        mobileSelections[role].delete(key);
      }
      updateMobileRoleButton(role);
      void refreshScenePreview();
    });
    list?.addEventListener("dblclick", (event) => {
      const row = (event.target as HTMLElement).closest<HTMLButtonElement>(".scene-mobile-pawn");
      if (!row) return;
      event.stopPropagation();
      const role: "attacker" | "defender" = row.dataset.role === "defender" ? "defender" : "attacker";
      const key = row.dataset.pawnId ?? row.dataset.name ?? row.textContent?.trim() ?? "";
      mobileSelections[role].add(key);
      row.classList.add("selected");
      updateMobileRoleButton(role);
      void refreshScenePreview();
      closeFloatingPopovers();
    });
  });

  document.querySelectorAll(".scene-popover").forEach((popover) => {
    popover.addEventListener("click", (event) => event.stopPropagation());
  });
  document.querySelector("#page-root")?.addEventListener("click", () => {
    closeFloatingPopovers();
  });

  document.querySelectorAll<HTMLInputElement>("#sceneDistance, #sceneAccuracy").forEach((input) => {
    input.addEventListener("input", () => {
      void refreshScenePreview();
    });
  });

  document.querySelector(".scene-save")?.addEventListener("click", async () => {
    const attackerPawnIds = selectedRoleIds("attacker");
    const defenderPawnIds = selectedRoleIds("defender");
    const distance = Number.parseInt(document.querySelector<HTMLInputElement>("#sceneDistance")?.value ?? "12", 10);
    const hitChance = Number.parseFloat(
      (document.querySelector<HTMLInputElement>("#sceneAccuracy")?.value ?? "100").replace("%", "")
    );
    try {
      const result = await apiJson<{ savedCount: number; skippedCount: number }>("/api/scenarios/save", {
        method: "POST",
        body: JSON.stringify({
          name: document.querySelector<HTMLInputElement>("#sceneName")?.value || "未命名场景",
          attackerPawnIds,
          defenderPawnIds,
          distanceCells: Number.isFinite(distance) ? distance : 12,
          hitChancePercent: Number.isFinite(hitChance) ? hitChance : 100,
        }),
      });
      setText("#scene-status", `已保存 ${result.savedCount} 个场景，跳过 ${result.skippedCount} 个重复/无效组合。`);
    } catch (error) {
      setText("#scene-status", error instanceof Error ? error.message : "保存场景失败。");
    }
  });

  const loadLivePawns = async (): Promise<void> => {
    try {
      const result = await apiJson<{ pawns: ApiPawn[] }>("/api/pawns");
      currentScenePawns = result.pawns;
      if (currentScenePawns.length === 0) {
        setText("#scene-status", "还没有已保存人物，先到人物创建页保存人物模板。");
        return;
      }
      const attacker = currentScenePawns.find((pawn) => pawn.weaponName && pawn.weaponName !== "无") ?? currentScenePawns[0];
      const defender = currentScenePawns.find((pawn) => pawn.id !== attacker.id) ?? currentScenePawns[0];
      const desktopList = document.querySelector("#scene-pawn-list");
      const attackerList = document.querySelector("#attacker-mobile-list");
      const defenderList = document.querySelector("#defender-mobile-list");
      if (desktopList) desktopList.innerHTML = scenePawnRowsFromApiHtml(attacker.id);
      if (attackerList) attackerList.innerHTML = mobileScenePawnRowsFromApiHtml("attacker", attacker.id);
      if (defenderList) defenderList.innerHTML = mobileScenePawnRowsFromApiHtml("defender", defender.id);
      const attackerSelected = document.querySelector("#attacker-selected");
      const defenderSelected = document.querySelector("#defender-selected");
      if (attackerSelected) attackerSelected.innerHTML = `<span data-pawn-id="${escapeHtml(attacker.id)}">${escapeHtml(attacker.name)}</span>`;
      if (defenderSelected) defenderSelected.innerHTML = `<span data-pawn-id="${escapeHtml(defender.id)}">${escapeHtml(defender.name)}</span>`;
      mobileSelections.attacker = new Set([attacker.id]);
      mobileSelections.defender = new Set([defender.id]);
      updateMobileRoleButton("attacker");
      updateMobileRoleButton("defender");
      updatePreview(attacker.id);
      await refreshScenePreview();
    } catch (error) {
      setText("#scene-status", "本地 API 未连接，当前显示静态原型数据。");
    }
  };

  void loadLivePawns();
}

function currentPawnPayload(): Record<string, unknown> {
  const species = selectedOptions("base")[0];
  const weapon = selectedOptions("weapon")[0]?.choice ?? null;
  const shootingSkill = Number.parseInt(
    document.querySelector<HTMLInputElement>("#pawnShooting")?.value ?? "14",
    10
  );
  return {
    id: "preview-pawn",
    name: document.querySelector<HTMLInputElement>("#pawnName")?.value ?? "",
    speciesId: species?.id ?? "human_baseliner",
    featureIds: selectedOptions("traits").map((option) => option.id).filter(Boolean),
    supportGearIds: selectedOptions("specials").map((option) => option.id).filter(Boolean),
    implantIds: selectedOptions("implants").map((option) => option.id).filter(Boolean),
    shootingSkill: Number.isFinite(shootingSkill) ? shootingSkill : 14,
    fullBodyArmorPercent: species?.defaultFullBodyArmorPercent ?? 0,
    weapon,
    apparel: selectedOptions("apparel").map((option) => option.choice).filter(Boolean)
  };
}

async function refreshFirepowerPreview(): Promise<void> {
  const payload = currentPawnPayload();
  if (!payload.weapon) {
    setText("#pawn-output-weapon", "请选择武器");
    return;
  }
  try {
    const result = await apiJson<{ preview: Record<string, any> }>("/api/pawn/preview", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    updateOutput(result.preview);
  } catch (error) {
    setText("#pawn-status", "本地算法服务未连接或游戏数据未导入。");
    setText("#pawn-output-weapon", "等待 API");
  }
}

function updateOutput(preview: Record<string, any>): void {
  const targets = new Map(
    (preview.targets ?? []).map((target: any) => [Number(target.armorPercent), target])
  );
  const bestDistance = String(preview.bestDistanceLabel ?? "-").replace(/\s*\n\s*/g, " / ");
  setText("#pawn-output-weapon", String(preview.weaponName ?? "-"));
  setText("#pawn-output-best-distance", `${bestDistance} / ${formatFixed(preview.finalHitPercent, 0)}%`);
  setText("#pawn-output-best-hit", `${formatFixed(preview.finalHitPercent, 0)}%`);
  [0, 20, 40, 70, 100].forEach((armor) => {
    const target = targets.get(armor) as any;
    const text = target
      ? `${formatFixed(target.expectedDps)} / ${formatFixed(target.ratioToUnarmored * 100, 0)}%`
      : "-";
    setText(`#pawn-output-dps-${armor}`, text);
  });
  setText(
    "#pawn-output-warmup",
    `${formatFixed(preview.actualWarmupSeconds)} / ${formatFixed(preview.baseWarmupSeconds)}`
  );
  setText(
    "#pawn-output-cooldown",
    `${formatFixed(preview.actualCooldownSeconds)} / ${formatFixed(preview.baseCooldownSeconds)}`
  );
}

async function hydrateLiveOptions(): Promise<void> {
  try {
    const result = await apiJson<{ options: any }>("/api/pawn/options");
    pawnQualityOptions = result.options.qualities ?? pawnQualityOptions;
    pawnMaterialOptions = result.options.materials ?? pawnMaterialOptions;
    pawnCatalog.base.options = result.options.species ?? pawnCatalog.base.options;
    pawnCatalog.traits.options = result.options.features ?? [];
    pawnCatalog.specials.options = result.options.supportGear ?? [];
    pawnCatalog.implants.options = result.options.implants ?? [];
    pawnCatalog.weapon.options = result.options.weapons ?? [];
    pawnCatalog.apparel.options = result.options.apparel ?? [];
    if (activePage === "pawn") {
      renderPawnPage();
    }
  } catch (error) {
    setText("#pawn-status", "本地算法服务未连接或游戏数据未导入。");
  }
}

renderShell();
renderPage();
hydrateLiveOptions();
