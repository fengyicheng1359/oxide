"""由独立文案生成九语种评论政策；根目录入口固定为英文，不随浏览器跳转。"""
import json
from html import escape
from pathlib import Path
from bs4 import BeautifulSoup
from build_i18n import LANGUAGES, add_language_picker, add_ad_script
from page_urls import normalize_index_links

ROOT = Path(__file__).resolve().parent


def write_comment_policies() -> list[Path]:
    config = json.loads((ROOT / 'static/site-config.json').read_text(encoding='utf-8'))
    translations = json.loads((ROOT / 'static/i18n/comment-policy.json').read_text(encoding='utf-8'))
    site_url = config['site_url'].rstrip('/')
    pages = []
    # 根目录是对外填写的稳定英文地址；各语种目录各自拥有政策页。
    for lang, localized in [('en', False), *((code, True) for code in LANGUAGES)]:
        text = translations[lang]
        prefix = '../' if localized else './'
        relative = f'{lang}/comment-policy.html' if localized else 'comment-policy.html'
        home = './index.html' if localized else './en/index.html'
        canonical = site_url + '/' + relative
        rules = ''.join(f'<li>{escape(rule)}</li>' for rule in text['rules'])
        alternates = ''.join(f'<link rel="alternate" hreflang="{html_lang}" href="{site_url}/{code}/comment-policy.html">' for code, (_, html_lang) in LANGUAGES.items())
        source = f'''<!doctype html>
<html lang="{LANGUAGES[lang][1]}" data-language="{lang}" data-page-path="comment-policy.html" data-site-root="{prefix}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(text['title'])} | MyOxide</title>
<meta name="description" content="{escape(text['intro'], quote=True)}">
<link rel="canonical" href="{canonical}">{alternates}
<link rel="alternate" hreflang="x-default" href="{site_url}/comment-policy.html">
<link rel="stylesheet" href="{prefix}styles.css">
<link rel="stylesheet" href="{prefix}static/comment-policy.css">
<script defer src="{prefix}static/language.js"></script>
</head><body>
<header class="site-header"><div class="header-inner"><a href="{home}">{escape(text['home'])}</a></div></header>
<main class="policy"><article>
<h1>{escape(text['title'])}</h1><p>{escape(text['intro'])}</p>
<h2>{escape(text['rules_title'])}</h2><ul>{rules}</ul>
<h2>{escape(text['moderation_title'])}</h2><p>{escape(text['moderation'])}</p><p>{escape(text['enforcement'])}</p>
<h2>{escape(text['about_title'])}</h2><p>{escape(text['about'])}</p>
</article><footer>MyOxide · Oxide: Survival Island</footer></main></body></html>'''
        soup = BeautifulSoup(source, 'html.parser')
        add_ad_script(soup)
        add_language_picker(soup, 'comment-policy.html', lang, localized, lambda _: text['language'])
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(normalize_index_links(str(soup), site_url), encoding='utf-8')
        pages.append(path)
    return pages


if __name__ == '__main__':
    write_comment_policies()
