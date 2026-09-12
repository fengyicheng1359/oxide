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
    return f'''<header class="site-header"><div class="header-inner">
      <a class="brand" href="{index_href}"><span class="brand-mark">O</span><span><strong>OXIDE</strong><small>ITEM DATABASE</small></span></a>
      <nav><a class="active" href="{index_href}#items">物品</a><a href="{index_href}#categories">分类</a><a href="{prefix}recycling.html">回收</a><a href="{prefix}attack.html">攻击力</a><a href="{prefix}defense.html">防御力</a><a href="{prefix}threat.html">威胁</a><a href="#about">关于</a></nav>
      <div class="header-tools"><span>中 / EN</span><span class="online"><i></i> STATIC DATA</span></div>
    </div></header>'''


def footer() -> str:
    return '<footer class="site-footer"><span>OXIDE / SURVIVAL FIELD NOTES</span><span>STATIC HTML · GENERATED FROM CONFIG.JSON</span></footer>'


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
    card_class = "item-card" if facts else "item-card single"
    attack_style = ".attack-fact{flex-direction:row;align-items:baseline;gap:14px}.attack-fact small{margin-left:auto}" if category in {"Weapon", "Armor"} else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{esc(item.get("name_zh"))} · Oxide Wiki</title><link rel="stylesheet" href="{prefix}styles.css"><style>.item-card.single{{grid-template-columns:1fr}}{attack_style}.acquisition-list{{display:grid;gap:8px}}.acquisition-row{{display:flex;align-items:center;gap:14px;padding:14px;background:#fff;border:1px solid #dfe3df;border-radius:7px}}.acquisition-row b{{min-width:72px;color:#526f3c;font-size:12px}}.acquisition-row span{{color:#78807c;font-size:12px}}.protection-list{{display:grid;gap:8px;grid-template-columns:repeat(3,1fr)}}.protection-row{{display:flex;align-items:center;justify-content:space-between;padding:14px;background:#fff;border:1px solid #dfe3df;border-radius:7px}}.protection-row span{{color:#78807c;font-size:12px}}.protection-row strong{{color:#526f3c;font:600 24px var(--display)}}</style></head><body>
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


def index_page(categories: dict[str, list[tuple[dict, str]]]) -> str:
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
    (HTML_DIR / "index.html").write_text(index_page(categories), encoding="utf-8")
    (HTML_DIR / "recycling.html").write_text(recycling_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "attack.html").write_text(attack_page(categories, recycling_count, attack_count), encoding="utf-8")
    (HTML_DIR / "defense.html").write_text(defense_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    (HTML_DIR / "threat.html").write_text(threat_page(categories, recycling_count, attack_count, threat_count), encoding="utf-8")
    print(f"generated {index} item pages, 1 catalog page, 1 recycling page, 1 attack page, 1 defense page and 1 threat page")


if __name__ == "__main__":
    main()
