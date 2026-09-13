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
    """生成每个静态页面共用的 SEO 标签和可选的 Google Analytics。"""
    config = site_config()
    site_name = configured_site_name()
    site_url = str(config.get("site_url") or "").rstrip("/")
    canonical = f"{site_url}/{page_path.lstrip('/')}" if site_url else ""
    keyword_values = keywords or config.get("default_keywords", [])
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
    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": site_url,
        "inLanguage": "zh-CN",
    }, ensure_ascii=False).replace("</", "<\\/")
    return f'''<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keyword_text)}"><meta name="robots" content="index,follow"><meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:site_name" content="{esc(site_name)}">{canonical_tag}{favicon_tag}<script type="application/ld+json">{structured_data}</script>{analytics}'''


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


def header(prefix: str, index_href: str | None = None) -> str:
    index_href = index_href or f"{prefix}index.html"
    items_href = f"{prefix}items.html"
    return f'''<header class="site-header"><div class="header-inner">
      <a class="brand" href="{index_href}"><img class="brand-mark" src="{prefix}static/assets/OSAAS.jpeg" alt="氧化物生存岛百科全书"><span><strong>氧化物生存岛</strong><small>百科全书</small></span></a>
      <nav><a class="active" href="{items_href}">物品</a><a href="{prefix}recycling.html">回收</a><a href="{prefix}attack.html">攻击力</a><a href="{prefix}defense.html">防御力</a><a href="{prefix}threat.html">威胁</a><a href="{prefix}about.html">关于</a></nav>
      <div class="header-tools"><span>中 / EN</span><span class="online"><i></i> STATIC DATA</span></div>
    </div></header>'''


def footer() -> str:
    return '<footer class="site-footer"><span>氧化物生存岛爱好者论坛</span><span>STATIC HTML · GENERATED FROM CONFIG.JSON</span></footer>'


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
        facts = f'<div class="facts"><div class="fact attack-fact"><span>攻击力</span><strong>{attack_text}</strong><small>ATTACK POWER</small></div></div>'
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
      {header(prefix, "./index.html")}<main class="page-shell"><div class="breadcrumb"><a href="./index.html">首页</a><span>/</span><a href="./index.html#category-{esc(category)}">{esc(category_name(category))}</a><span>/</span>{esc(item.get("name_zh"))}</div>
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
    image = item.get("image") or ""
    stem = Path(image).stem
    for category in ARMOR_CATEGORIES:
        path = ROOT.parent / "output" / category / f"{stem}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        objects = data.get("related_configs", {}).get("protection", {}).get("objects", [])
        amounts = [value for obj in objects for value in obj.get("data", {}).get("amounts", [])]
        if amounts:
            return amounts
    return None


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
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>防御力 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.attack-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.attack-table{{width:100%;border-collapse:collapse;text-align:left}}.attack-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.attack-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.attack-table tr:last-child td{{border-bottom:0}}.attack-table tr:hover td{{background:#fbfcfa}}.attack-table .recycle-image{{width:50px;height:50px}}.attack-amount{{width:120px;color:var(--green);font:600 22px var(--display)}}.attack-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Defense", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">DEFENSE RANKING</span><h1>防御力</h1><p>按照游戏界面的防护属性展示。</p></div><div class="attack-table-wrap"><table class="attack-table"><thead><tr><th>护甲</th><th>射击</th><th>近战</th><th>寒冷</th></tr></thead><tbody>{rows}</tbody></table></div><p class="attack-note">共 {len(items)} 件护甲；展示游戏界面中的射击、近战、寒冷防护百分比。</p></section></div></main>{footer()}</body></html>'''


def threat_data() -> tuple[list[dict], list[dict]]:
    animals = []
    for path in sorted((ROOT.parent / "output" / "animal").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        damage_entries = data.get("damage", [])
        damage = [entry.get("base_damage") for entry in damage_entries if entry.get("base_damage") is not None]
        distances = [entry.get("min_attack_distance") for entry in damage_entries if entry.get("min_attack_distance") is not None]
        speeds = [entry.get("attack_speed") for entry in damage_entries if entry.get("attack_speed") is not None]
        states = sorted({state.get("state_name") for state in data.get("behavior_states", []) if state.get("state_name")})
        animals.append({"name_zh": data.get("name_zh") or path.stem, "name_en": data.get("name_en") or path.stem, "damage": max(damage) if damage else None, "distance": min(distances) if distances else None, "speed": min(speeds) if speeds else None, "states": states})
    animals.sort(key=lambda item: (item["damage"] is None, -(item["damage"] or 0), item["name_zh"]))
    npcs = [{"name_zh": zh, "name_en": en, "level": level} for zh, en, level in THREAT_NPCS]
    level_rank = {"困难": 0, "中等": 1, "简单": 2, "新手": 3, "未确认": 4}
    npcs.sort(key=lambda item: (level_rank[item["level"]], item["name_zh"]))
    return animals, npcs


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
            cards.append(f'<a class="catalog-card" href="./{esc(slug)}.html">{image_tag(item, "./", "catalog-image", item.get("name_zh"))}<span class="catalog-copy"><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small></span></a>')
        cards.append('</div></section>')
    recycling_count = recycling_item_count(categories)
    attack_count = attack_item_count(categories)
    threat_count = threat_item_count()
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Oxide Wiki · Items</title><link rel="stylesheet" href="./styles.css"></head><body>{header("./")}<main class="page-shell"><div class="search-row"><div><span class="eyebrow">OXIDE WIKI</span><h1>游戏物品数据库</h1><p>浏览物品、制造配方与生存资源。</p></div><div class="search">⌕ <span>搜索物品...</span></div></div><div class="catalog-layout">{sidebar(categories, "./", recycling_count=recycling_count, attack_count=attack_count, threat_count=threat_count)}<section id="items" class="catalog-content">{"".join(cards)}</section></div></main>{footer()}</body></html>'''


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
    card = '''<a class="download-card" href="https://www.bluestacks.com/apps/action/oxide-survival-island-on-pc.html" target="_blank" rel="noopener"><span><b>Windows / BlueStacks</b><small>下载电脑版</small></span><span class="arrow">↗</span></a>'''
    marker = '</a></section><footer class="promo-footer">'
    return page.replace(marker, '</a>' + card + '</section><footer class="promo-footer">', 1)


def index_page() -> str:
    gallery = "".join(
        f'<figure class="promo-shot"><img src="./static/loop-imge/loop-{index:02d}.jpg" alt="氧化物：生存岛游戏截图 {index}"></figure>'
        for index in range(1, 17)
    )
    promo_header = header("./").replace(' class="active" href="./items.html"', ' href="./items.html"')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>氧化物生存岛爱好者论坛</title><meta name="description" content="氧化物：生存岛官方游戏介绍、宣传视频、游戏截图以及 Android 和 Apple 下载入口。"><link rel="stylesheet" href="./styles.css"><style>
    .promo-page{{background:#111713;color:#f4f5ef;overflow:hidden}}.promo-page .site-header{{background:#111713;border-color:#2c352e}}.promo-page .brand strong{{color:#f4f5ef}}.promo-page .header-inner nav a{{color:#a9b5aa}}.promo-page .header-tools{{color:#879389}}.promo-shell{{max-width:1240px;margin:auto;padding:30px 28px 76px}}.hero{{position:relative;min-height:620px;display:flex;align-items:end;overflow:hidden;border:1px solid #38453a;border-radius:18px;background:#243128;box-shadow:0 25px 70px #0008}}.hero video{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.65}}.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#0d120fef 0%,#0d120f99 44%,#0d120f12 78%),linear-gradient(0deg,#0d120fdb,#0d120f00 58%)}}.hero-copy{{position:relative;z-index:1;max-width:720px;padding:54px}}.hero-kicker{{color:#b3d391;font:11px var(--mono);letter-spacing:.18em}}.hero h1{{margin:16px 0 14px;font:600 clamp(46px,7vw,92px)/.92 var(--display);letter-spacing:-.04em}}.hero p{{max-width:580px;margin:0;color:#c7d0c5;font-size:17px;line-height:1.75}}.hero-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}}.hero-actions a,.download-card{{display:inline-flex;align-items:center;gap:10px;padding:13px 17px;border:1px solid #b3d391;border-radius:7px;color:#162016;background:#b3d391;font-weight:700}}.hero-actions a.secondary{{color:#e3eade;background:#1b261d;border-color:#566656}}.section-intro{{display:flex;align-items:end;justify-content:space-between;gap:24px;margin:72px 0 22px}}.section-intro h2{{margin:8px 0 0;font:600 44px/.95 var(--display)}}.section-intro p{{max-width:430px;margin:0;color:#9daa9e;line-height:1.7}}.eyebrow{{color:#98aa9a;font:11px var(--mono);letter-spacing:.16em}}.promo-window{{position:relative;overflow:hidden;padding:8px 0 22px}}.promo-track{{display:flex;width:max-content;gap:18px;animation:promo-scroll 72s linear infinite}}.promo-shot{{width:350px;height:198px;flex:none;margin:0;overflow:hidden;border:1px solid #3a493d;border-radius:10px;background:#202b22;box-shadow:0 12px 32px #0005}}.promo-shot img{{width:100%;height:100%;object-fit:cover;display:block;transition:transform .45s ease}}.promo-shot:hover img{{transform:scale(1.04)}}@keyframes promo-scroll{{from{{transform:translateX(0)}}to{{transform:translateX(calc(-50% - 9px))}}}}.promo-window:hover .promo-track{{animation-play-state:paused}}.download-panel{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:34px}}.download-card{{display:flex;justify-content:space-between;background:#1b261d;border-color:#3d503f;color:#e7eee4;text-decoration:none}}.download-card small{{display:block;margin-top:5px;color:#98aa9a;font:10px var(--mono)}}.download-card .arrow{{color:#b3d391;font-size:24px}}.promo-footer{{display:flex;justify-content:space-between;gap:20px;margin-top:76px;padding-top:24px;border-top:1px solid #303c32;color:#91a092;font:10px var(--mono);letter-spacing:.08em}}.promo-footer a{{color:#b3d391}}@media(max-width:760px){{.promo-shell{{padding:18px 16px 52px}}.hero{{min-height:600px}}.hero-copy{{padding:30px 24px}}.hero p{{font-size:15px}}.section-intro{{display:block;margin-top:50px}}.section-intro p{{margin-top:14px}}.promo-shot{{width:280px;height:158px}}.download-panel{{grid-template-columns:1fr}}.promo-footer{{display:block;line-height:2.2}}}}
    </style></head><body class="promo-page">{promo_header}<main class="promo-shell"><section class="hero"><video autoplay muted loop playsinline poster="./static/loop-imge/loop-01.jpg"><source src="./static/loop-imge/trailer.mp4" type="video/mp4"></video><div class="hero-copy"><span class="hero-kicker">OXIDE · SURVIVAL ISLAND</span><h1>氧化物：生存岛</h1><p>在残酷的开放世界中收集资源、制作装备、建造基地，与朋友并肩生存，征服属于你的岛屿。</p><div class="hero-actions"><a href="./items.html">浏览物品百科 <span>↗</span></a><a class="secondary" href="https://hyper-hug.com/" target="_blank" rel="noopener">访问官方网站 <span>↗</span></a></div></div></section><section class="section-intro"><div><span class="eyebrow">FROM THE ISLAND</span><h2>游戏现场</h2></div><p>官方页面中的游戏截图，展示荒岛求生、资源采集、基地建造与战斗场景。</p></section><section class="promo-window" aria-label="游戏截图轮播"><div class="promo-track">{gallery}{gallery}</div></section><section class="section-intro"><div><span class="eyebrow">JOIN THE SURVIVAL</span><h2>开始生存</h2></div><p>选择你的平台，下载《氧化物：生存岛》，进入多人在线生存世界。</p></section><section class="download-panel"><a class="download-card" href="https://play.google.com/store/apps/details?id=com.catsbit.oxidesurvivalisland&hl=zh" target="_blank" rel="noopener"><span><b>Android / Google Play</b><small>下载安卓版</small></span><span class="arrow">↗</span></a><a class="download-card" href="https://apps.apple.com/sg/app/%E6%B0%A7%E5%8C%96%E7%89%A9-%E7%94%9F%E5%AD%98%E5%B2%9B-%E7%94%9F%E5%AD%98-%E5%88%B6%E4%BD%9C-%E5%BE%81%E6%9C%8D/id1579424683?l=zh-Hans-CN" target="_blank" rel="noopener"><span><b>iPhone / App Store</b><small>下载苹果版</small></span><span class="arrow">↗</span></a></section><footer class="promo-footer"><span>氧化物生存岛爱好者论坛 · STATIC PAGE</span><span><a href="https://hyper-hug.com/" target="_blank" rel="noopener">官方网站</a> · HYPERHUG</span></footer></main></body></html>'''


def about_page() -> str:
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>关于 · 氧化物生存岛百科全书</title><link rel="stylesheet" href="./styles.css"><style>
    .about-shell{max-width:960px;margin:auto;padding:70px 28px 100px}.about-hero{padding:56px 0 62px;border-bottom:1px solid var(--line)}.about-kicker{color:var(--green);font:11px var(--mono);letter-spacing:.16em}.about-hero h1{max-width:760px;margin:18px 0 22px;font:600 clamp(42px,7vw,84px)/.94 var(--display);letter-spacing:-.04em}.about-hero p{max-width:700px;margin:0;color:var(--muted);font-size:18px;line-height:1.9}.about-quote{margin:48px 0;padding:28px 32px;border-left:4px solid var(--green);background:var(--light);font:600 clamp(24px,4vw,42px)/1.35 var(--display)}.about-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:34px}.about-card{padding:24px;background:#fff;border:1px solid var(--line);border-radius:8px}.about-card strong{display:block;margin-bottom:10px;font:600 24px var(--display)}.about-card p{margin:0;color:var(--muted);font-size:13px;line-height:1.8}.about-note{margin-top:42px;color:var(--muted);font-size:13px;line-height:1.9}@media(max-width:760px){.about-shell{padding:42px 18px 70px}.about-hero{padding-top:28px}.about-hero p{font-size:16px}.about-quote{padding:22px 20px;margin:34px 0}.about-grid{grid-template-columns:1fr}}
    </style></head><body><header class="site-header"><div class="header-inner"><a class="brand" href="./index.html"><img class="brand-mark" src="./static/assets/OSAAS.jpeg" alt="氧化物生存岛百科全书"><span><strong>氧化物生存岛</strong><small>百科全书</small></span></a><nav><a href="./items.html#items">物品</a><a href="./recycling.html">回收</a><a href="./attack.html">攻击力</a><a href="./defense.html">防御力</a><a href="./threat.html">威胁</a><a class="active" href="./about.html">关于</a></nav><div class="header-tools"><span>中 / EN</span><span class="online"><i></i> STATIC DATA</span></div></div></header><main class="about-shell"><section class="about-hero"><span class="about-kicker">WELCOME TO THE ISLAND</span><h1>每一次出发，<br>都值得被记住。</h1><p>这里是氧化物生存岛百科全书。我们把岛上的物品、武器、护甲、材料和生存线索，整理成一张清晰的地图，让每一个刚踏上荒岛的孩子，都能找到属于自己的第一步。</p></section><blockquote class="about-quote">你不只是寻找答案，<br>你正在学会创造自己的生存故事。</blockquote><section class="about-grid"><article class="about-card"><strong>探索</strong><p>从一棵树、一块石头开始，认识岛上的每一种资源，发现未知角落里的惊喜。</p></article><article class="about-card"><strong>创造</strong><p>查找配方，制作工具和装备，把自己的想法变成真正可以使用的东西。</p></article><article class="about-card"><strong>并肩</strong><p>和朋友分享发现、交换经验，在一次次合作中，让普通的冒险变成难忘的回忆。</p></article></section><p class="about-note">这个站点是玩家整理的静态资料站，内容用于帮助大家更快了解游戏。真正精彩的部分，永远发生在你亲自踏上岛屿、做出选择、解决困难的那一刻。愿你带着好奇心出发，也带着属于自己的故事回来。</p></main><footer class="site-footer"><span>氧化物生存岛爱好者论坛</span><span>STATIC HTML · ABOUT</span></footer></body></html>'''


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
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>回收 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.recycling-intro{{margin-bottom:24px}}.recycling-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.recycling-intro p{{margin:0;color:var(--muted);font-size:13px}}.recycle-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.recycle-table{{width:100%;min-width:760px;border-collapse:collapse;text-align:left}}.recycle-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.recycle-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.recycle-table tr:last-child td{{border-bottom:0}}.recycle-table tr:hover td{{background:#fbfcfa}}.recycle-item{{display:flex;align-items:center;gap:12px;min-width:220px}}.recycle-image{{width:42px;height:42px;object-fit:contain}}.recycle-item b,.recycle-item small{{display:block}}.recycle-item b{{font-size:12px}}.recycle-item small{{margin-top:3px;color:var(--muted);font:9px var(--mono)}}.recycle-amount{{width:120px;color:var(--green);font:600 19px var(--display)}}.recycle-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Recycling", "./index.html", recycling_count, attack_count)}<section class="catalog-content"><div class="recycling-intro"><span class="eyebrow">RECYCLE DATABASE</span><h1>回收</h1><p>按单个物品可回收产物数量排序，数量相同则继续比较下一种材料。</p></div><div class="recycle-table-wrap"><table class="recycle-table"><thead><tr><th>物品</th>{headers}</tr></thead><tbody>{"".join(body)}</tbody></table></div><p class="recycle-note">共 {len(rows)} 件物品有已解析的回收产物；“—”表示该物品不产出此类材料。</p></section></div></main>{footer()}</body></html>'''


def attack_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int) -> str:
    items = sorted(categories.get("Weapon", []), key=lambda pair: (pair[0].get("attack_power") is None, -(pair[0].get("attack_power") or 0), pair[0].get("name_zh") or ""))
    rows = []
    for item, slug in items:
        attack = item.get("attack_power")
        value = "暂无数据" if attack is None else esc(attack)
        rows.append(f'<tr><td><a class="recycle-item" href="./{esc(slug)}.html">{image_tag(item, "./", "recycle-image", item.get("name_zh"))}<span><b>{esc(item.get("name_zh"))}</b><small>{esc(item.get("name_en"))}</small></span></a></td><td class="attack-amount">{value}</td></tr>')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>攻击力 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.attack-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.attack-table{{width:100%;border-collapse:collapse;text-align:left}}.attack-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.attack-table td{{padding:10px 16px;border-bottom:1px solid #edf0ed}}.attack-table tr:last-child td{{border-bottom:0}}.attack-table tr:hover td{{background:#fbfcfa}}.attack-table .recycle-image{{width:50px;height:50px}}.attack-amount{{width:180px;color:var(--green);font:600 24px var(--display)}}.attack-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Attack", "./index.html", recycling_count, attack_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">ATTACK POWER RANKING</span><h1>攻击力</h1><p>武器按照攻击力从高到低排列。</p></div><div class="attack-table-wrap"><table class="attack-table"><thead><tr><th>武器</th><th>攻击力</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="attack-note">共 {len(items)} 件武器；没有可靠攻击力数据的武器排在最后。</p></section></div></main>{footer()}</body></html>'''


def threat_page_legacy(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int, threat_count: int) -> str:
    animals, npcs = threat_data()
    animal_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-amount">{"暂无数据" if item["damage"] is None else esc(item["damage"])}</td></tr>' for item in animals)
    npc_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-level">{esc(item["level"])}</td><td class="threat-amount">未确认</td></tr>' for item in npcs)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>威胁 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.threat-block{{margin-bottom:34px}}.threat-block h2{{margin:0 0 14px;font:600 28px var(--display)}}.threat-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.threat-table{{width:100%;border-collapse:collapse;text-align:left}}.threat-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.threat-table td{{padding:12px 16px;border-bottom:1px solid #edf0ed}}.threat-table tr:last-child td{{border-bottom:0}}.threat-table tr:hover td{{background:#fbfcfa}}.threat-table td b,.threat-table td small{{display:block}}.threat-table td b{{font-size:13px}}.threat-table td small{{margin-top:3px;color:var(--muted);font:10px var(--mono)}}.threat-amount{{width:180px;color:var(--green);font:600 22px var(--display)}}.threat-level{{width:180px;color:var(--green);font-weight:700}}.threat-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Threat", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">THREAT DATABASE</span><h1>威胁</h1><p>野兽按基础攻击力从高到低；人机按已确认的难度等级排列。</p></div><div class="threat-block"><h2>野兽</h2><div class="threat-table-wrap"><table class="threat-table"><thead><tr><th>野兽</th><th>基础攻击力</th></tr></thead><tbody>{animal_rows}</tbody></table></div></div><div class="threat-block"><h2>人机</h2><div class="threat-table-wrap"><table class="threat-table"><thead><tr><th>人机</th><th>威胁等级</th><th>攻击力</th></tr></thead><tbody>{npc_rows}</tbody></table></div></div><p class="threat-note">共 {len(animals)} 种野兽、{len(npcs)} 类人机；人机的实际生命值和攻击力在当前导出数据中未可靠确认。</p></section></div></main>{footer()}</body></html>'''


def threat_page(categories: dict[str, list[tuple[dict, str]]], recycling_count: int, attack_count: int, threat_count: int) -> str:
    animals, npcs = threat_data()
    animal_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-amount">{"暂无数据" if item["damage"] is None else esc(item["damage"])}</td><td>{"—" if item["distance"] is None else esc(item["distance"])}</td><td>{"—" if item["speed"] is None else esc(item["speed"])}</td></tr>' for item in animals)
    npc_rows = "".join(f'<tr><td><b>{esc(item["name_zh"])}</b><small>{esc(item["name_en"])}</small></td><td class="threat-level">{esc(item["level"])}</td><td class="threat-amount">未确认</td></tr>' for item in npcs)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>威胁 · Oxide Wiki</title><link rel="stylesheet" href="./styles.css"><style>.ranking-intro{{margin-bottom:24px}}.ranking-intro h1{{margin:8px 0 5px;font:600 48px/1 var(--display)}}.ranking-intro p{{margin:0;color:var(--muted);font-size:13px}}.threat-block{{margin-bottom:34px}}.threat-block h2{{margin:0 0 14px;font:600 28px var(--display)}}.threat-table-wrap{{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:8px}}.threat-table{{width:100%;border-collapse:collapse;text-align:left}}.threat-table th{{padding:14px 16px;color:var(--muted);background:#f5f7f4;font:10px var(--mono);letter-spacing:.08em;border-bottom:1px solid var(--line)}}.threat-table td{{padding:12px 16px;border-bottom:1px solid #edf0ed}}.threat-table tr:last-child td{{border-bottom:0}}.threat-table tr:hover td{{background:#fbfcfa}}.threat-table td b,.threat-table td small{{display:block}}.threat-table td b{{font-size:13px}}.threat-table td small{{margin-top:3px;color:var(--muted);font:10px var(--mono)}}.threat-amount{{width:130px;color:var(--green);font:600 22px var(--display)}}.threat-level{{width:180px;color:var(--green);font-weight:700}}.threat-note{{margin-top:13px;color:var(--muted);font-size:11px}}</style></head><body>{header("./")}<main class="page-shell"><div class="catalog-layout">{sidebar(categories, "./", "Threat", "./index.html", recycling_count, attack_count, threat_count)}<section class="catalog-content"><div class="ranking-intro"><span class="eyebrow">THREAT DATABASE</span><h1>威胁</h1><p>野兽按基础攻击力从高到低；人机按已确认的难度等级排列。</p></div><div class="threat-block"><h2>野兽</h2><div class="threat-table-wrap"><table class="threat-table"><thead><tr><th>野兽</th><th>基础攻击力</th><th>攻击距离</th><th>攻击速度</th></tr></thead><tbody>{animal_rows}</tbody></table></div></div><div class="threat-block"><h2>人机</h2><div class="threat-table-wrap"><table class="threat-table"><thead><tr><th>人机</th><th>威胁等级</th><th>攻击力</th></tr></thead><tbody>{npc_rows}</tbody></table></div></div><p class="threat-note">共 {len(animals)} 种野兽、{len(npcs)} 类人机；缺失的野兽指标显示“—”，人机的实际生命值和攻击力在当前导出数据中未可靠确认。</p></section></div></main>{footer()}</body></html>'''


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
        f"  <url><loc>{html.escape(site_url + '/' + page.name)}</loc></url>"
        for page in sorted(pages, key=lambda path: path.name)
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
    (HTML_DIR / "about.html").write_text(about_page(), encoding="utf-8")
    (HTML_DIR / "recycling.html").write_text(recycling_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "attack.html").write_text(attack_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "defense.html").write_text(defense_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    (HTML_DIR / "threat.html").write_text(threat_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    items_by_slug = {slug: item for items in categories.values() for item, slug in items}
    for page in HTML_DIR.glob("*.html"):
        content = clean_page_branding(page.read_text(encoding="utf-8"))
        page.write_text(inject_seo(page, content, items_by_slug), encoding="utf-8")
    write_crawl_files(sorted(HTML_DIR.glob("*.html")))
    print(f"generated {index} item pages, 1 promotional page, 1 items page, 1 recycling page, 1 attack page, 1 defense page and 1 threat page")


if __name__ == "__main__":
    main()
