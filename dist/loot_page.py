"""战利品页面：展示已解析奖励池及物品用途，不推测地图来源或实际掉率。"""
import json
from pathlib import Path

ROOT = Path(__file__).parent


def load_loot():
    data = json.loads((ROOT / 'static/loot.json').read_text())
    if len(data['sources']) != 1 or data['sources'][0]['id'] != 'military-crate':
        raise ValueError('当前页面只展示军用箱奖励池；增加其他来源时须同步页面结构和说明。')
    return data


def page(header, footer):
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>战利品 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><script defer src="./static/loot.js"></script></head><body>{header('./', selected='loot')}<main class="page-shell loot-page"><section class="loot-intro"><h1>战利品</h1><p>查看可能获得的物品，以及它们的制作用途。</p></section><section class="loot-source" id="military-crate"><h2>军用箱奖励池</h2><p class="data-version" id="loot-version"></p><p class="loot-note">此处列出奖励池中的可能物品，不代表每次都会获得全部物品。</p><p class="loot-note">箱体来源、出现地点、刷新条件和实际掉落概率尚未确认。</p><form class="loot-search" role="search"><label><span class="visually-hidden">搜索奖励物品</span><input type="search" id="loot-search" name="q" placeholder="搜索名称、英文名或别名" aria-controls="loot-items" autocomplete="off"></label><button type="reset">清除搜索</button></form><p id="loot-count" role="status" aria-live="polite"></p><div id="loot-items" class="loot-items"></div><p id="loot-empty" hidden>没有找到匹配的奖励物品。</p></section></main>{footer()}</body></html>'''


def render_loot(soup, mapping, translator, locale_root, asset_root):
    """在翻译之后按物品 ID 生成同语种链接；未收录详情的奖励仍显示名称，不生成坏链接。"""
    from build_i18n import game_text, load_game_en
    from site_discovery import discovery_data

    tr = translator.text
    data = load_loot()
    source = data['sources'][0]
    discovery = discovery_data()
    english = load_game_en()
    container = soup.select_one('#loot-items')
    count = soup.select_one('#loot-count')
    count.string = tr('已收录 {count} 种可能奖励').format(count=len(source['items']))
    count['data-label'] = tr('找到 {count} 种奖励')
    soup.select_one('#loot-version').string = tr('奖励池配置版本') + ' · ' + data['version']

    def name(slug):
        token = mapping['items'][slug]['name']
        return game_text(translator.game[token])

    for slug in source['items']:
        item = discovery['items'].get(slug)
        linked = item is not None and slug in mapping['items']
        if linked:
            token = mapping['items'][slug]['name']
            title, en_name = name(slug), game_text(english[token])
        else:
            extra = data['extra_items'][slug]
            title = game_text(translator.game.get(extra['name_token']) or extra['english'])
            en_name = game_text(english.get(extra['name_token']) or extra['english'])
        aliases = [slug] + discovery['aliases'].get(slug, [])
        if not linked:
            aliases.append(data['extra_items'][slug]['english'])
        article = soup.new_tag('article', attrs={'class': 'loot-item', 'data-item-id': slug,
            'data-item-name': title, 'data-search-name': title + ' ' + en_name,
            'data-search-aliases': json.dumps(aliases, ensure_ascii=False)})
        heading = soup.new_tag('div', attrs={'class': 'loot-item-heading'})
        if item and item.get('image'):
            image = soup.new_tag('img', src=asset_root + 'static/' + item['image'], alt=title,
                                 attrs={'class': 'catalog-image'})
            heading.append(image)
        copy = soup.new_tag('div')
        title_node = soup.new_tag('h3')
        if linked:
            anchor = soup.new_tag('a', href=locale_root + slug + '.html')
            anchor.string = title; title_node.append(anchor)
        else:
            title_node.string = title
        copy.append(title_node)
        if translator.lang != 'en' and title != en_name:
            subtitle = soup.new_tag('small'); subtitle.string = en_name; copy.append(subtitle)
        heading.append(copy); article.append(heading)

        products = [product for product in discovery['used_by'].get(slug, [])
                    if product in mapping['items'] and product in discovery['items']]
        if products:
            uses = soup.new_tag('div', attrs={'class': 'loot-uses'})
            label = soup.new_tag('span'); label.string = tr('用于制作'); uses.append(label)
            for product in products[:3]:
                anchor = soup.new_tag('a', href=locale_root + product + '.html')
                anchor.string = name(product); uses.append(anchor)
            if len(products) > 3:
                anchor = soup.new_tag('a', href=locale_root + slug + '.html#used-in')
                anchor.string = tr('全部用途') + ' ↗'; uses.append(anchor)
            article.append(uses)
        if linked and (ammo := discovery['ammunition'].get(slug)) in mapping['items']:
            uses = soup.new_tag('div', attrs={'class': 'loot-uses'})
            label = soup.new_tag('span'); label.string = tr('使用弹药'); uses.append(label)
            anchor = soup.new_tag('a', href=locale_root + ammo + '.html')
            anchor.string = name(ammo); uses.append(anchor); article.append(uses)
        if not linked:
            note = soup.new_tag('p', attrs={'class': 'loot-note'})
            note.string = tr('详情暂未收录'); article.append(note)
        container.append(article)
