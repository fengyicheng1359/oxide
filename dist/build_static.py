#!/usr/bin/env python3
"""根据 static/config.json 生成纯静态物品目录和物品详情页。"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).parent
STATIC = ROOT / "static"
HTML_DIR = ROOT
GAMEPLAY_SOURCE_DIR = ROOT.parent / "tmp" / "gameplay"
CONFIG_FILE = STATIC / "config.json"
SITE_CONFIG_FILE = STATIC / "site-config.json"
ARMOR_CATEGORIES = {"Feet Equipment", "Head Equipment", "Legs Equipment", "Suit", "Torso Equipment"}
EQUIPMENT_CATEGORIES = ARMOR_CATEGORIES | {"Backpack Equipment"}
DISPLAY_CATEGORY_ORDER = ["Construction", "Tool", "Weapon", "Ammunition", "Medical", "Armor", "Material", "Other"]
RECYCLE_MATERIALS = [
    ("废料", "Scrap"),
    ("高品质金属", "High Quality Metal"),
    ("金属碎片", "Metal Fragment"),
    ("木材", "Wood"),
    ("石头", "Stone"),
]
ARMOR_DISPLAY_PROTECTION = [(9, "射击"), (10, "近战"), (11, "寒冷")]
THREAT_NPCS = [
    ("困难防御者", "RT Defender Hard", "困难"),
    ("沙地困难防御者", "RT Defender Hard Sand", "困难"),
    ("中等防御者", "RT Defender Medium Sand", "中等"),
    ("简单防御者", "RT Defender Easy", "简单"),
    ("沙地简单防御者", "RT Defender Easy Sand", "简单"),
    ("RT 新手人机", "RT Newbie", "新手"),
    ("自由行走新手人机", "Free Walking Newbie", "新手"),
    ("道路巡逻人机", "Road Patrol", "未确认"),
    ("新手道路巡逻人机", "Road Patrol Newbie", "未确认"),
]


def site_config() -> dict:
    return json.loads(SITE_CONFIG_FILE.read_text(encoding="utf-8"))


def configured_site_name() -> str:
    return str(site_config().get("site_name") or "氧化物生存岛爱好者论坛")


def seo_head(title: str, description: str, page_path: str, keywords: list[str] | None = None) -> str:
    """生成每个静态页面共用的 SEO 标签和可选的 Google Analytics、AdSense 代码。"""
    config = site_config()
    site_name = configured_site_name()
    site_url = str(config.get("site_url") or "").rstrip("/")
    canonical = f"{site_url}/{page_path.lstrip('/')}" if site_url else ""
    keyword_values = keywords or config.get("default_keywords", [])
    # 全站关键词始终追加到页面关键词中，去重并保留原有顺序。
    keyword_values = dict.fromkeys([*keyword_values, *config.get("shared_keywords", [])])
    keyword_text = ", ".join(str(keyword) for keyword in keyword_values if keyword)
    canonical_tag = f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ""
    favicon_data_uri = str(config.get("favicon_data_uri") or "").strip()
    favicon_path = str(config.get("favicon_path") or "").strip()
    favicon_href = favicon_data_uri or favicon_path
    favicon_type = ' type="image/jpeg"' if favicon_path.lower().endswith(('.jpg', '.jpeg')) else ""
    favicon_tag = f'<link rel="icon"{favicon_type} href="{esc(favicon_href)}">' if favicon_href else ""
    analytics_id = str(config.get("google_analytics_id") or "").strip()
    analytics = ""
    if analytics_id:
        analytics = f'''<!-- Google tag (gtag.js) -->
      <script async src="https://www.googletagmanager.com/gtag/js?id={esc(analytics_id)}"></script>
      <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{esc(analytics_id)}');
      </script>'''
    adsense_client = str(config.get("google_adsense_client") or "").strip()
    adsense = ""
    if adsense_client:
        adsense = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(adsense_client)}" crossorigin="anonymous"></script>'
    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": site_url,
        "inLanguage": "zh-CN",
    }, ensure_ascii=False).replace("</", "<\\/")
    return f'''<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keyword_text)}"><meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:site_name" content="{esc(site_name)}">{canonical_tag}{favicon_tag}<script type="application/ld+json">{structured_data}</script>{analytics}{adsense}'''


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def slug_for(item: dict, index: int) -> str:
    image = item.get("image") or ""
    if image:
        return Path(image).stem
    value = item.get("name_en") or item.get("name_zh") or f"item-{index}"
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or f"item-{index}"


def image_tag(item: dict, prefix: str, class_name: str, alt: str) -> str:
    image = item.get("image")
    if not image:
        return f'<span class="{class_name} missing-image">NO IMAGE</span>'
    return f'<img class="{class_name}" src="{prefix}static/{esc(image)}" alt="{esc(alt)}">'


def category_name(category: str) -> str:
    return {
        "Ammunition": "弹药", "Backpack Equipment": "背包", "Component": "组件",
        "Construction": "建筑", "Consumable": "消耗品", "Feet Equipment": "足部装备",
        "Head Equipment": "头部装备", "Interactable": "可交互物", "Legs Equipment": "腿部装备",
        "Other": "其他", "Resource": "资源", "Suit": "套装", "Equipment": "装备", "Tool": "工具",
        "Medical": "医疗", "Armor": "护甲", "Material": "材料",
        "Torso Equipment": "躯干装备", "Weapon": "武器", "Weapon Mod": "武器配件",
    }.get(category, category)


def display_category(category: str) -> str:
    if category in {"Construction", "Interactable"}:
        return "Construction"
    if category == "Tool":
        return "Tool"
    if category == "Weapon":
        return "Weapon"
    if category == "Ammunition":
        return "Ammunition"
    if category == "Consumable":
        return "Medical"
    if category in EQUIPMENT_CATEGORIES:
        return "Armor"
    if category in {"Component", "Resource"}:
        return "Material"
    return "Other"


def armor_material_rank(item: dict) -> tuple[int, str]:
    text = " ".join([
        str(item.get("name_en") or ""),
        str(item.get("name_zh") or ""),
        " ".join(str(material.get("name_en") or "") for material in item.get("crafting_materials", [])),
        " ".join(str(material.get("name_zh") or "") for material in item.get("crafting_materials", [])),
    ]).lower()
    if any(keyword in text for keyword in ("military", "hazmat", "军用", "防化", "防火")):
        return 5, item.get("name_zh") or ""
    for rank, keywords in enumerate((("wood", "木"), ("bone", "骨"), ("leather", "皮"), ("metal", "金属"))):
        if any(keyword in text for keyword in keywords):
            return rank, item.get("name_zh") or ""
    return 4, item.get("name_zh") or ""


def header(prefix: str, index_href: str | None = None, *, selected: str | None = None) -> str:
    index_href = index_href or f"{prefix}index.html"
    # 由页面明确指定所属栏目；首页不选中任何栏目。
    entries = [
        ("items", "items.html", "物品"),
        ("gameplay", "gameplay/index.html", "玩法"),
        ("recycling", "recycling.html", "回收"),
        ("attack", "attack.html", "攻击力"),
        ("defense", "defense.html", "防御力"),
        ("healing", "healing.html", "治疗"),
        ("threat", "threat.html", "威胁"),
        ("about", "about.html", "关于"),
    ]
    links = []
    for key, path, label in entries:
        active = ' class="active" aria-current="page"' if key == selected else ""
        links.append(f'<a{active} href="{prefix}{path}">{label}</a>')
    return f'''<header class="site-header"><div class="header-inner">
      <a class="brand" href="{index_href}"><img class="brand-mark" src="{prefix}static/assets/OSAAS.jpeg" alt="氧化物生存岛百科全书"><span><strong>氧化物生存岛</strong><small>百科全书</small></span></a>
      <nav>{"".join(links)}</nav>
      <div class="header-tools"><span>中 / EN</span><span class="online"><i></i> STATIC DATA</span></div>
    </div></header>'''


def footer() -> str:
    return '<footer class="site-footer"><span>氧化物生存岛爱好者论坛</span><span>STATIC HTML · GENERATED FROM CONFIG.JSON</span></footer>'


GAMEPLAY_CATEGORY_RULES = [
    ("生存基础", ("睡眠者", "睡袋", "重生点", "生命值", "饥饿", "口渴", "食用", "饮用", "皮肤", "指南针", "标记", "生物群系", "安全区")),
    ("建造与基地", ("窗栏", "维修", "升级墙", "密码锁", "工具柜", "基地", "存储", "保险箱", "修理柜", "烹饪装置", "工作台", "制作菜单", "快速制作")),
    ("氏族与社交", ("氏族", "部落", "小队", "队友")),
    ("战斗与装备", ("武器配件", "配件", "军事护甲")),
    ("交通与探索", ("滑索", "电力线塔", "商人", "铁路", "火车", "载具", "军事基地", "战利品容器")),
]

GAMEPLAY_SLUG_CATEGORIES = {
    "-104": "建造与基地", "-113": "建造与基地", "-115": "建造与基地", "-122": "建造与基地",
    "-124": "建造与基地", "-188": "建造与基地", "-189": "建造与基地", "-72": "建造与基地",
    "-73": "建造与基地", "-74": "建造与基地", "-75": "建造与基地", "quick-craft-47": "建造与基地",
    "-131": "氏族与社交", "-176": "氏族与社交", "-177": "氏族与社交", "-178": "氏族与社交",
    "-180": "氏族与社交", "-182": "氏族与社交",
    "-108": "战斗与装备", "-126": "战斗与装备", "-193": "战斗与装备", "-208": "战斗与装备",
    "-112": "交通与探索", "-118": "交通与探索", "-224": "交通与探索", "-232": "交通与探索",
    "-69": "交通与探索", "-70": "交通与探索", "citadel-221": "交通与探索",
    "gather-resources-quickly": "生存基础",
    "avoid-animal-attacks": "战斗与装备",
    "lighthouse-basement": "交通与探索",
    "military-base-keycard": "交通与探索",
    "plane-crash-keycard": "交通与探索",
    "-241": "生存基础", "-242": "生存基础", "-29": "生存基础", "-32": "生存基础", "-43": "生存基础",
    "-44": "生存基础", "-45": "生存基础", "-46": "生存基础", "-52": "生存基础", "-57": "生存基础",
    "-58": "生存基础", "-65": "生存基础", "-82": "生存基础",
}

GAMEPLAY_CATEGORY_ANCHORS = {
    "生存基础": "survival",
    "建造与基地": "base-building",
    "氏族与社交": "clans",
    "战斗与装备": "combat",
    "交通与探索": "exploration",
}


def gameplay_category(title: str, content: str) -> str:
    """按文章标题和正文中的核心玩法词重新归类。"""
    text = f"{title} {content}"
    for category, keywords in GAMEPLAY_CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "生存基础"


def gameplay_articles() -> list[dict]:
    """读取下载的纯文本文章，清除客服页杂项并保留正文段落。"""
    cached = STATIC / "i18n/gameplay/zh.json"
    if cached.exists():
        from build_i18n import load_guides
        rows = load_guides('zh')
        return [{"slug": slug, "title": row["title"],
                 "category": GAMEPLAY_SLUG_CATEGORIES[slug],
                 "content": row["text"], "source_file": slug + ".html"}
                for slug, row in sorted(rows.items())]
    articles = []
    for text_file in sorted(GAMEPLAY_SOURCE_DIR.glob("*.txt")):
        lines = [line.strip() for line in text_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            continue
        title = re.sub(r"\s+–\s+Oxide: Survival Island 客服$", "", lines[0]).strip()
        body = []
        started = False
        for line in lines[1:]:
            if line == title:
                started = True
                continue
            if line == "这有帮助吗？":
                break
            if line in {"Oxide: Survival Island", "Chinese (Simplified)", ">", "玩法", "简短说明视频："}:
                continue
            if not started:
                continue
            body.append(line)
        content = "\n".join(body).strip()
        if not content:
            continue
        category = GAMEPLAY_SLUG_CATEGORIES.get(text_file.stem) or gameplay_category(title, content)
        articles.append({
            "slug": text_file.stem,
            "title": title,
            "category": category,
            "content": content,
            "source_file": text_file.name,
        })
    return articles


def gameplay_page_styles() -> str:
    return '''<style>
.gameplay-shell{max-width:1180px;margin:auto;padding:42px 28px 72px}.gameplay-intro{display:grid;grid-template-columns:minmax(200px,1fr) minmax(0,480px);gap:32px;align-items:end;margin-bottom:34px}.gameplay-intro h1{margin:9px 0 10px;color:var(--ink);font:600 clamp(42px,6vw,72px)/.95 var(--display);letter-spacing:-.04em}.gameplay-intro p{max-width:480px;margin:0;color:var(--muted);font-size:14px;line-height:1.8}.gameplay-category{margin:42px 0}.gameplay-category-heading{display:flex;align-items:baseline;gap:14px;padding-bottom:12px;border-bottom:1px solid var(--line)}.gameplay-category-heading h2{margin:0;color:var(--ink);font:600 30px var(--display)}.gameplay-category-heading span{color:var(--muted);font:10px var(--mono);letter-spacing:.08em}.gameplay-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:16px}.gameplay-card{display:flex;flex-direction:column;min-height:132px;padding:18px;background:var(--panel);border:1px solid var(--line);border-radius:8px;color:var(--ink);text-decoration:none;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}.gameplay-card:hover{transform:translateY(-3px);border-color:#8ebf5e;box-shadow:0 12px 26px #0007}.gameplay-card small{color:var(--green);font:10px var(--mono);letter-spacing:.08em}.gameplay-card strong{margin-top:12px;font-size:16px;line-height:1.45}.gameplay-card .arrow{margin-top:auto;padding-top:14px;color:var(--green);font-size:18px}.gameplay-article-shell{max-width:900px;margin:auto;padding:42px 28px 72px}.gameplay-breadcrumb{display:flex;gap:9px;margin-bottom:28px;color:var(--muted);font:10px var(--mono)}.gameplay-breadcrumb a{color:var(--green);text-decoration:none}.gameplay-article{padding:30px 34px 38px;background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:0 16px 36px #0005}.gameplay-article .eyebrow{color:var(--green)}.gameplay-article h1{margin:12px 0 28px;color:var(--ink);font:600 clamp(36px,5vw,62px)/1.05 var(--display);letter-spacing:-.03em}.gameplay-body{color:#dce8dc;font-size:16px;line-height:2}.gameplay-body p{margin:0 0 18px}.gameplay-back{display:inline-flex;margin-top:28px;color:var(--green);font-weight:700;text-decoration:none}.gameplay-back:hover{text-decoration:underline}@media(max-width:760px){.gameplay-shell,.gameplay-article-shell{padding:30px 18px 56px}.gameplay-intro{display:block}.gameplay-intro p{margin-top:18px}.gameplay-grid{grid-template-columns:1fr}.gameplay-article{padding:24px 20px 30px}.gameplay-body{font-size:15px;line-height:1.9}}
.gameplay-layout{display:grid;grid-template-columns:190px 1fr;gap:42px}.gameplay-sidebar{align-self:start;position:sticky;top:20px}.gameplay-sidebar h2{margin:0 0 13px;color:var(--ink);font-size:13px}.gameplay-sidebar a{display:flex;justify-content:space-between;padding:9px 12px;margin:2px 0;border-radius:6px;color:var(--muted);font-size:12px;text-decoration:none}.gameplay-sidebar a:hover,.gameplay-sidebar a:focus,.gameplay-sidebar a.selected{color:var(--green);background:var(--light);font-weight:600}.gameplay-sidebar b{font:10px var(--mono);font-weight:400}.gameplay-sidebar-foot{margin:38px 12px 0;color:var(--muted);font:10px/1.8 var(--mono)}.gameplay-category{scroll-margin-top:24px}
@media(max-width:760px){.gameplay-layout{display:block}.gameplay-sidebar{position:static;margin-bottom:34px;padding-bottom:18px;border-bottom:1px solid var(--line)}.gameplay-sidebar h2{margin-bottom:8px}.gameplay-sidebar a{display:inline-flex;margin:2px 3px 2px 0}.gameplay-sidebar-foot{display:none}}
</style>'''


def gameplay_header() -> str:
    return header("../", selected="gameplay")


def gameplay_sidebar(articles: list[dict], active_category: str | None = None) -> str:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        grouped.setdefault(article["category"], []).append(article)
    links = "".join(
        f'<a class="{"selected" if category == active_category else ""}" href="./index.html#gameplay-{GAMEPLAY_CATEGORY_ANCHORS[category]}"><span>{esc(category)}</span><b>{len(grouped.get(category, [])):02d}</b></a>'
        for category, _ in GAMEPLAY_CATEGORY_RULES if grouped.get(category)
    )
    return f'<aside class="gameplay-sidebar"><h2>玩法分类</h2>{links}<div class="gameplay-sidebar-foot">共 {len(articles)} 篇玩法<br>按主题重新整理</div></aside>'


def gameplay_index_page(articles: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {}
    for article in articles:
        grouped.setdefault(article["category"], []).append(article)
    sections = []
    for category, _ in GAMEPLAY_CATEGORY_RULES:
        category_articles = grouped.get(category, [])
        if not category_articles:
            continue
        cards = "".join(
            f'<a class="gameplay-card" href="./{esc(article["slug"])}.html"><small>{esc(category.upper())}</small><strong>{esc(article["title"])}</strong><span class="arrow">↗</span></a>'
            for article in category_articles
        )
        sections.append(f'<section id="gameplay-{GAMEPLAY_CATEGORY_ANCHORS[category]}" class="gameplay-category"><div class="gameplay-category-heading"><h2>{esc(category)}</h2><span>{len(category_articles):02d} ARTICLES</span></div><div class="gameplay-grid">{cards}</div></section>')
    sidebar = gameplay_sidebar(articles)
    head = seo_head(
        "玩法攻略 · 氧化物生存岛爱好者论坛",
        "氧化物生存岛玩法攻略，包含生存基础、基地建造、氏族社交、战斗装备、交通探索和游戏机制说明。",
        "gameplay/index.html",
        ["氧化物生存岛玩法", "氧化物生存岛攻略", "氧化物生存岛新手攻略", "基地建造", "氏族", "生存技巧"],
    )
    return f'''<!doctype html><html lang="zh-CN"><head>{head}{gameplay_page_styles()}<link rel="stylesheet" href="../styles.css"></head><body>{gameplay_header()}<main class="gameplay-shell"><div class="gameplay-layout">{sidebar}<section class="gameplay-content"><section class="gameplay-intro"><div><span class="eyebrow">GAMEPLAY FIELD MANUAL</span><h1>玩法攻略</h1></div><p>从第一次登陆荒岛，到建造基地、加入氏族，再到探索铁路和军事基地。这里整理了游戏中最重要的生存规则与玩法线索。</p></section>{"".join(sections)}</section></div></main>{footer()}</body></html>'''


def gameplay_article_page(article: dict, articles: list[dict]) -> str:
    paragraphs = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in article["content"].splitlines() if paragraph.strip())
    description = article["content"].splitlines()[0][:150]
    keywords = ["氧化物生存岛", "氧化物生存岛玩法", article["category"], article["title"]]
    head = seo_head(
        f"{article['title']} · 氧化物生存岛玩法攻略",
        description,
        f"gameplay/{article['slug']}.html",
        keywords,
    )
    sidebar = gameplay_sidebar(articles, article["category"])
    return f'''<!doctype html><html lang="zh-CN"><head>{head}{gameplay_page_styles()}<link rel="stylesheet" href="../styles.css"></head><body>{gameplay_header()}<main class="gameplay-shell"><div class="gameplay-layout">{sidebar}<section class="gameplay-article-main"><nav class="gameplay-breadcrumb" aria-label="面包屑"><a href="../index.html">首页</a><span>/</span><a href="./index.html">玩法攻略</a><span>/</span><span>{esc(article["category"])}</span></nav><article class="gameplay-article"><span class="eyebrow">{esc(article["category"].upper())}</span><h1>{esc(article["title"])}</h1><div class="gameplay-body">{paragraphs}</div><a class="gameplay-back" href="./index.html">← 返回玩法攻略</a></article></section></div></main>{footer()}</body></html>'''


def write_gameplay_pages() -> int:
    articles = gameplay_articles()
    output_dir = HTML_DIR / "gameplay"
    output_dir.mkdir(exist_ok=True)
    for old_page in output_dir.glob("*.html"):
        old_page.unlink()
    (output_dir / "index.html").write_text(gameplay_index_page(articles), encoding="utf-8")
    for article in articles:
        (output_dir / f"{article['slug']}.html").write_text(gameplay_article_page(article, articles), encoding="utf-8")
    return len(articles)


def clean_page_branding(content: str) -> str:
    replacements = {
        "游戏物品数据库": "游戏物品百科",
        "OXIDE WIKI": "OXIDE FANS FORUM",
        "RECYCLE DATABASE": "RECYCLE GUIDE",
        "THREAT DATABASE": "THREAT GUIDE",
        'href="./index.html#category-': 'href="./items.html#category-',
        "background:#111713;color:#f4f5ef;overflow:hidden": "background:#111713;color:#f4f5ef;overflow-x:hidden",
        '<span class="hero-kicker">OXIDE · SURVIVAL ISLAND</span><h1>氧化物：生存岛</h1><p>在残酷的开放世界中收集资源、制作装备、建造基地，与朋友并肩生存，征服属于你的岛屿。</p>':
            '<img class="hero-logo" src="./static/assets/OSAAS.jpeg" alt="氧化物：生存岛"><h1>氧化物：生存岛 - 生存、制作、征服！</h1><strong class="hero-publisher">HYPERHUG</strong><p class="hero-disclaimer">包含广告 · 应用内购商品</p>',
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def material_card(material: dict, lookup: dict[str, tuple[dict, str]], prefix: str) -> str:
    key = (material.get("name_en"), material.get("name_zh"))
    target = lookup.get(key)
    link = f"{prefix}{target[1]}.html" if target else "#"
    target_item = target[0] if target else material
    return f'''<a class="material-card" href="{esc(link)}" title="查看 {esc(material.get('name_zh'))} 详情">
      <span class="material-thumb">{image_tag(target_item, prefix, "material-icon", material.get("name_zh"))}</span>
      <span class="material-info"><span class="material-cn">{esc(material.get("name_zh"))}</span><span class="material-en">{esc(material.get("name_en"))}</span></span>
      <span class="amount">×{esc(material.get("amount"))}</span><span class="arrow">→</span></a>'''


def grouped_acquisition(methods: list[dict]) -> list[dict]:
    """把分析来源转换为玩家可见的获取方式，并按类型去重。"""
    grouped: dict[str, list[str]] = {}
    for method in methods:
        method_type = str(method.get("type") or "其他")
        detail = str(method.get("detail") or "")
        if "掉落" in method_type:
            method_type, detail = "掉落", "可通过掉落获得"
        elif "奖励" in method_type:
            method_type, detail = "奖励/商店", "可通过奖励或商店获得"
        elif "回收" in method_type:
            method_type = "回收"
            if detail.startswith("回收来源："):
                detail = detail[len("回收来源："):]
        elif "采集" in method_type:
            method_type, detail = "采集", "可通过采集获得"
        else:
            for prefix in ("熔炼来源：", "资源点候选："):
                if detail.startswith(prefix):
                    detail = detail[len(prefix):]
                    break
        if detail and detail not in grouped.setdefault(method_type, []):
            grouped[method_type].append(detail)
    result = []
    for method_type, details in grouped.items():
        if method_type in {"掉落", "奖励/商店", "采集"}:
            detail = details[0]
        elif method_type == "回收":
            detail = "可从" + "、".join(details) + "回收获得"
        elif "熔炉" in method_type and len(details) > 1:
            detail = "可通过熔炉加工获得：" + "、".join(details)
        elif len(details) == 1:
            detail = details[0]
        else:
            detail = f"共 {len(details)} 个候选来源：" + "、".join(details)
        result.append({"type": method_type, "detail": detail})
    return result


def sidebar(categories: dict[str, list[tuple[dict, str]]], prefix: str, selected: str = "", index_href: str | None = None, recycling_count: int = 0, attack_count: int = 0, threat_count: int = 0) -> str:
    if selected in {"Recycling", "Attack", "Defense", "Threat"}:
        return ""
    index_href = index_href or f"{prefix}index.html"
    links = []
    for category, items in categories.items():
        selected_class = " selected" if category == selected else ""
        links.append(f'<a class="{selected_class}" href="{index_href}#category-{esc(category)}">{esc(category_name(category))}<b>{len(items)}</b></a>')
    return f'<aside id="categories" class="sidebar"><div class="side-group"><div class="side-title">分类</div>{"".join(links)}</div><div class="side-foot">{sum(len(x) for x in categories.values())} ITEMS<br><span>LOCAL DATASET</span></div></aside>'


def consumable_usage(slug: str, detailed: bool = False) -> str:
    """展示每次使用的配置效果；持续回血只列持续时间，不把效果强度推算为总回血量。"""
    effects = json.loads((STATIC / "game-stats.json").read_text(encoding="utf-8"))["consumable_effects"].get(slug)
    if effects is None:
        return ""
    lines = []
    for field, label in [("hunger", "饱食度"), ("thirst", "水分")]:
        low, high = effects[field + "ChangeMin"], effects[field + "ChangeMax"]
        if low or high:
            value = f"{low:g}" if low == high else f"{low:g}–{high:g}"
            lines.append((f"{label} +{value}", False))
    health = effects["healthChange"]
    if health > 0:
        lines.append((f"立即恢复生命 +{health:g}", False))
    elif health < 0:
        lines.append((f"损失生命 {abs(health):g}", True))
    buff_labels = {"HealthRegenBuff": "持续恢复生命", "IncreaseSpeedBuff": "提升移动速度", "DecreaseColdBuff": "御寒效果"}
    if effects["buffName"]:
        lines.append((f"{buff_labels[effects['buffName']]} {effects['buffDurationSeconds']:g} 秒", False))
    for field, label in [("bpExpAmount", "通行证经验"), ("miniBpExpAmount", "活动通行证经验")]:
        if effects[field]:
            lines.append((f"{label} +{effects[field]:g}", False))
    if effects["consumeStorageId"]:
        lines.append(("使用后开出奖励", False))
    if detailed and effects["consumeCooldownSeconds"]:
        lines.append((f"使用间隔 {effects['consumeCooldownSeconds']:g} 秒", False))
    if not lines:
        lines.append(("暂无数据", False))
    entries = "".join(f'<span class="usage-effect{ " usage-negative" if negative else ""}">{esc(text)}</span>' for text, negative in lines)
    note = f'<span class="usage-note">{esc(effects["note"])}</span>' if effects["note"] else ""
    return f'<span class="usage-effects">{entries}</span>{note}'


def detail_page(item: dict, category: str, slug: str, categories: dict, lookup: dict, prefix: str, recycling_count: int, attack_count: int, threat_count: int) -> str:
    materials = item.get("crafting_materials", [])
    cards = "".join(material_card(material, lookup, prefix) for material in materials)
    acquisition = grouped_acquisition([method for method in item.get("acquisition_methods", []) if "回收" not in str(method.get("type"))])
    recycling_sources = item.get("recycling_sources", [])
    if recycling_sources:
        sources = "、".join(f'{esc(source.get("name_zh"))} ×{esc(source.get("amount"))}' for source in recycling_sources)
        acquisition.append({"type": "回收", "detail": f"可从{sources}回收获得"})
    recycling_outputs = item.get("recycling_outputs", [])
    sections = []
    if cards:
        sections.append(f'<div class="section-heading"><h2>制造配方</h2><span>CRAFTING RECIPE</span></div><div class="materials">{cards}</div>')
    if acquisition:
        methods = "".join(f'<div class="acquisition-row"><b>{esc(method.get("type"))}</b><span>{esc(method.get("detail"))}</span></div>' for method in acquisition)
        sections.append(f'<div class="section-heading"><h2>获取方式</h2><span>HOW TO OBTAIN</span></div><div class="acquisition-list">{methods}</div>')
    if not sections:
        sections.append('<div class="section-heading"><h2>获取方式</h2><span>HOW TO OBTAIN</span></div><div class="empty">暂无已解析获取方式。</div>')
    if recycling_outputs:
        outputs = "".join(material_card(output, lookup, prefix) for output in recycling_outputs)
        sections.append(f'<div class="section-heading"><h2>回收产物</h2><span>RECYCLE YIELD</span></div><div class="materials">{outputs}</div>')
    attack = item.get("attack_power")
    attack_text = "—" if attack is None else esc(attack)
    if category == "Weapon":
        facts = f'<div class="facts"><div class="fact attack-fact"><span>攻击力</span><strong>{attack_text}</strong></div></div>'
    elif category == "Medical":
        facts = f'<div class="consumable-facts"><h2>使用效果</h2>{consumable_usage(slug, detailed=True)}</div>'
    elif category == "Armor":
        protection = armor_protection(item)
        facts = '<div class="facts"><div class="fact attack-fact"><span>防御力</span><strong>游戏属性</strong><small>DEFENSE ATTRIBUTES</small></div></div>'
        if protection is not None:
            display_values = "".join(f'<div class="protection-row"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>' for label, value in armor_display_protection(protection))
            sections.append(f'<div class="section-heading"><h2>防御属性</h2><span>DEFENSE ATTRIBUTES</span></div><div class="protection-list">{display_values}</div>')
    else:
        facts = ""
    recipe_section = "".join(sections)
    item_name = str(item.get("name_zh") or item.get("name_en") or "物品")
    item_keywords = [item_name, str(item.get("name_en") or ""), f"氧化物生存岛{item_name}", f"{item_name}制作配方", f"{item_name}获取方式", f"{item_name}回收"]
    card_class = "item-card" if facts else "item-card single"
    attack_style = ".attack-fact{flex-direction:row;align-items:baseline;gap:14px}.attack-fact small{margin-left:auto}" if category in {"Weapon", "Armor"} else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      {seo_head(f"{item_name} · 氧化物生存岛 Wiki", f"查询氧化物生存岛{item_name}的英文名、制作配方、材料、获取方式和回收产物。", f"{slug}.html", item_keywords)}<link rel="stylesheet" href="{prefix}styles.css"><style>.item-card.single{{grid-template-columns:1fr}}{attack_style}.acquisition-list{{display:grid;gap:8px}}.acquisition-row{{display:flex;align-items:center;gap:14px;padding:14px;background:#fff;border:1px solid #dfe3df;border-radius:7px}}.acquisition-row b{{min-width:72px;color:#526f3c;font-size:12px}}.acquisition-row span{{color:#78807c;font-size:12px}}.protection-list{{display:grid;gap:8px;grid-template-columns:repeat(3,1fr)}}.protection-row{{display:flex;align-items:center;justify-content:space-between;padding:14px;background:#fff;border:1px solid #dfe3df;border-radius:7px}}.protection-row span{{color:#78807c;font-size:12px}}.protection-row strong{{color:#526f3c;font:600 24px var(--display)}}</style></head><body>
      {header(prefix, "./index.html", selected="items")}<main class="page-shell"><div class="breadcrumb"><a href="./index.html">首页</a><span>/</span><a href="./index.html#category-{esc(category)}">{esc(category_name(category))}</a><span>/</span>{esc(item.get("name_zh"))}</div>
      <div class="content-layout">{sidebar(categories, prefix, category, "./index.html", recycling_count, attack_count, threat_count)}<section class="item-content"><div class="item-heading"><div><span class="tag">{esc(category_name(category))}</span><h1>{esc(item.get("name_zh"))}</h1><p>{esc(item.get("name_en"))}</p></div><span class="item-id">ITEM · {esc(category.upper())}</span></div>
      <div class="{card_class}"><div class="item-image-wrap">{image_tag(item, prefix, "item-image", item.get("name_zh"))}<span class="image-caption">{esc(item.get("name_en"))} / {esc(category.upper())}</span></div>{facts}</div>
      {recipe_section}</section></div></main>{footer()}</body></html>'''


def recycling_item_count(categories: dict[str, list[tuple[dict, str]]]) -> int:
    return sum(
        1
        for items in categories.values()
        for item, _ in items
        if any(output.get("amount") or 0 for output in item.get("recycling_outputs", []))
    )


def attack_item_count(categories: dict[str, list[tuple[dict, str]]]) -> int:
    return len(categories.get("Weapon", []))


def armor_protection(item: dict) -> list[float] | None:
    """读取随站点保存的快照，构建不依赖仓库外的 APK 导出目录。"""
    data = json.loads((STATIC / "game-stats.json").read_text(encoding="utf-8"))
    return data["armor"].get(Path(item.get("image") or "").stem)


def armor_display_protection(protection: list[float] | None) -> list[tuple[str, str]]:
    if protection is None:
        return []
    return [(label, f"{round(protection[index] * 100):g}%") for index, label in ARMOR_DISPLAY_PROTECTION if index < len(protection)]


def armor_table_cells(protection: list[float] | None) -> str:
    values = dict(armor_display_protection(protection))
    return "".join(f'<td class="attack-amount">{esc(values.get(label, "—"))}</td>' for _, label in ARMOR_DISPLAY_PROTECTION)


def defense_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int, threat_count: int) -> str:
    items = [(item, slug, armor_protection(item)) for item, slug in categories.get("Armor", [])]
    items.sort(key=lambda row: (row[2] is None, -max(row[2] or [0]), row[0].get("name_zh") or ""))
    rows = "".join(f'<tr><td><a class="recycle-item" href="./{esc(slug)}.html">{image_tag(item, "./", "recycle-image", item.get("name_zh"))}<span><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small></span></a></td>{armor_table_cells(protection)}</tr>' for item, slug, protection in items)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>防御力 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.attack-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.attack-table{{width:100%;border-collapse:collapse;text-align:left}}.attack-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.attack-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.attack-table tr:last-child td{{border-bottom:0}}.attack-table tr:hover td{{background:#fbfcfa}}.attack-table .recycle-image{{width:50px;height:50px}}.attack-amount{{width:120px;color:var(--green);font:600 22px var(--display)}}.attack-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./", selected="defense")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Defense", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">DEFENSE RANKING</span><h1>防御力</h1><p>按照游戏界面的防护属性展示。</p></div><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="attack-table-wrap" tabindex="0"><table class="attack-table defense-table"><thead><tr><th>护甲</th><th>射击</th><th>近战</th><th>寒冷</th></tr></thead><tbody>{rows}</tbody></table></div><p class="attack-note">共 {len(items)} 件护甲；展示游戏界面中的射击、近战、寒冷防护百分比。</p></section></div></main>{footer()}</body></html>'''


def threat_data() -> tuple[list[dict], list[dict]]:
    data = json.loads((STATIC / "game-stats.json").read_text(encoding="utf-8"))
    return data["animals"], data["npcs"]


def threat_item_count() -> int:
    animals, npcs = threat_data()
    return len(animals) + len(npcs)


def items_page(categories: dict[str, list[tuple[dict, str]]]) -> str:
    cards = []
    for category, items in categories.items():
        if category == "Weapon":
            items = sorted(items, key=lambda pair: (pair[0].get("attack_power") is None, -(pair[0].get("attack_power") or 0), pair[0].get("name_zh") or ""))
        elif category == "Armor":
            items = sorted(items, key=lambda pair: armor_material_rank(pair[0]))
        cards.append(f'<section id="category-{esc(category)}" class="category-section"><div class="section-heading"><h2>{esc(category_name(category))}</h2><span>{esc(category.upper())} · {len(items)} ITEMS</span></div><div class="item-grid">')
        for item, slug in items:
            usage = consumable_usage(slug) if category == "Medical" else ""
            cards.append(f'<a class="catalog-card" href="./{esc(slug)}.html">{image_tag(item, "./", "catalog-image", item.get("name_zh"))}<span class="catalog-copy"><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small>{usage}</span></a>')
        cards.append('</div></section>')
    recycling_count = recycling_item_count(categories)
    attack_count = attack_item_count(categories)
    threat_count = threat_item_count()
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Oxide Wiki · Items</title><link rel="stylesheet" href="./styles.css"></head><body>{header("./", selected="items")}<main class="page-shell"><div class="search-row"><div><span class="eyebrow">OXIDE WIKI</span><h1>游戏物品数据库</h1><p>浏览物品、制造配方与生存资源。</p></div><div class="search">⌕ <span>搜索物品...</span></div></div><div class="catalog-layout">{sidebar(categories, "./", recycling_count=recycling_count, attack_count=attack_count, threat_count=threat_count)}<section id="items" class="catalog-content">{"".join(cards)}</section></div></main>{footer()}</body></html>'''


def add_items_search(page: str) -> str:
    """给物品页增加纯前端即时搜索，不影响其他静态页面。"""
    search_box = '''<label class="search" for="item-search"><span aria-hidden="true">⌕</span><input id="item-search" type="search" placeholder="搜索物品..." autocomplete="off"></label>'''
    script = '''<script>
      (() => {
        const input = document.querySelector('#item-search');
        const cards = [...document.querySelectorAll('.catalog-card')];
        const sections = [...document.querySelectorAll('.category-section')];
        if (!input || !cards.length) return;
        const normalize = value => value.trim().toLocaleLowerCase();
        const update = () => {
          const keyword = normalize(input.value);
          cards.forEach(card => {
            card.hidden = Boolean(keyword) && !normalize(card.textContent).includes(keyword);
          });
          sections.forEach(section => {
            section.hidden = !section.querySelector('.catalog-card:not([hidden])');
          });
        };
        input.addEventListener('input', update);
      })();
    </script>'''
    return page.replace('<div class="search">⌕ <span>搜索物品...</span></div>', search_box).replace('</body>', script + '</body>')


def add_pc_download(page: str) -> str:
    """在首页下载区域增加电脑版入口。"""
    card = '''<a class="download-card" href="https://www.bluestacks.com/apps/action/oxide-survival-island-on-pc.html" target="_blank" rel="noopener"><span><b>PC / Mac</b><small>下载电脑版</small></span><span class="arrow">↗</span></a>'''
    marker = '</a></section><footer class="promo-footer">'
    return page.replace(marker, '</a>' + card + '</section><footer class="promo-footer">', 1)


def index_page() -> str:
    gallery = "".join(
        f'<figure class="promo-shot"><img src="./static/loop-imge/loop-{index:02d}.jpg" alt="氧化物：生存岛游戏截图 {index}"></figure>'
        for index in range(1, 17)
    )
    promo_header = header("./")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>氧化物生存岛爱好者论坛</title><meta name="description" content="氧化物：生存岛官方游戏介绍、宣传视频、游戏截图以及 Android 和 Apple 下载入口。"><link rel="stylesheet" href="./styles.css"><style>
    .promo-page{{background:#111713;color:#f4f5ef;overflow:hidden}}.promo-page .site-header{{background:#111713;border-color:#2c352e}}.promo-page .brand strong{{color:#f4f5ef}}.promo-page .header-inner nav a{{color:#a9b5aa}}.promo-page .header-tools{{color:#879389}}.promo-shell{{max-width:1240px;margin:auto;padding:30px 28px 76px}}.hero{{position:relative;min-height:620px;display:flex;align-items:end;overflow:hidden;border:1px solid #38453a;border-radius:18px;background:#243128;box-shadow:0 25px 70px #0008}}.hero video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.65}}.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#0d120fef 0%,#0d120f99 44%,#0d120f12 78%),linear-gradient(0deg,#0d120fdb,#0d120f00 58%)}}.hero-copy{{position:relative;z-index:1;max-width:720px;padding:54px}}.hero-kicker{{color:#b3d391;font:11px var(--mono);letter-spacing:.18em}}.hero h1{{margin:16px 0 14px;font:600 clamp(46px,7vw,92px)/.92 var(--display);letter-spacing:-.04em}}.hero p{{max-width:580px;margin:0;color:#c7d0c5;font-size:17px;line-height:1.75}}.hero-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}}.hero-actions a,.download-card{{display:inline-flex;align-items:center;gap:10px;padding:13px 17px;border:1px solid #b3d391;border-radius:7px;color:#162016;background:#b3d391;font-weight:700}}.hero-actions a.secondary{{color:#e3eade;background:#1b261d;border-color:#566656}}.section-intro{{display:flex;align-items:end;justify-content:space-between;gap:24px;margin:72px 0 22px}}.section-intro h2{{margin:8px 0 0;font:600 44px/.95 var(--display)}}.section-intro p{{max-width:430px;margin:0;color:#9daa9e;line-height:1.7}}.eyebrow{{color:#98aa9a;font:11px var(--mono);letter-spacing:.16em}}.promo-window{{position:relative;overflow:hidden;padding:8px 0 22px}}.promo-track{{display:flex;width:max-content;gap:18px;animation:promo-scroll 72s linear infinite}}.promo-shot{{width:350px;height:198px;flex:none;margin:0;overflow:hidden;border:1px solid #3a493d;border-radius:10px;background:#202b22;box-shadow:0 12px 32px #0005}}.promo-shot img{{width:100%;height:100%;object-fit:cover;display:block;transition:transform .45s ease}}.promo-shot:hover img{{transform:scale(1.04)}}@keyframes promo-scroll{{from{{transform:translateX(0)}}to{{transform:translateX(calc(-50% - 9px))}}}}.promo-window:hover .promo-track{{animation-play-state:paused}}.download-panel{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:34px}}.download-card{{display:flex;justify-content:space-between;background:#1b261d;border-color:#3d503f;color:#e7eee4;text-decoration:none}}.download-card small{{display:block;margin-top:5px;color:#98aa9a;font:10px var(--mono)}}.download-card .arrow{{color:#b3d391;font-size:24px}}.promo-footer{{display:flex;justify-content:space-between;gap:20px;margin-top:76px;padding-top:24px;border-top:1px solid #303c32;color:#91a092;font:10px var(--mono);letter-spacing:.08em}}.promo-footer a{{color:#b3d391}}@media(max-width:760px){{.promo-shell{{padding:18px 16px 52px}}.hero{{min-height:600px}}.hero-copy{{padding:30px 24px}}.hero p{{font-size:15px}}.section-intro{{display:block;margin-top:50px}}.section-intro p{{margin-top:14px}}.promo-shot{{width:280px;height:158px}}.download-panel{{grid-template-columns:1fr}}.promo-footer{{display:block;line-height:2.2}}}}
    </style></head><body class="promo-page">{promo_header}<main class="promo-shell"><section class="hero"><video autoplay muted loop playsinline poster="./static/loop-imge/loop-01.jpg"><source src="./static/loop-imge/trailer.mp4" type="video/mp4"></video><div class="hero-copy"><span class="hero-kicker">OXIDE · SURVIVAL ISLAND</span><h1>氧化物：生存岛</h1><p>在残酷的开放世界中收集资源、制作装备、建造基地，与朋友并肩生存，征服属于你的岛屿。</p><div class="hero-actions"><a href="./items.html">浏览物品百科 <span>↗</span></a><a class="secondary" href="https://hyper-hug.com/" target="_blank" rel="noopener">访问官方网站 <span>↗</span></a></div></div></section><section class="section-intro"><div><span class="eyebrow">FROM THE ISLAND</span><h2>游戏现场</h2></div><p>官方页面中的游戏截图，展示荒岛求生、资源采集、基地建造与战斗场景。</p></section><section class="promo-window" aria-label="游戏截图轮播"><div class="promo-track">{gallery}{gallery}</div></section><section class="section-intro"><div><span class="eyebrow">JOIN THE SURVIVAL</span><h2>开始生存</h2></div><p>选择你的平台，下载《氧化物：生存岛》，进入多人在线生存世界。</p></section><section class="download-panel"><a class="download-card" href="https://play.google.com/store/apps/details?id=com.catsbit.oxidesurvivalisland&hl=zh" target="_blank" rel="noopener"><span><b>Android / Google Play</b><small>下载安卓版</small></span><span class="arrow">↗</span></a><a class="download-card" href="https://apps.apple.com/sg/app/%E6%B0%A7%E5%8C%96%E7%89%A9-%E7%94%9F%E5%AD%98%E5%B2%9B-%E7%94%9F%E5%AD%98-%E5%88%B6%E4%BD%9C-%E5%BE%81%E6%9C%8D/id1579424683?l=zh-Hans-CN" target="_blank" rel="noopener"><span><b>iPhone / App Store</b><small>下载苹果版</small></span><span class="arrow">↗</span></a></section><footer class="promo-footer"><span>氧化物生存岛爱好者论坛 · STATIC PAGE</span><span><a href="https://hyper-hug.com/" target="_blank" rel="noopener">官方网站</a> · HYPERHUG</span></footer></main></body></html>'''


def about_page() -> str:
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>关于 · 氧化物生存岛百科全书</title><link rel="stylesheet" href="./styles.css"><style>
    .about-shell{max-width:960px;margin:auto;padding:70px 28px 100px}.about-hero{padding:56px 0 62px;border-bottom:1px solid var(--line)}.about-kicker{color:var(--green);font:11px var(--mono);letter-spacing:.16em}.about-hero h1{max-width:760px;margin:18px 0 22px;font:600 clamp(42px,7vw,84px)/.94 var(--display);letter-spacing:-.04em}.about-hero p{max-width:700px;margin:0;color:var(--muted);font-size:18px;line-height:1.9}.about-quote{margin:48px 0;padding:28px 32px;border-left:4px solid var(--green);background:var(--light);font:600 clamp(24px,4vw,42px)/1.35 var(--display)}.about-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:34px}.about-card{padding:24px;background:var(--panel);border:1px solid var(--line);border-radius:8px}.about-card strong{display:block;margin-bottom:10px;font:600 24px var(--display)}.about-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.8}.about-note{margin-top:42px;color:var(--muted);font-size:13px;line-height:1.9}@media(max-width:760px){.about-shell{padding:42px 18px 70px}.about-hero{padding-top:28px}.about-hero p{font-size:16px}.about-quote{padding:22px 20px;margin:34px 0}.about-grid{grid-template-columns:1fr}}
    </style></head><body>''' + header("./", selected="about") + '''<main class="about-shell"><section class="about-hero"><span class="about-kicker">WELCOME TO THE ISLAND</span><h1>每一次出发，<br>都值得被记住。</h1><p>这里是氧化物生存岛百科全书。我们把岛上的物品、武器、护甲、材料和生存线索，整理成一张清晰的地图，让每一个刚踏上荒岛的孩子，都能找到属于自己的第一步。</p></section><blockquote class="about-quote">你不只是寻找答案，<br>你正在学会创造自己的生存故事。</blockquote><section class="about-grid"><article class="about-card"><strong>探索</strong><p>从一棵树、一块石头开始，认识岛上的每一种资源，发现未知角落里的惊喜。</p></article><article class="about-card"><strong>创造</strong><p>查找配方，制作工具和装备，把自己的想法变成真正可以使用的东西。</p></article><article class="about-card"><strong>并肩</strong><p>和朋友分享发现、交换经验，在一次次合作中，让普通的冒险变成难忘的回忆。</p></article></section><p class="about-note">这个站点是玩家整理的静态资料站，内容用于帮助大家更快了解游戏。真正精彩的部分，永远发生在你亲自踏上岛屿、做出选择、解决困难的那一刻。愿你带着好奇心出发，也带着属于自己的故事回来。</p></main><footer class="site-footer"><span>氧化物生存岛爱好者论坛</span><span>STATIC HTML · ABOUT</span></footer></body></html>'''


def play_page() -> str:
    head = seo_head(
        "玩法攻略 · 氧化物生存岛爱好者论坛",
        "了解氧化物生存岛的探索、资源采集、制造、基地建造、战斗和载具玩法。",
        "gameplay/index.html",
        ["氧化物生存岛玩法", "氧化物生存岛攻略", "资源采集", "基地建造", "空投", "军事基地", "直升机", "越野车"],
    )
    page_header = header("./", selected="gameplay")
    cards = [
        ("探索荒岛", "从森林、山地和海岸开始，寻找资源点、空投和军事基地，熟悉岛上的危险与机会。"),
        ("资源采集", "砍伐木材、开采石头和金属，收集布料、骨头与废料，为下一次制作做好准备。"),
        ("制造装备", "利用配方制作工具、武器、弹药和护具，逐步提升自己的生存能力。"),
        ("基地建造", "从简易木屋到装甲基地，使用墙体、门、舱门和领地柜建立安全的生存据点。"),
        ("战斗生存", "面对野兽和人机，选择合适的武器与护具，掌握攻击距离、攻击力和防护属性。"),
        ("载具与事件", "关注直升机、越野车、气球、加油站和空投，在移动与事件中获得更多资源。"),
    ]
    body = "".join(f'<article class="play-card"><span class="play-index">{index:02d}</span><h2>{esc(title)}</h2><p>{esc(description)}</p></article>' for index, (title, description) in enumerate(cards, 1))
    return f'''<!doctype html><html lang="zh-CN"><head>{head}<link rel="stylesheet" href="./styles.css"><style>.play-shell{{max-width:1120px;margin:auto;padding:64px 28px 100px}}.play-hero{{padding:12px 0 48px;border-bottom:1px solid var(--line)}}.play-kicker{{color:var(--green);font:11px var(--mono);letter-spacing:.16em}}.play-hero h1{{max-width:760px;margin:18px 0;font:600 clamp(44px,7vw,82px)/.94 var(--display);letter-spacing:-.04em}}.play-hero p{{max-width:700px;margin:0;color:var(--muted);font-size:17px;line-height:1.9}}.play-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:36px}}.play-card{{position:relative;min-height:190px;padding:24px;background:var(--panel);border:1px solid var(--line);border-radius:8px}}.play-card:hover{{border-color:var(--green);transform:translateY(-3px)}}.play-index{{color:var(--green);font:12px var(--mono);letter-spacing:.12em}}.play-card h2{{margin:28px 0 12px;font:600 27px var(--display)}}.play-card p{{margin:0;color:var(--muted);font-size:13px;line-height:1.8}}@media(max-width:760px){{.play-shell{{padding:42px 18px 70px}}.play-grid{{grid-template-columns:1fr}}}}</style></head><body>{page_header}<main class="play-shell"><section class="play-hero"><span class="play-kicker">SURVIVAL PLAYBOOK</span><h1>在岛上活下来，<br>也找到自己的玩法。</h1><p>从第一块石头、第一把工具，到基地、战斗与载具，认识氧化物生存岛的核心玩法，规划你的每一次出发。</p></section><section class="play-grid">{body}</section></main>{footer()}</body></html>'''


def recycling_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int) -> str:
    materials = [name_zh for name_zh, _ in RECYCLE_MATERIALS]
    rows = []
    all_items = [pair for items in categories.values() for pair in items]
    for item, slug in all_items:
        outputs = {output.get("name_zh"): output.get("amount", 0) for output in item.get("recycling_outputs", [])}
        values = [int(outputs.get(name_zh) or 0) for name_zh in materials]
        if not any(output.get("amount") or 0 for output in item.get("recycling_outputs", [])):
            continue
        rows.append((values, item, slug, outputs))
    rows.sort(key=lambda row: tuple(-value for value in row[0]) + (row[1].get("name_zh") or "",))
    body = []
    for values, item, slug, outputs in rows:
        cells = "".join(f'<td class="recycle-amount">{esc(outputs.get(name_zh) or "—")}</td>' for name_zh, _ in RECYCLE_MATERIALS)
        body.append(f'<tr><td><a class="recycle-item" href="./{esc(slug)}.html">{image_tag(item, "./", "recycle-image", item.get("name_zh"))}<span><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small></span></a></td>{cells}</tr>')
    headers = "".join(f'<th>{esc(name_zh)}</th>' for name_zh, _ in RECYCLE_MATERIALS)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>回收 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.recycling-intro{{margin-bottom:24px}}.recycling-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.recycling-intro p{{margin:0;color:var(--muted);font-size:13px}}.recycle-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.recycle-table{{width:100%;min-width:760px;border-collapse:collapse;text-align:left}}.recycle-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.recycle-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.recycle-table tr:last-child td{{border-bottom:0}}.recycle-table tr:hover td{{background:#fbfcfa}}.recycle-amount{{width:120px;color:var(--green);font:600 19px var(--display)}}.recycle-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./", selected="recycling")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Recycling", "./index.html", recycling_count, attack_count)}<section class="catalog-content"><div class="recycling-intro"><span class="eyebrow">RECYCLE DATABASE</span><h1>回收</h1><p>按单个物品可回收产物数量排序，数量相同则继续比较下一种材料。</p></div><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="recycle-table-wrap" tabindex="0"><table class="recycle-table"><thead><tr><th>物品</th>{headers}</tr></thead><tbody>{"".join(body)}</tbody></table></div><p class="recycle-note">共 {len(rows)} 件物品有已解析的回收产物；“—”表示该物品不产出此类材料。</p></section></div></main>{footer()}</body></html>'''


def attack_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int) -> str:
    items = sorted(categories.get("Weapon", []), key=lambda pair: (pair[0].get("attack_power") is None, -(pair[0].get("attack_power") or 0), pair[0].get("name_zh") or ""))
    # 对应关系取自物品配置：空字符串表示不使用弹药，缺少记录表示尚未确认。
    weapon_stats = json.loads((STATIC / "game-stats.json").read_text(encoding="utf-8"))
    ammunition_by_weapon = weapon_stats["weapon_ammunition"]
    ammunition_items = {slug: item for item, slug in categories.get("Ammunition", [])}
    rows = []
    for item, slug in items:
        attack_type = weapon_stats["weapon_attack_types"].get(slug, "未确认")
        attack = item.get("attack_power")
        value = "暂无数据" if attack is None else esc(attack)
        ammunition_id = ammunition_by_weapon.get(slug)
        if ammunition_id is None:
            ammunition = "未确认"
        elif ammunition_id == "":
            ammunition = "不使用弹药"
        else:
            ammunition_item = ammunition_items[ammunition_id]
            ammunition = f'<a href="./{esc(ammunition_id)}.html">{esc(ammunition_item["name_zh"])}</a>'
        # 仅展示已核对的基础配置；距离单位和衰减公式未确认，不标注为米或实测伤害。
        combat = weapon_stats.get("weapon_distance_reload", {}).get(slug)
        combat_values = ["未确认"] * 5
        combat_note = "—"
        if combat:
            high, low = combat["high_damage_point"], combat["low_damage_point"]
            combat_values = [f'({high["x"]:.2g}, {high["y"]:g})', f'({low["x"]:.2g}, {low["y"]:g})', f'{combat["max_distance"]:g}', str(combat["magazine"]), "逐发装填"]
            if combat["full_reload_seconds"] is not None:
                combat_values[4] = f'{combat["full_reload_seconds"]:g} s'
            elif not combat["loop_reload"]:
                combat_values[4] = "未确认"
            combat_note = combat["note"] or "—"
        combat_cells = [f'<td class="weapon-config-value">{esc(value)}</td>' for value in combat_values]
        reload_cells = "".join(combat_cells[3:5])
        combat_cells = "".join(combat_cells[:3])
        combat_cells += f'<td class="weapon-combat-note">{esc(combat_note)}</td>'
        rows.append(f'<tr><td><a class="recycle-item" href="./{esc(slug)}.html">{image_tag(item, "./", "recycle-image", item.get("name_zh"))}<span><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small></span></a></td><td class="attack-amount">{value}</td>{reload_cells}<td>{ammunition}</td><td>{esc(attack_type)}</td>{combat_cells}<td class="weapon-description" data-item-description="{esc(slug)}"></td></tr>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>攻击力 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.attack-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.attack-table{{width:100%;min-width:1600px;border-collapse:collapse;text-align:left}}.attack-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.attack-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.attack-table tr:last-child td{{border-bottom:0}}.attack-table tr:hover td{{background:#fbfcfa}}.attack-table .recycle-image{{width:50px;height:50px}}.weapon-config-value{{white-space:nowrap}}.weapon-combat-note{{min-width:180px;line-height:1.7}}.weapon-description{{min-width:280px;max-width:460px;line-height:1.7;font-size:13px;white-space:pre-line}}.attack-amount{{width:110px;color:var(--green);font:600 24px var(--display)}}.attack-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./", selected="attack")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Attack", "./index.html", recycling_count, attack_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">ATTACK POWER RANKING</span><h1>攻击力</h1><p>武器按照攻击力从高到低排列。</p></div><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="attack-table-wrap" tabindex="0"><table class="attack-table"><thead><tr><th>武器</th><th>攻击力</th><th>基础弹匣</th><th>整体换弹时间</th><th>使用弹药</th><th>攻击方式</th><th>高伤害配置点（倍率, 距离）</th><th>低伤害配置点（倍率, 距离）</th><th>最大距离</th><th>交战提醒</th><th>游戏内描述</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="attack-note">距离数据来自 11920 版基础配置；单位和衰减公式未验证，不代表实测伤害。弹匣与换弹时间不含配件效果；交战提醒为操作建议。</p><p class="attack-note">共 {len(items)} 件武器；没有可靠攻击力数据的武器排在最后。</p></section></div></main>{footer()}</body></html>'''


def healing_sort_key(entry: tuple[dict, str, dict]) -> tuple:
    """依次比较立即治疗、水分、饱食度；区间先比较上限，再比较下限。

    持续回血只确认了持续时间，不将秒数或效果强度当作回血量参与排序。
    最后按物品标识排序，确保各语言在数值相同时顺序一致。
    """
    _, slug, effect = entry
    return (-effect["healthChange"], -effect["thirstChangeMax"], -effect["thirstChangeMin"],
            -effect["hungerChangeMax"], -effect["hungerChangeMin"], slug)


def healing_page(categories: dict) -> str:
    effects = json.loads((STATIC / "game-stats.json").read_text(encoding="utf-8"))["consumable_effects"]
    items = sorted([(item, slug, effects[slug]) for group in categories.values() for item, slug in group
                    if slug in effects and effects[slug]["canConsume"]], key=healing_sort_key)

    def value_cell(low: float, high: float) -> str:
        value = f"{low:g}" if low == high else f"{low:g}–{high:g}"
        style = "restoration-negative" if low < 0 else ("restoration-positive" if high > 0 else "restoration-zero")
        return f'<td class="{style}">{esc(value)}</td>'

    rows = []
    for item, slug, effect in items:
        healing = value_cell(effect["healthChange"], effect["healthChange"])
        duration = f'持续恢复生命 {effect["buffDurationSeconds"]:g} 秒' if effect["buffName"] == "HealthRegenBuff" else "—"
        water = value_cell(effect["thirstChangeMin"], effect["thirstChangeMax"])
        food = value_cell(effect["hungerChangeMin"], effect["hungerChangeMax"])
        rows.append(f'<tr data-item="{esc(slug)}"><td><a class="recycle-item" href="./{esc(slug)}.html">{image_tag(item, "./", "recycle-image", item.get("name_zh"))}<span><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></span></a></td>{healing}<td>{esc(duration)}</td>{water}{food}</tr>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>治疗 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"></head><body>{header("./", selected="healing")}<main class="page-shell"><section class="healing-content"><div class="ranking-intro"><h1>治疗</h1><p>按立即治疗、水分、饱食度依次降序；区间先比上限，再比下限。</p></div><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="healing-table-wrap" tabindex="0"><table class="healing-table"><thead><tr><th>物品</th><th>立即治疗</th><th>持续治疗</th><th>水分恢复</th><th>饱食度恢复</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="healing-note">共 {len(items)} 件可使用物品。正值表示恢复，负值表示损失，0 表示没有对应的即时变化。</p><p class="healing-note">持续回血仅显示持续时间，未计入治疗排序。</p></section></main>{footer()}</body></html>'''


def threat_page_legacy(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int, threat_count: int) -> str:
    animals, npcs = threat_data()
    animal_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-amount">{"暂无数据" if item["damage"] is None else esc(item["damage"])}</td></tr>' for item in animals)
    npc_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-level">{esc(item["level"])}</td><td class="threat-amount">未确认</td></tr>' for item in npcs)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>威胁 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.threat-block{{margin-bottom:34px}}.threat-block h2{{margin:0 0 14px;font:600 28px var(--display)}}.threat-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.threat-table{{width:100%;border-collapse:collapse;text-align:left}}.threat-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.threat-table td{{padding:12px 16px;border-bottom:1px solid #edf0ed}}.threat-table tr:last-child td{{border-bottom:0}}.threat-table tr:hover td{{background:#fbfcfa}}.threat-table td b,.threat-table td small{{display:block}}.threat-table td b{{font-size:13px}}.threat-table td small{{margin-top:3px;color:var(--muted);font:10px var(--mono)}}.threat-amount{{width:180px;color:var(--green);font:600 22px var(--display)}}.threat-level{{width:180px;color:var(--green);font-weight:700}}.threat-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./", selected="threat")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Threat", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">THREAT DATABASE</span><h1>威胁</h1><p>野兽按基础攻击力从高到低；人机按已确认的难度等级排列。</p></div><div class="threat-block"><h2>野兽</h2><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="threat-table-wrap" tabindex="0"><table class="threat-table"><thead><tr><th>野兽</th><th>基础攻击力</th></tr></thead><tbody>{animal_rows}</tbody></table></div></div><div class="threat-block"><h2>人机</h2><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="threat-table-wrap" tabindex="0"><table class="threat-table"><thead><tr><th>人机</th><th>威胁等级</th><th>攻击力</th></tr></thead><tbody>{npc_rows}</tbody></table></div></div><p class="threat-note">共 {len(animals)} 种野兽、{len(npcs)} 类人机；人机的实际生命值和攻击力在当前导出数据中未可靠确认。</p></section></div></main>{footer()}</body></html>'''


def threat_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int, threat_count: int) -> str:
    animals, npcs = threat_data()
    animal_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-amount">{"未确认" if item["max_health"] is None else esc(item["max_health"])}<small>{esc(item.get("health_note", ""))}</small></td><td class="threat-amount">{"暂无数据" if item["damage"] is None else esc(item["damage"])}</td><td>{"—" if item["distance"] is None else esc(item["distance"])}</td><td>{"—" if item["speed"] is None else esc(item["speed"])}</td></tr>' for item in animals)
    npc_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-level">{esc(item["level"])}</td><td class="threat-amount">未确认</td></tr>' for item in npcs)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>威胁 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.threat-block{{margin-bottom:34px}}.threat-block h2{{margin:0 0 14px;font:600 28px var(--display)}}.threat-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.threat-table{{width:100%;border-collapse:collapse;text-align:left}}.threat-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.threat-table td{{padding:12px 16px;border-bottom:1px solid #edf0ed}}.threat-table tr:last-child td{{border-bottom:0}}.threat-table tr:hover td{{background:#fbfcfa}}.threat-table td b,.threat-table td small{{display:block}}.threat-table td b{{font-size:13px}}.threat-table td small{{margin-top:3px;color:var(--muted);font:10px var(--mono)}}.threat-amount{{width:130px;color:var(--green);font:600 22px var(--display)}}.threat-level{{width:180px;color:var(--green);font-weight:700}}.threat-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./", selected="threat")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Threat", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">THREAT DATABASE</span><h1>威胁</h1><p>野兽按基础攻击力从高到低；人机按已确认的难度等级排列。</p></div><div class="threat-block"><h2>野兽</h2><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="threat-table-wrap" tabindex="0"><table class="threat-table"><thead><tr><th>野兽</th><th>生命值</th><th>基础攻击力</th><th>攻击距离</th><th>攻击速度</th></tr></thead><tbody>{animal_rows}</tbody></table></div><p class="threat-note">生命值为满血时的基础值；服务器设置可能影响实际数值。</p></div><div class="threat-block"><h2>人机</h2><p class="table-scroll-hint">窄屏下可左右滑动表格，查看完整信息。</p><div class="threat-table-wrap" tabindex="0"><table class="threat-table"><thead><tr><th>人机</th><th>威胁等级</th><th>攻击力</th></tr></thead><tbody>{npc_rows}</tbody></table></div></div><p class="threat-note">共 {len(animals)} 种野兽、{len(npcs)} 类人机；缺失的野兽指标显示“—”，人机的实际生命值和攻击力在当前导出数据中未可靠确认。</p></section></div></main>{footer()}</body></html>'''


def inject_seo(page: Path, content: str, items_by_slug: dict[str, dict]) -> str:
    """将统一 SEO 头注入已经生成的每个 HTML 页面。"""
    if page.name == "index.html":
        title = "氧化物生存岛爱好者论坛"
        description = "氧化物生存岛物品图鉴，查询武器、护甲、工具、弹药、建筑和材料的制作配方与获取方式。"
        keywords = None
    elif page.name == "about.html":
        title = "关于 · 氧化物生存岛百科全书"
        description = "了解氧化物生存岛百科全书的内容、目标与玩家社区定位。"
        keywords = ["氧化物生存岛百科全书", "氧化物生存岛攻略", "氧化物生存岛玩家资料"]
    elif page.name == "items.html":
        title = f"物品百科 · {configured_site_name()}"
        description = "浏览氧化物生存岛中的建筑、工具、武器、弹药、医疗、护甲、材料和其他物品。"
        keywords = ["氧化物生存岛物品", "氧化物生存岛物品百科", "制作配方", "武器", "护甲", "材料"]
    elif page.name == "recycling.html":
        title = f"回收表 · {configured_site_name()}"
        description = "查看氧化物生存岛物品回收产物，按废料、高品质金属、金属碎片、木材和石头数量排序。"
        keywords = ["氧化物生存岛回收表", "氧化物生存岛回收产物", "废料", "高品质金属", "金属碎片", "木材", "石头"]
    elif page.name == "attack.html":
        title = f"攻击力排行 · {configured_site_name()}"
        description = "查看氧化物生存岛武器攻击力排行和各武器详情。"
        keywords = ["氧化物生存岛攻击力排行", "氧化物生存岛武器伤害", "武器攻击力"]
    elif page.name == "healing.html":
        title = f"治疗 · {configured_site_name()}"
        description = "比较物品的治疗、水分和饱食度恢复值。"
        keywords = ["氧化物生存岛治疗", "生命恢复", "补水", "饱食度"]
    elif page.name == "defense.html":
        title = f"防御力排行 · {configured_site_name()}"
        description = "查看氧化物生存岛护甲的射击、近战和寒冷防护属性排行。"
        keywords = ["氧化物生存岛防御力排行", "氧化物生存岛护甲", "射击防护", "近战防护", "寒冷防护"]
    elif page.name == "threat.html":
        title = f"威胁信息 · {configured_site_name()}"
        description = "查看氧化物生存岛野兽和人机的威胁信息、基础攻击力、攻击距离和攻击速度。"
        keywords = ["氧化物生存岛野兽", "氧化物生存岛人机", "氧化物生存岛威胁", "野兽攻击力"]
    else:
        item = items_by_slug.get(page.stem)
        if not item:
            return content
        item_name = str(item.get("name_zh") or item.get("name_en") or "物品")
        title = f"{item_name} · {configured_site_name()}"
        description = f"查询氧化物生存岛{item_name}的英文名、制作配方、材料、获取方式和回收产物。"
        keywords = [item_name, str(item.get("name_en") or ""), f"氧化物生存岛{item_name}", f"{item_name}制作配方", f"{item_name}获取方式", f"{item_name}回收"]
    head = seo_head(title, description, page.name, keywords)
    return re.sub(r'<head>.*?<link rel="stylesheet"', f'<head>{head}<link rel="stylesheet"', content, count=1, flags=re.DOTALL)


def write_crawl_files(pages: list[Path]) -> None:
    """生成搜索引擎使用的站点地图和抓取规则。"""
    site_url = str(site_config().get("site_url") or "").rstrip("/")
    urls = "\n".join(
        f"  <url><loc>{html.escape(site_url + '/' + page.relative_to(HTML_DIR).as_posix())}</loc></url>"
        for page in sorted(pages, key=lambda path: path.relative_to(HTML_DIR).as_posix())
    )
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
'''
    (HTML_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (HTML_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n",
        encoding="utf-8",
    )


def main() -> None:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    categories: dict[str, list[tuple[dict, str]]] = {}
    lookup: dict[tuple[str | None, str | None], tuple[dict, str]] = {}
    used_slugs: set[str] = set()
    index = 0
    for source_category, items in config.items():
        category = display_category(source_category)
        categories.setdefault(category, [])
        for item in items:
            if not item.get("image"):
                continue
            slug = slug_for(item, index)
            original_slug = slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{original_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)
            categories[category].append((item, slug))
            lookup[(item.get("name_en"), item.get("name_zh"))] = (item, slug)
            index += 1

    categories = {category: categories[category] for category in DISPLAY_CATEGORY_ORDER if category in categories}
    recycling_count = recycling_item_count(categories)
    attack_count = attack_item_count(categories)
    threat_count = threat_item_count()

    HTML_DIR.mkdir(exist_ok=True)
    for old_page in HTML_DIR.glob("*.html"):
        old_page.unlink()
    for category, items in categories.items():
        for item, slug in items:
            (HTML_DIR / f"{slug}.html").write_text(detail_page(item, category, slug, categories, lookup, "./", recycling_count, attack_count, threat_count), encoding="utf-8")
    (HTML_DIR / "index.html").write_text(add_pc_download(index_page()), encoding="utf-8")
    (HTML_DIR / "items.html").write_text(add_items_search(items_page(categories)), encoding="utf-8")
    (HTML_DIR / "play.html").write_text(play_page(), encoding="utf-8")
    (HTML_DIR / "about.html").write_text(about_page(), encoding="utf-8")
    (HTML_DIR / "recycling.html").write_text(recycling_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "attack.html").write_text(attack_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "defense.html").write_text(defense_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    (HTML_DIR / "healing.html").write_text(healing_page(categories), encoding="utf-8")
    (HTML_DIR / "threat.html").write_text(threat_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    items_by_slug = {slug: item for items in categories.values() for item, slug in items}
    for page in HTML_DIR.glob("*.html"):
        content = clean_page_branding(page.read_text(encoding="utf-8"))
        page.write_text(inject_seo(page, content, items_by_slug), encoding="utf-8")
    gameplay_count = write_gameplay_pages()
    crawl_pages = list(HTML_DIR.glob("*.html")) + list((HTML_DIR / "gameplay").glob("*.html"))
    from build_i18n import build_localized_pages
    localized_pages = build_localized_pages(sorted(crawl_pages))
    write_crawl_files(localized_pages)
    print(f"generated {index} item pages, 1 promotional page, 1 items page, 1 recycling page, 1 attack page, 1 defense page, 1 healing page, 1 threat page and {gameplay_count} gameplay pages")


if __name__ == "__main__":
    main()
