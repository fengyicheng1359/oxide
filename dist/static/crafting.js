/* 配方以稳定 ID 计算；页面与 Node 校验共用同一套批次、材料及库存逻辑。 */
(function () {
  'use strict';
  const MAX_QUANTITY = 1000000;
  const STORAGE_KEY = 'oxide-crafting-plan-v1';

  function quantity(value, minimum = 0) {
    return typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum && value <= MAX_QUANTITY;
  }

  function normalizeState(value, items) {
    const state = { version: 1, targets: {}, inventory: {} };
    if (!value || value.version !== 1) return state;
    for (const [id, count] of Object.entries(value.targets || {})) {
      if (Object.hasOwn(items, id) && items[id].recipe && quantity(count, 1)) state.targets[id] = count;
    }
    for (const [id, count] of Object.entries(value.inventory || {})) {
      if (Object.hasOwn(items, id) && quantity(count)) state.inventory[id] = count;
    }
    return state;
  }

  function calculate(items, targets, inventory) {
    const totals = new Map();
    const products = [];
    // 每种成品先按单次产量向上取整，再合并直接材料，最后统一扣库存。
    for (const [id, requested] of Object.entries(targets)) {
      if (!Object.hasOwn(items, id) || !items[id].recipe || !quantity(requested, 1)) continue;
      const recipe = items[id].recipe;
      const batches = Math.ceil(requested / recipe.output);
      products.push({ id, requested, batches, produced: batches * recipe.output });
      for (const [material, amount] of Object.entries(recipe.materials)) {
        totals.set(material, (totals.get(material) || 0) + amount * batches);
      }
    }
    const materials = [...totals].map(([id, required]) => {
      const owned = quantity(inventory[id]) ? inventory[id] : 0;
      return { id, required, owned, missing: Math.max(0, required - owned) };
    });
    return { products, materials };
  }

  function recyclingOptions(sources, missing) {
    if (!Number.isFinite(missing) || missing <= 0) return [];
    // 概率未知或非零时不承诺补足数量；各来源是独立备选方案，不叠加消耗。
    return sources.filter(source => source.amount > 0 && source.skipChance !== 1).map(source => ({
      ...source,
      count: source.skipChance === 0 ? Math.ceil(missing / source.amount) : null
    })).sort((a, b) => Number(a.count === null) - Number(b.count === null) || (a.priority ?? 1) - (b.priority ?? 1) || b.amount - a.amount || a.id.localeCompare(b.id));
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { calculate, normalizeState, quantity, recyclingOptions };
  if (typeof document === 'undefined') return;
  const source = document.getElementById('craft-data');
  if (!source) return;
  const { items, labels, recyclingSources } = JSON.parse(source.textContent);
  const t = key => labels[key] || key;
  const root = document.documentElement.dataset.siteRoot;
  const language = document.documentElement.dataset.language;
  const byId = id => document.getElementById(id);
  const number = n => n.toLocaleString(language);
  let state = normalizeState(null, items);
  let storageAvailable = true;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) state = normalizeState(JSON.parse(stored), items);
  } catch (_) { storageAvailable = false; }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function itemImage(id) {
    const img = element('img', 'craft-icon');
    img.src = root + 'static/' + items[id].image;
    img.alt = '';
    img.loading = 'lazy';
    img.width = 48;
    img.height = 48;
    return img;
  }
  function itemLink(id) {
    const link = element('a', 'craft-item-link', items[id].name);
    link.href = './' + id + '.html';
    return link;
  }
  function save() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); storageAvailable = true; }
    catch (_) { storageAvailable = false; }
    byId('craft-save').textContent = t(storageAvailable ? '已保存到此浏览器' : '无法保存，刷新后清单可能丢失');
  }
  function numberInput(id, value, minimum, field) {
    const input = element('input', 'craft-number');
    input.type = 'number'; input.min = minimum; input.max = MAX_QUANTITY; input.step = '1';
    input.inputMode = 'numeric'; input.value = value;
    input.dataset.item = id; input.dataset.field = field;
    input.setAttribute('aria-label', items[id].name + ' · ' + t(field === 'targets' ? '制作数量' : '已有'));
    input.addEventListener('change', () => {
      const count = input.value === '' && minimum === 0 ? 0 : input.valueAsNumber;
      if (!quantity(count, minimum)) { input.value = state[field][id] || minimum; return; }
      state[field][id] = count;
      input.value = count;
      save(); updatePlanNumbers();
    });
    return input;
  }

  const craftable = Object.keys(items).filter(id => items[id].recipe);
  const categories = [...new Set(craftable.map(id => items[id].category))];
  for (const category of categories) {
    const option = element('option', '', category); option.value = category;
    byId('craft-category').append(option);
  }
  function renderCatalog() {
    const query = byId('craft-search').value.trim().toLocaleLowerCase();
    const category = byId('craft-category').value;
    const matches = craftable.filter(id => (!category || items[id].category === category) &&
      (items[id].name + ' ' + items[id].english + ' ' + id).toLocaleLowerCase().includes(query));
    byId('craft-items').replaceChildren();
    byId('craft-catalog-status').textContent = matches.length ? `${number(matches.length)} / ${number(craftable.length)}` : t('没有找到匹配的物品。');
    for (const id of matches) {
      const item = items[id];
      const card = element('article', 'craft-card');
      const copy = element('div', 'craft-card-copy');
      copy.append(itemLink(id));
      if (item.english !== item.name) copy.append(element('small', '', item.english));
      copy.append(element('span', 'craft-yield', t('每次产出') + ' ×' + number(item.recipe.output)));
      const button = element('button', 'craft-add', '+');
      button.type = 'button'; button.setAttribute('aria-label', t('添加') + ' ' + item.name);
      button.addEventListener('click', () => {
        state.targets[id] = Math.min(MAX_QUANTITY, (state.targets[id] || 0) + 1);
        save(); renderPlan();
        byId('craft-message').textContent = t('添加') + ' · ' + item.name;
      });
      card.append(itemImage(id), copy, button); byId('craft-items').append(card);
    }
  }

  const expandedMaterials = new Set();

  function recyclingPanel(material) {
    const panel = element('tr', 'craft-recycling-row');
    panel.id = 'craft-recycling-' + material.id;
    panel.hidden = !expandedMaterials.has(material.id);
    const cell = element('td'); cell.colSpan = 4;
    const options = recyclingOptions(recyclingSources[material.id] || [], material.missing);
    if (!options.length) {
      cell.append(element('p', 'craft-muted', t('暂无已收录的回收来源。')));
    } else {
      cell.append(element('p', 'craft-muted', t('各方案单独补足当前缺口，不会自动扣减清单或库存。')));
      const list = element('ul', 'craft-recycling-list');
      for (const option of options) {
        const row = element('li', 'craft-recycling-source');
        row.dataset.source = option.id;
        const name = element('div', 'craft-recycling-item');
        name.append(itemImage(option.id), itemLink(option.id));
        const yieldLabel = element('div');
        yieldLabel.append(element('small', '', t('每件回收产量')), element('strong', '', number(option.amount)));
        const required = element('div');
        required.append(element('small', '', t('补足缺口需回收')),
          element('strong', option.count === null ? 'craft-source-count craft-probability' : 'craft-source-count', option.count === null ? t('概率产出，不保证数量') : number(option.count)));
        row.append(name, yieldLabel, required); list.append(row);
      }
      cell.append(list, element('p', 'craft-muted', t('回收数量按当前数据估算，实际产出可能受物品状态或服务器规则影响。')));
    }
    panel.append(cell);
    return panel;
  }

  function renderPlan() {
    const result = calculate(items, state.targets, state.inventory);
    byId('craft-targets').replaceChildren();
    byId('craft-materials').replaceChildren();
    byId('craft-copy-fallback').hidden = true;
    byId('craft-message').textContent = '';
    byId('craft-clear').disabled = !result.products.length && !Object.keys(state.inventory).length;
    byId('craft-copy').disabled = !result.products.length;
    if (!result.products.length) {
      const empty = element('div', 'craft-empty');
      empty.append(element('span', 'craft-empty-mark', '+'), element('h3', '', t('清单为空')), element('p', '', t('从左侧选择要制作的物品。')));
      byId('craft-targets').append(empty);
    }
    for (const product of result.products) {
      const row = element('div', 'craft-target');
      row.dataset.product = product.id;
      const copy = element('div', 'craft-target-copy');
      copy.append(itemLink(product.id), element('small', '', `${t('制作次数')} ${number(product.batches)} · ${t('实际产出')} ${number(product.produced)}`));
      const remove = element('button', 'craft-remove', '×');
      remove.type = 'button'; remove.setAttribute('aria-label', t('移除') + ' ' + items[product.id].name);
      remove.addEventListener('click', () => { delete state.targets[product.id]; save(); renderPlan(); });
      row.append(itemImage(product.id), copy, numberInput(product.id, product.requested, 1, 'targets'), remove);
      byId('craft-targets').append(row);
    }
    result.materials.sort((a, b) => items[a.id].name.localeCompare(items[b.id].name, language));
    for (const material of result.materials) {
      const row = element('tr', material.missing ? '' : 'craft-complete');
      row.dataset.material = material.id;
      const name = element('th'); name.scope = 'row';
      const nameContent = element('div', 'craft-material-name'); nameContent.append(itemImage(material.id), itemLink(material.id)); name.append(nameContent);
      const owned = element('td'); owned.append(numberInput(material.id, material.owned, 0, 'inventory'));
      row.append(name, element('td', 'craft-required', number(material.required)), owned, element('td', 'craft-missing', number(material.missing)));
      byId('craft-materials').append(row);
      {
        // 预先保留回收入口，缺口变化时只切换可见性，避免移除正在点击的节点。
        const panel = recyclingPanel({ ...material, missing: Math.max(1, material.missing) });
        const button = element('button', 'craft-recycling-toggle'); button.type = 'button';
        button.setAttribute('aria-controls', panel.id);
        const updateButton = () => {
          button.textContent = t(panel.hidden ? '查看回收来源' : '收起回收来源');
          button.setAttribute('aria-expanded', String(!panel.hidden));
          button.setAttribute('aria-label', items[material.id].name + ' · ' + button.textContent);
        };
        updateButton();
        button.addEventListener('click', () => {
          panel.hidden = !panel.hidden;
          if (panel.hidden) expandedMaterials.delete(material.id); else expandedMaterials.add(material.id);
          updateButton();
        });
        name.append(button); byId('craft-materials').append(panel);
      }
    }
    updatePlanNumbers(result);
  }

  function updatePlanNumbers(result = calculate(items, state.targets, state.inventory)) {
    // 数量提交时不重建输入框、链接或按钮，让浏览器正常处理 Tab、失焦与点击。
    byId('craft-copy-fallback').hidden = true;
    byId('craft-message').textContent = '';
    for (const product of result.products) {
      const row = document.querySelector(`[data-product="${product.id}"]`);
      row.querySelector('small').textContent = `${t('制作次数')} ${number(product.batches)} · ${t('实际产出')} ${number(product.produced)}`;
    }
    for (const material of result.materials) {
      const row = document.querySelector(`[data-material="${material.id}"]`);
      row.classList.toggle('craft-complete', material.missing === 0);
      row.querySelector('.craft-required').textContent = number(material.required);
      row.querySelector('.craft-missing').textContent = number(material.missing);
      const button = row.querySelector('.craft-recycling-toggle');
      const panel = byId('craft-recycling-' + material.id);
      button.hidden = material.missing === 0;
      panel.hidden = material.missing === 0 || !expandedMaterials.has(material.id);
      button.textContent = t(panel.hidden ? '查看回收来源' : '收起回收来源');
      button.setAttribute('aria-expanded', String(!panel.hidden));
      button.setAttribute('aria-label', items[material.id].name + ' · ' + button.textContent);
      for (const option of recyclingOptions(recyclingSources[material.id] || [], material.missing)) {
        const output = panel.querySelector(`[data-source="${option.id}"] .craft-source-count`);
        output.textContent = option.count === null ? t('概率产出，不保证数量') : number(option.count);
      }
    }
    const missing = result.materials.filter(row => row.missing > 0).length;
    byId('craft-summary').textContent = !result.products.length ? '—' : missing ? t('还缺 {count} 种材料').replace('{count}', number(missing)) : t('材料已备齐');
    byId('craft-summary').classList.toggle('is-ready', !!result.products.length && !missing);
  }

  byId('craft-search').addEventListener('input', renderCatalog);
  byId('craft-category').addEventListener('change', renderCatalog);
  byId('craft-clear').addEventListener('click', () => {
    if (!window.confirm(t('清除清单和库存？'))) return;
    state = normalizeState(null, items); save(); renderPlan();
  });
  byId('craft-copy').addEventListener('click', async () => {
    const result = calculate(items, state.targets, state.inventory);
    const text = [t('制作计算器'), ...result.products.map(row => `${items[row.id].name} ×${row.requested} (${t('实际产出')} ${row.produced})`), '',
      ...result.materials.map(row => `${items[row.id].name}: ${t('需要')} ${row.required} / ${t('已有')} ${row.owned} / ${t('还缺')} ${row.missing}`)].join('\n');
    try { await navigator.clipboard.writeText(text); byId('craft-message').textContent = t('已复制'); }
    catch (_) {
      const fallback = byId('craft-copy-fallback'); fallback.hidden = false; fallback.value = text; fallback.focus(); fallback.select();
      byId('craft-message').textContent = t('复制失败，请手动复制下方清单');
    }
  });
  // 不在首次打开时覆写存储；语言页面共享同一份物品 ID 清单。
  byId('craft-save').textContent = t(storageAvailable ? '已保存到此浏览器' : '无法保存，刷新后清单可能丢失');
  renderCatalog(); renderPlan();
})();
