/* 别名按显式词表精确匹配，其他查询仍使用物品名称；不把 AK 误当作 makeshift 的片段。 */
(() => {
  'use strict';
  const normalize = text => text.trim().toLocaleLowerCase();
  const input = document.querySelector('#item-search');
  if (input) {
    const cards = [...document.querySelectorAll('.catalog-card')];
    const sections = [...document.querySelectorAll('.category-section')];
    const aliases = new Map(cards.map(card => [card, JSON.parse(card.dataset.searchAliases).map(normalize)]));
    const empty = document.querySelector('#search-empty');
    const update = () => {
      const query = normalize(input.value);
      const exact = cards.filter(card => aliases.get(card).includes(query));
      for (const card of cards) {
        card.hidden = !!query && (exact.length ? !exact.includes(card) : !normalize(card.dataset.searchName).includes(query));
      }
      for (const section of sections) section.hidden = !section.querySelector('.catalog-card:not([hidden])');
      empty.hidden = cards.some(card => !card.hidden);
    };
    input.value = new URLSearchParams(location.search).get('q') || '';
    input.addEventListener('input', update);
    document.querySelector('#search-reset').addEventListener('click', () => {
      input.value = ''; update(); input.focus();
      const url = new URL(location.href); url.searchParams.delete('q'); history.replaceState(null, '', url);
    });
    update();
  }
  // 无脚本时分类默认展开；窄屏只折叠导航，正文与物品名称始终可见。
  const narrow = matchMedia('(max-width: 760px)');
  const menus = [...document.querySelectorAll('.category-menu')];
  const setMenus = () => { for (const menu of menus) menu.open = !narrow.matches; };
  setMenus(); narrow.addEventListener('change', setMenus);
})();
