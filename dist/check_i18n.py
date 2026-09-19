"""核对每个语种的页面、资源链接、SEO 和玩法内容；任一遗漏均使检查失败。"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
from bs4 import BeautifulSoup
from build_i18n import ROOT, DATA, LANGUAGES, load_guides


def main():
    expected = {p.relative_to(ROOT/'zh') for p in (ROOT/'zh').rglob('*.html')}
    config = json.loads((ROOT/'static/config.json').read_text())
    item_pages = {Path(item['image']).stem + '.html' for items in config.values() for item in items if item.get('image')}
    required = {Path(name) for name in item_pages | {'index.html', 'items.html', 'play.html', 'about.html', 'recycling.html', 'attack.html', 'defense.html', 'healing.html', 'threat.html'}}
    required |= {Path('gameplay') / (slug + '.html') for slug in load_guides('zh')}
    required.add(Path('gameplay/index.html'))
    assert expected == required, (expected ^ required)
    errors = []
    pages = 0
    site_url = json.loads((ROOT/'static/site-config.json').read_text())['site_url'].rstrip('/')
    for lang, (_, html_lang) in LANGUAGES.items():
        paths = {p.relative_to(ROOT/lang) for p in (ROOT/lang).rglob('*.html')}
        assert paths == expected, (lang, paths ^ expected)
        guides = load_guides(lang)
        for relative in sorted(paths):
            path = ROOT/lang/relative
            soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
            assert soup.html['lang'] == html_lang, path
            assert soup.select_one('link[rel=canonical]')['href'] == f'{site_url}/{lang}/{relative.as_posix()}', path
            alternates = soup.select('link[rel=alternate][hreflang]')
            assert len(alternates) == 10 and len({a['hreflang'] for a in alternates}) == 10, path
            options = soup.select('#site-language option')
            assert [o['data-language'] for o in options] == list(LANGUAGES), path
            assert [o['data-language'] for o in options if o.has_attr('selected')] == [lang], path
            for option in options:
                target = (path.parent/option['value']).resolve()
                assert target == (ROOT/option['data-language']/relative).resolve(), path
            for element in soup.select('[href], [src], [poster]'):
                for attr in ('href', 'src', 'poster'):
                    if not element.has_attr(attr): continue
                    url = urlsplit(element[attr])
                    if url.scheme or url.netloc or not url.path: continue
                    target = (path.parent/unquote(url.path)).resolve()
                    if not target.is_file(): errors.append(f'{path.relative_to(ROOT)}: {element[attr]}')
                    if attr == 'href' and element.name == 'a' and target.suffix == '.html' and not element.find_parent('noscript'):
                        assert target.is_relative_to((ROOT/lang).resolve()), (path, element[attr])
            if relative.parts[0] == 'gameplay' and relative.stem != 'index':
                assert soup.select_one('.gameplay-article h1').get_text() == guides[relative.stem]['title'], path
                body = soup.select_one('.gameplay-body')
                body.select_one('.article-source').decompose()
                assert body.get_text(' ', strip=True) == guides[relative.stem]['text'], path
            assert '__OFFICIAL_TITLE__' not in str(soup), path
            pages += 1
        print(lang, len(paths), 'pages checked', flush=True)
    assert not errors, '\n'.join(errors[:40])
    from xml.etree import ElementTree
    sitemap = ElementTree.parse(ROOT/'sitemap.xml')
    assert len(sitemap.getroot()) == pages
    print(f'PASS: {pages} localized pages; all nine language sets, links, assets, articles and SEO checked.')


if __name__ == '__main__':
    main()
