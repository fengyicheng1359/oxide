"""目录首页对外使用带斜杠的地址，磁盘仍保留 index.html 文件。"""
import re
from urllib.parse import urlsplit, urlunsplit


def directory_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.path == 'index.html' or parts.path.endswith('/index.html'):
        path = parts.path[:-len('index.html')] or './'
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    return value


def normalize_index_links(source: str, site_url: str) -> str:
    """只改本站 URL，不改页面文件标识、外部链接和脚本里的业务配置。"""
    def replace_attribute(match: re.Match) -> str:
        value = match.group(2)
        parts = urlsplit(value)
        if parts.scheme or parts.netloc:
            if parts.netloc != urlsplit(site_url).netloc:
                return match.group(0)
        return match.group(1) + directory_url(value) + match.group(3)

    source = re.sub(r'((?:href|value|content)=")([^"]*)(")', replace_attribute, source)
    # JSON-LD 中的页面地址与 canonical 保持一致。
    return re.sub(r'("url":\s*")(' + re.escape(site_url.rstrip('/')) + r'/[^"\s]*)(")', replace_attribute, source)
