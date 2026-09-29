"""生成列表用缩略图，并为静态图片设置尺寸与加载策略。"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
THUMBNAIL_SIZE = 128


@lru_cache(maxsize=None)
def thumbnail_image(image: str) -> str:
    """只替换体积更小的缩略图；保留原图，内容指纹避免更新后命中旧缓存。"""
    source = STATIC / image
    content = source.read_bytes()
    name = f'{source.stem}-{sha256(content).hexdigest()[:12]}.webp'
    target = STATIC / 'thumbnails' / name
    target.parent.mkdir(exist_ok=True)
    with Image.open(source) as original:
        thumb = original.convert('RGBA')
        thumb.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        thumb.save(target, 'WEBP', quality=85, method=6)
    if target.stat().st_size >= len(content):
        target.unlink()
        return image
    return target.relative_to(STATIC).as_posix()


@lru_cache(maxsize=None)
def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def optimize_images(soup, page: str, lang: str, localized: bool) -> None:
    """保留真实 src 供抓取；首批列表图立即加载，首屏主图与标志不懒加载。"""
    directory = (ROOT / lang / page).parent if localized else (ROOT / page).parent
    list_count = 0
    for image in soup.select('img[src]'):
        url = urlsplit(image['src'])
        if url.scheme or url.netloc:
            continue
        source = (directory / url.path).resolve()
        if not source.is_relative_to(STATIC) or not source.is_file():
            continue
        classes = set(image.get('class', []))
        is_list = bool(classes & {'catalog-image', 'recycle-image', 'material-icon'})
        if is_list:
            relative = source.relative_to(STATIC).as_posix()
            replacement = thumbnail_image(relative)
            image['src'] = image['src'].replace(relative, replacement)
            source = STATIC / replacement
            list_count += 1
        width, height = image_size(source)
        image['width'], image['height'] = str(width), str(height)
        image['decoding'] = 'async'
        prominent = bool(classes & {'brand-mark', 'hero-logo', 'item-image'})
        image['loading'] = 'eager' if prominent or (is_list and list_count <= 8) else 'lazy'
