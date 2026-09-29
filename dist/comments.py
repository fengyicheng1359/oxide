"""为页面添加本站评论入口脚本；Disqus 仅在用户点击按钮后加载。"""
from html import escape


def add_comments(source: str, prefix: str, config: dict) -> str:
    shortname = config.get('disqus_shortname', '')
    if not shortname or 'data-community-script' in source:
        return source
    assets = (
        f'<link rel="stylesheet" href="{escape(prefix, quote=True)}static/comments.css">'
        f'<script defer data-community-script data-shortname="{escape(shortname, quote=True)}" '
        f'data-site-url="{escape(config["site_url"].rstrip("/"), quote=True)}" '
        f'src="{escape(prefix, quote=True)}static/comments.js"></script>'
    )
    return source.replace('</head>', assets + '</head>', 1)
