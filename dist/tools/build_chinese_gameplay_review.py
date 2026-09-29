"""生成仅供中文审核的玩法文章：python3 dist/tools/build_chinese_gameplay_review.py。

审核稿独立保存，不要求其他语言提前提供译文。完整站点重新生成后，
再次运行本脚本即可恢复中文审核入口；审核通过后再纳入正式多语言文章。
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup
import build_i18n as i18n
import build_static as site


def main() -> None:
    drafts = i18n.load(i18n.DATA / 'gameplay-review/zh.json')
    guides = i18n.load_guides('zh')
    if guides.keys() & drafts.keys():
        raise ValueError('审核文章与正式文章标识重复，请先移除已经转正的审核稿')
    guides.update(drafts)
    articles = site.gameplay_articles()
    articles.extend({'slug': slug, 'title': row['title'], 'category': row['category'],
                     'content': row['text']} for slug, row in drafts.items())
    mapping = i18n.load(i18n.DATA / 'item-tokens.json')
    translator = i18n.Translator('zh', mapping)
    site_url = i18n.load(i18n.ROOT / 'static/site-config.json')['site_url'].rstrip('/')
    sources = {'gameplay/index.html': site.gameplay_index_page(articles)}
    for article in articles:
        if article['slug'] in drafts:
            sources[f"gameplay/{article['slug']}.html"] = site.gameplay_article_page(article, articles)
        else:
            # 已有文章仅替换侧栏数量，保留正文及页面其他内容。
            sidebar = site.gameplay_sidebar(articles, article['category']).replace('<br>', '<br/>')
            for directory in (i18n.ROOT, i18n.ROOT / 'zh'):
                path = directory / 'gameplay' / f"{article['slug']}.html"
                content = path.read_text(encoding='utf-8')
                content = re.sub(r'<aside class="gameplay-sidebar">.*?</aside>',
                                 lambda _: sidebar, content, count=1, flags=re.S)
                path.write_text(content, encoding='utf-8')
    for page, source in sources.items():
        for localized in (False, True):
            content = i18n.render(site.clean_page_branding(source), page, 'zh', mapping,
                                  guides, translator, site_url, localized=localized)
            soup = BeautifulSoup(content, 'html.parser')
            if Path(page).stem in drafts:
                # 第三方经验与官方资料分别署名，避免统一显示为官方原文。
                draft = drafts[Path(page).stem]
                if draft.get('source_label'):
                    soup.select_one('.article-source').string = draft['source_label'] + ' ↗'
                # 这些文章尚无其他译文；旧入口也留在中文，避免自动跳转到空页面。
                soup.html.attrs.pop('data-legacy-page', None)
                for tag in soup.select('link[rel="alternate"]'):
                    if tag.get('hreflang') not in ('zh-CN', 'x-default'):
                        tag.decompose()
                for option in soup.select('#site-language option'):
                    if option.get('data-language') != 'zh':
                        option.decompose()
                for link in soup.select('.language-fallback a'):
                    if link.get('hreflang') != 'zh-CN':
                        link.decompose()
            destination = i18n.ROOT / ('zh' if localized else '') / page
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(str(soup), encoding='utf-8')
    print(f'已生成 {len(drafts)} 篇中文审核稿，中文玩法列表共 {len(articles)} 篇')


if __name__ == '__main__':
    main()
