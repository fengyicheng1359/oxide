"""在九种语言的最终页面中补齐搜索、工具入口和可靠的物品关联。"""
import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent


@lru_cache(maxsize=1)
def discovery_data():
    """按稳定 ID 建立索引；制作关系只取已收录配方，不根据物品名称猜测。"""
    config = json.loads((ROOT / 'static/config.json').read_text())
    recipes = json.loads((ROOT / 'static/crafting-recipes.json').read_text())
    items = {}
    for rows in config.values():
        for row in rows:
            slug = row.get('item_id') or (Path(row['image']).stem if row.get('image') else None)
            if slug:
                items[slug] = row
    used_by = {}
    for product, recipe in recipes['recipes'].items():
        for material in recipe['materials']:
            used_by.setdefault(material, []).append(product)
    mapping = json.loads((ROOT / 'static/i18n/item-tokens.json').read_text())['items']
    owners = defaultdict(set)
    # 旧配置有名称互换和错译；只有不冒用其他物品正式名称的旧名才能参与检索。
    for path in (ROOT / 'static/i18n/game').glob('*.json'):
        names = json.loads(path.read_text())
        for slug, tokens in mapping.items():
            name = re.sub(r'<[^>]+>', '', names[tokens['name']]).strip().lower()
            owners[name].add(slug)
    aliases = json.loads((ROOT / 'static/search-aliases.json').read_text())
    for slug, values in aliases.items():
        if slug not in items:
            raise ValueError(f'搜索别名指向未收录物品：{slug}')
        for value in values:
            if owners[value.strip().lower()] - {slug}:
                raise ValueError(f'{slug} 搜索别名冒用了其他物品名称：{value}')
    aliases = {slug: values[:] for slug, values in aliases.items()}
    for slug, row in items.items():
        for name in [row['name_zh'], row['name_en']]:
            if not owners[name.strip().lower()] - {slug}:
                aliases.setdefault(slug, []).append(name)
        aliases[slug] = list(dict.fromkeys(aliases.get(slug, [])))
    return {
        'items': items, 'recipes': recipes, 'used_by': used_by,
        'ammunition': json.loads((ROOT / 'static/game-stats.json').read_text())['weapon_ammunition'],
        'release': json.loads((ROOT / 'static/apk-11966-new-items.json').read_text()),
        'aliases': aliases,
    }


def item_name(slug, mapping, translator):
    # 游戏文本可能含字体标签，网页名称只使用纯文本。
    token = mapping['items'][slug]['name']
    return BeautifulSoup(translator.game[token], 'html.parser').get_text()


def search_form(soup, locale_root, translator, class_name='site-search'):
    tr = translator.text
    form = soup.new_tag('form', action=locale_root + 'items.html', method='get', attrs={'class': class_name, 'role': 'search'})
    label = soup.new_tag('label')
    caption = soup.new_tag('span', attrs={'class': 'visually-hidden'})
    caption.string = tr('搜索物品...')
    field = soup.new_tag('input', type='search', attrs={'name': 'q', 'placeholder': tr('搜索名称、英文名或别名'), 'autocomplete': 'off'})
    label.extend([caption, field])
    button = soup.new_tag('button', type='submit'); button.string = tr('搜索')
    form.extend([label, button])
    return form


def add_home_tools(soup, locale_root, mapping, translator, data):
    tr = translator.text
    panel = soup.new_tag('section', attrs={'class': 'wiki-tools', 'aria-label': tr('物品与生存工具')})
    heading = soup.new_tag('h2'); heading.string = tr('物品与生存工具')
    panel.extend([heading, search_form(soup, locale_root, translator, 'wiki-search')])
    links = soup.new_tag('nav', attrs={'class': 'wiki-tool-links', 'aria-label': tr('常用工具')})
    for path, label in [('items.html', '物品'), ('loot.html', '战利品'), ('crafting.html', '制作计算器'), ('recycling.html', '回收'), ('gameplay/index.html', '玩法攻略')]:
        anchor = soup.new_tag('a', href=locale_root + path); anchor.string = tr(label) + ' ↗'; links.append(anchor)
    panel.append(links)
    main = soup.select_one('main')
    main.insert(0, panel)

    release = data['release']
    recent = [slug for slug in release['added_item_ids'] if slug in data['items'] and slug in mapping['items']]
    section = soup.new_tag('section', attrs={'class': 'wiki-release'})
    heading = soup.new_tag('h2'); heading.string = tr('版本新增物品')
    version = soup.new_tag('span', attrs={'class': 'data-version'}); version.string = release['new_version']
    heading.append(version); section.append(heading)
    cards = soup.new_tag('div', attrs={'class': 'release-items'})
    for slug in recent:
        anchor = soup.new_tag('a', href=locale_root + slug + '.html')
        anchor.string = item_name(slug, mapping, translator)
        cards.append(anchor)
    section.append(cards)
    # 新增物品直接进入详情，更新条目不凭空写入发布日期或已验证时间。
    panel.insert_after(section)


def add_item_links(soup, slug, locale_root, mapping, translator, data):
    tr = translator.text
    content = soup.select_one('.item-content')
    if not content:
        return
    links = soup.new_tag('nav', attrs={'class': 'item-actions', 'aria-label': tr('物品工具')})
    if slug in data['recipes']['recipes']:
        anchor = soup.new_tag('a', href=locale_root + 'crafting.html?item=' + slug + '#craft-plan')
        anchor.string = tr('加入制作清单') + ' ↗'; links.append(anchor)
    ammunition = data['ammunition'].get(slug)
    if ammunition in mapping['items'] and ammunition in data['items']:
        anchor = soup.new_tag('a', href=locale_root + ammunition + '.html')
        anchor.string = tr('使用弹药') + ' · ' + item_name(ammunition, mapping, translator)
        links.append(anchor)
    from loot_page import load_loot
    for source in load_loot()['sources']:
        if slug in source['items']:
            anchor = soup.new_tag('a', href=locale_root + 'loot.html?item=' + slug + '#' + source['id'])
            anchor.string = tr('奖励池收录') + ' · ' + tr(source['name'])
            links.append(anchor)
    if links.contents:
        soup.select_one('.item-heading').insert_after(links)

    products = [product for product in data['used_by'].get(slug, []) if product in mapping['items'] and product in data['items']]
    if products:
        section = soup.new_tag('details', attrs={'class': 'used-in'})
        summary = soup.new_tag('summary'); summary.string = tr('用于制作') + ' · ' + str(len(products))
        section.append(summary)
        nav = soup.new_tag('nav', attrs={'class': 'related-pages', 'id': 'used-in', 'aria-label': tr('用于制作')})
        for product in products:
            anchor = soup.new_tag('a', href=locale_root + product + '.html')
            anchor.string = item_name(product, mapping, translator); nav.append(anchor)
        section.append(nav); content.append(section)


def add_catalog_search(soup, data):
    for card in soup.select('.catalog-card'):
        slug = Path(card['href'].split('?')[0]).stem
        # 兼容已发布的旧物品名；额外的玩家叫法仍由 search-aliases.json 明确维护。
        card['data-search-aliases'] = json.dumps(data['aliases'][slug], ensure_ascii=False)
        card['data-search-name'] = ' '.join(node.get_text(' ', strip=True) for node in card.select('.catalog-copy b, .catalog-copy small'))
    field = soup.select_one('#item-search')
    field['aria-controls'] = 'items'


def add_discovery(soup, page, mapping, translator, locale_root, asset_root):
    """统一在翻译和旧链接处理之后添加，所有新链接明确指向当前语种。"""
    tr = translator.text
    data = discovery_data()
    if page == 'index.html':
        add_home_tools(soup, locale_root, mapping, translator, data)
    elif page not in {'items.html', 'loot.html'}:
        soup.select_one('.header-inner').append(search_form(soup, locale_root, translator))
    if page == 'items.html':
        add_catalog_search(soup, data)
    slug = Path(page).stem
    if slug in mapping['items']:
        add_item_links(soup, slug, locale_root, mapping, translator, data)

    sidebar = soup.select_one('.sidebar')
    if sidebar:
        menu = soup.new_tag('details', attrs={'class': 'category-menu', 'open': ''})
        summary = soup.new_tag('summary'); summary.string = tr('分类')
        sidebar.wrap(menu); menu.insert(0, summary)

    # 配方版本取自同一份计算数据；旧战斗数据继续保留其原有版本与未验证说明。
    note = soup.select_one('[data-recipe-version]')
    if note:
        note.string = tr('配方数据版本') + ' · ' + data['recipes']['version']
    if page == 'crafting.html':
        version = soup.new_tag('p', attrs={'class': 'craft-data-version'})
        version.string = tr('配方数据版本') + ' · ' + data['recipes']['version']
        soup.select_one('.craft-intro > div').append(version)
    if page.startswith('gameplay/') and page != 'gameplay/index.html':
        headings = soup.select('.gameplay-body h2')
        if len(headings) >= 3:
            toc = soup.new_tag('nav', attrs={'class': 'article-toc', 'aria-label': tr('文章目录')})
            title = soup.new_tag('h2'); title.string = tr('文章目录'); toc.append(title)
            for index, heading in enumerate(headings, 1):
                heading['id'] = heading.get('id') or 'guide-section-' + str(index)
                anchor = soup.new_tag('a', href='#' + heading['id']); anchor.string = heading.get_text(' ', strip=True)
                toc.append(anchor)
            soup.select_one('.gameplay-article h1').insert_after(toc)
    script = soup.new_tag('script', src=asset_root + 'static/discovery.js', defer=True)
    soup.head.append(script)
