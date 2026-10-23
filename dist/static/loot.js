/* 在静态奖励清单中搜索；没有脚本时仍能浏览全部物品和用途。 */
(() => {
  'use strict';
  const input = document.querySelector('#loot-search');
  if (!input) return;
  const form = input.closest('form');
  const cards = [...document.querySelectorAll('.loot-item')];
  const count = document.querySelector('#loot-count');
  const empty = document.querySelector('#loot-empty');
  const normalize = value => value.normalize('NFKC').trim().toLocaleLowerCase();
  const aliases = new Map(cards.map(card => [card, JSON.parse(card.dataset.searchAliases).map(normalize)]));

  function update() {
    // 与物品目录保持一致：先精确匹配别名，避免 AK 命中 makeshift 或 brake。
    const query = normalize(input.value);
    const exact = query ? cards.filter(card => aliases.get(card).includes(query)) : [];
    let found = 0;
    for (const card of cards) {
      card.hidden = !!query && (exact.length ? !exact.includes(card) : !normalize(card.dataset.searchName).includes(query));
      if (!card.hidden) found += 1;
    }
    count.textContent = count.dataset.label.replace('{count}', found);
    empty.hidden = found !== 0;
  }

  const params = new URLSearchParams(location.search);
  const item = params.get('item');
  const selected = cards.find(card => card.dataset.itemId === item);
  input.value = selected ? selected.dataset.itemName : (params.get('q') || '');
  input.addEventListener('input', update);
  form.addEventListener('submit', event => { event.preventDefault(); update(); });
  form.addEventListener('reset', event => {
    event.preventDefault(); input.value = ''; update(); input.focus();
    const url = new URL(location.href);
    url.searchParams.delete('q'); url.searchParams.delete('item');
    history.replaceState(null, '', url);
  });
  update();
})();
