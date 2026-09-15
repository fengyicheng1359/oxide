"""从本地 output 导出文件更新站点数值快照；不执行网络请求。"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_static import ROOT, CONFIG_FILE, ARMOR_CATEGORIES, THREAT_NPCS, display_category

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

if __name__ == '__main__':
    if not (ROOT.parent / 'output/animal').is_dir():
        raise SystemExit('缺少本地 output 数据，不能更新快照。')
    config = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    armor = {Path(item['image']).stem: armor_protection(item)
             for category, items in config.items() if display_category(category) == 'Armor'
             for item in items if item.get('image')}
    animals, npcs = threat_data()
    (ROOT / 'static/game-stats.json').write_text(json.dumps(
        {'armor': armor, 'animals': animals, 'npcs': npcs}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
