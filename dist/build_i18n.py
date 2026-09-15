"""按显式词典生成九种语言的静态目录；不在浏览器中替换正文。"""
from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path
from string import Formatter
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'static/i18n'
LANGUAGES = {'zh': ('中文', 'zh-CN'), 'en': ('English', 'en'), 'ja': ('日本語', 'ja'),
             'ko': ('한국어', 'ko'), 'fr': ('Français', 'fr'), 'de': ('Deutsch', 'de'),
             'es': ('Español', 'es'), 'pt': ('Português', 'pt'), 'ru': ('Русский', 'ru')}
HAN = re.compile(r'[\u3400-\u9fff]')


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def game_text(value: str) -> str:
    # 游戏字体、颜色和图标标记不适用于网页，保留文字与换行。
    return '\n'.join(line.rstrip() for line in re.sub(r'<[^>]+>', '', value).strip().splitlines())


class Translator:
    def __init__(self, lang: str, mapping: dict):
        self.lang = lang
        self.ui = load(DATA / 'ui' / f'{lang}.json')
        self.game = load(DATA / 'game' / f'{lang}.json')
        self.names = {name: game_text(self.game[token]) for name, token in mapping['legacy_names'].items()}
        self.templates = []
        for source, target in self.ui.items():
            if '{' not in source:
                continue
            pattern = ''
            for literal, field, _, _ in Formatter().parse(source):
                pattern += re.escape(literal)
                if field:
                    value_pattern = r'\d+' if field in {'count', 'animals', 'npcs'} else '.+?'
                    pattern += f'(?P<{field}>{value_pattern})'
            self.templates.append((re.compile('^' + pattern + '$'), target))

    def text(self, value: str) -> str:
        text = value.strip()
        if not text:
            return value
        if text in self.ui:
            result = self.ui[text]
        elif text in self.names:
            result = self.names[text]
        else:
            result = self.dynamic(text)
        return value[:len(value)-len(value.lstrip())] + result + value[len(value.rstrip()):]

    def dynamic(self, text: str) -> str:
        for pattern, target in self.templates:
            match = pattern.fullmatch(text)
            if match:
                values = {k: self.materials(v) if k == 'sources' else self.text(v)
                          for k, v in match.groupdict().items()}
                return target.format(**values)
        category_labels = {'CONSTRUCTION': '建筑', 'TOOL': '工具', 'WEAPON': '武器', 'AMMUNITION': '弹药',
                           'MEDICAL': '医疗', 'ARMOR': '护甲', 'MATERIAL': '材料', 'OTHER': '其他'}
        if text == 'ITEM':
            return self.ui['物品']
        if text in category_labels:
            return self.ui[category_labels[text]]
        if ' · ' in text and ('ITEM' in text):
            return ' · '.join(self.text(part) for part in text.split(' · '))
        if ' → ' in text:
            return ' → '.join(self.materials(part) for part in text.split(' → '))
        if text == '氧化物生存岛爱好者论坛 · STATIC PAGE':
            return self.ui['氧化物生存岛爱好者论坛']
        if self.lang == 'zh' or not HAN.search(text):
            return text
        raise ValueError(f'{self.lang} 缺少站点文案翻译：{text}')

    def materials(self, text: str) -> str:
        values = []
        for part in text.split('、'):
            match = re.fullmatch(r'(.+?)(\s*×\s*[\d.]+)?', part)
            name, amount = match.groups()
            values.append(self.text(name) + (amount or ''))
        return ('、' if self.lang in {'zh', 'ja'} else ', ').join(values)


def relative_root(page: str, localized: bool = True) -> str:
    return '../' * (len(Path(page).parts) - 1 + int(localized)) or './'


def local_link(value: str, page: str, localized: bool, lang: str) -> str:
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or not parts.path:
        return value
    if parts.path.lstrip('./').startswith('static/'):
        return urlunsplit(('', '', relative_root(page, localized) + parts.path.lstrip('./'), parts.query, parts.fragment))
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page), parts.path))
    if resolved == 'styles.css' or resolved.startswith('static/'):
        path = relative_root(page, localized) + resolved
    elif not localized and resolved.endswith('.html'):
        path = relative_root(page, False) + lang + '/' + resolved
    else:
        return value
    return urlunsplit(('', '', path, parts.query, parts.fragment))


def render(source: str, page: str, lang: str, mapping: dict, guides: dict,
           translator: Translator, site_url: str, localized: bool = True) -> str:
    soup = BeautifulSoup(source, 'html.parser')
    tr = translator.text
    # 官方文章按稳定的数字 ID 对应，标题及正文均不再自行翻译。
    official = guides.get(Path(page).stem) if page.startswith('gameplay/') else None
    if official:
        soup.select_one('.gameplay-article h1').string = '__OFFICIAL_TITLE__'
        soup.select_one('.gameplay-body').clear()
    for card in soup.select('.gameplay-card'):
        slug = Path(urlsplit(card['href']).path).stem
        title = card.select_one('strong')
        title.string = '__OFFICIAL_TITLE__'
        title['data-article-slug'] = slug
    for anchor in soup.body.select('a[href]'):
        linked_item = mapping['items'].get(Path(urlsplit(anchor['href']).path).stem)
        if linked_item:
            for subtitle in anchor.select('.material-en, .catalog-copy small, .recycle-item small'):
                subtitle.string = game_text(load_game_en()[linked_item['name']])
                if lang == 'en': subtitle.decompose()
    # 只翻译可见文字及无障碍标签，不改脚本、CSS、URL、数值或资源 ID。
    for node in list(soup.body.find_all(string=True)):
        if isinstance(node, Comment) or node.parent.name in {'script', 'style'}:
            continue
        node.replace_with(tr(str(node)))
    for element in soup.body.find_all(True):
        for attr in ('title', 'alt', 'placeholder', 'aria-label'):
            if element.has_attr(attr):
                element[attr] = tr(element[attr])
    for element in soup.find_all(True):
        for attr in ('href', 'src', 'poster'):
            if element.has_attr(attr):
                element[attr] = local_link(element[attr], page, localized, lang)
    for title in soup.select('[data-article-slug]'):
        title.string = guides[title['data-article-slug']]['title']
        del title['data-article-slug']
    if official:
        soup.select_one('.gameplay-article h1').string = official['title']
        body = soup.select_one('.gameplay-body')
        body.append(BeautifulSoup(official['html'], 'html.parser'))
        # 已收录的官方文章链接指向站内同语种页面；其余链接留在官方同语种站点。
        ids = {re.search(r'(\d+)$', slug).group(1): slug for slug in guides}
        for anchor in body.select('a[href]'):
            parts = urlsplit(anchor['href'])
            if parts.hostname == 'support.playoxide.com':
                match = re.search(r'/articles/[^/]*?(\d+)$', parts.path)
                if match and match.group(1) in ids:
                    dest = './' + ids[match.group(1)] + '.html'
                    anchor['href'] = local_link(dest, page, localized, lang) + (('#' + parts.fragment) if parts.fragment else '')
                else:
                    anchor['href'] = re.sub(r'/hc/[^/]+/', '/hc/' + official['source_locale'] + '/', anchor['href'])
        credit = soup.new_tag('a', href=official['source_url'], attrs={'class': 'article-source', 'rel': 'noopener', 'target': '_blank'})
        credit.string = tr('官方原文') + ' ↗'
        body.append(credit)
    item = mapping['items'].get(Path(page).stem)
    if item:
        content = soup.select_one('.item-content')
        for field, label in [('description', '物品说明'), ('craft_description', '制作说明')]:
            token = item.get(field)
            if token:
                section = soup.new_tag('section', attrs={'class': 'item-description'})
                heading = soup.new_tag('h2'); heading.string = tr(label)
                paragraph = soup.new_tag('p'); paragraph.string = game_text(translator.game[token])
                section.extend([heading, paragraph]); content.append(section)
    # 标题区保留英文名作辅助检索，但从官方 token 获取，替换旧数据中的英文回退值。
    if item:
        en_name = game_text(load_game_en()[item['name']])
        caption = soup.select_one('.image-caption')
        if caption:
            category = caption.get_text().split(' / ')[-1]
            caption.string = en_name + ' / ' + tr(category)
        subtitle = soup.select_one('.item-heading p')
        if subtitle:
            subtitle.string = en_name
            if lang == 'en': subtitle.decompose()
    add_language_picker(soup, page, lang, localized, tr)
    soup.html['lang'] = LANGUAGES[lang][1]
    soup.html['data-language'] = lang
    soup.html['data-page-path'] = page
    soup.html['data-site-root'] = relative_root(page, localized)
    if not localized:
        soup.html['data-legacy-page'] = 'true'
    script = soup.new_tag('script', src=relative_root(page, localized) + 'static/language.js', defer=True)
    soup.head.append(script)
    heading = soup.body.find('h1')
    page_title = heading.get_text(' ', strip=True) if heading else tr('氧化物生存岛')
    intro = soup.select_one('.gameplay-intro p, .ranking-intro p, .recycling-intro p, .about-hero p, .play-hero p, .search-row p')
    description = official['text'][:180] if official else (intro.get_text(' ', strip=True)[:180] if intro else tr('浏览物品、制造配方与生存资源。'))
    if item and item.get('description'):
        description = game_text(translator.game[item['description']])[:180]
    # 移除旧的中文 SEO，按目标语言与目录重新生成，避免 canonical 指向另一语种。
    for tag in soup.head.select('title, meta[name="description"], meta[name="keywords"], meta[property^="og:"], link[rel="canonical"], link[rel="alternate"], script[type="application/ld+json"]'):
        tag.decompose()
    title = soup.new_tag('title'); title.string = page_title + ' · Oxide Wiki'; soup.head.append(title)
    keywords = ', '.join(dict.fromkeys([page_title, 'Oxide: Survival Island', tr('玩法攻略'), tr('制造配方'), tr('物品')]))
    if lang == 'zh':
        keywords += ', ' + ', '.join(load(ROOT / 'static/site-config.json').get('shared_keywords', []))
    for name, value in [('description', description), ('keywords', keywords)]:
        soup.head.append(soup.new_tag('meta', attrs={'name': name, 'content': value}))
    canonical = f'{site_url}/{lang}/{page}'
    for prop, value in [('og:title', page_title), ('og:description', description), ('og:site_name', tr('氧化物生存岛爱好者论坛')), ('og:type', 'website'), ('og:url', canonical)]:
        soup.head.append(soup.new_tag('meta', attrs={'property': prop, 'content': value}))
    soup.head.append(soup.new_tag('link', rel='canonical', href=canonical))
    for code, (_, html_lang) in LANGUAGES.items():
        soup.head.append(soup.new_tag('link', rel='alternate', hreflang=html_lang, href=f'{site_url}/{code}/{page}'))
    soup.head.append(soup.new_tag('link', rel='alternate', hreflang='x-default', href=f'{site_url}/zh/{page}'))
    structured = soup.new_tag('script', type='application/ld+json')
    structured.string = json.dumps({'@context': 'https://schema.org', '@type': 'WebPage', 'name': page_title, 'url': canonical, 'inLanguage': LANGUAGES[lang][1]}, ensure_ascii=False).replace('</', '<\\/')
    soup.head.append(structured)
    return str(soup)


_EN = None

def load_game_en():
    global _EN
    if _EN is None:
        _EN = load(DATA / 'game/en.json')
    return _EN


def add_language_picker(soup, page, lang, localized, tr):
    tools = soup.select_one('.header-tools')
    if tools: tools.decompose()
    label = soup.new_tag('label', attrs={'class': 'language-picker'})
    caption = soup.new_tag('span', attrs={'class': 'visually-hidden'}); caption.string = tr('语言')
    select = soup.new_tag('select', id='site-language', attrs={'aria-label': tr('语言')})
    for code, (name, _) in LANGUAGES.items():
        option = soup.new_tag('option', value=relative_root(page, localized) + code + '/' + page)
        option['data-language'] = code
        option.string = name
        if code == lang: option['selected'] = ''
        select.append(option)
    label.extend([caption, select]); soup.select_one('.header-inner').append(label)
    # 不依赖 JavaScript 也能进入任一语种。
    fallback = soup.new_tag('noscript')
    links = soup.new_tag('div', attrs={'class': 'language-fallback'})
    for code, (name, _) in LANGUAGES.items():
        anchor = soup.new_tag('a', href=relative_root(page, localized) + code + '/' + page, hreflang=LANGUAGES[code][1]); anchor.string = name; links.append(anchor)
    fallback.append(links); soup.select_one('.site-header').append(fallback)


def build_localized_pages(pages: list[Path]) -> list[Path]:
    mapping = load(DATA / 'item-tokens.json')
    site_url = load(ROOT / 'static/site-config.json')['site_url'].rstrip('/')
    sources = {p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8') for p in pages}
    result = []
    zh_pages = {}
    for lang in LANGUAGES:
        translator = Translator(lang, mapping)
        guides = load(DATA / 'gameplay' / f'{lang}.json')
        expected = {Path(p).stem for p in sources if p.startswith('gameplay/') and Path(p).stem != 'index'}
        if set(guides) != expected:
            raise ValueError(f'{lang} 官方玩法文章未齐全：{expected - set(guides)}')
        for page, source in sources.items():
            destination = ROOT / lang / page
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(render(source, page, lang, mapping, guides, translator, site_url), encoding='utf-8')
            result.append(destination)
            if lang == 'zh':
                zh_pages[page] = render(source, page, lang, mapping, guides, translator, site_url, localized=False)
        print(f'{lang}: {len(sources)} pages', flush=True)
    # 全部语种成功后才更新旧入口；旧地址由浏览器跳到用户选定语种。
    for page, source in zh_pages.items():
        (ROOT / page).write_text(source, encoding='utf-8')
    return result
