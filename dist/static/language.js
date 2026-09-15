/* 明确的语种 URL 优先；旧入口按已保存选择、浏览器语言、中文的顺序跳转。 */
(() => {
  const root = document.documentElement;
  const supported = new Set(['zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'pt', 'ru']);
  const picker = document.querySelector('#site-language');
  const save = language => {
    try { localStorage.setItem('oxide-language', language); } catch (_) { /* 禁用存储时仍可切换。 */ }
  };
  const browserLanguage = () => {
    const preferences = [...(navigator.languages || []), navigator.language];
    for (const preference of preferences) {
      if (typeof preference !== 'string') continue;
      // zh-TW、en-US、pt-BR 等地区变体使用对应的现有语种目录。
      const language = preference.trim().toLowerCase().split(/[-_]/)[0];
      if (supported.has(language)) return language;
    }
    return 'zh';
  };
  if (root.dataset.legacyPage === 'true') {
    let language = browserLanguage();
    try {
      const saved = localStorage.getItem('oxide-language');
      if (supported.has(saved)) language = saved;
    } catch (_) { /* 没有存储权限时继续使用浏览器语言。 */ }
    const target = new URL(root.dataset.siteRoot + language + '/' + root.dataset.pagePath, location.href);
    target.search = location.search;
    target.hash = location.hash;
    location.replace(target.href);
    return;
  }
  picker?.addEventListener('change', () => {
    const option = picker.selectedOptions[0];
    if (!supported.has(option.dataset.language)) return;
    save(option.dataset.language);
    const target = new URL(option.value, location.href);
    target.search = location.search;
    target.hash = location.hash;
    location.assign(target.href);
  });
})();
