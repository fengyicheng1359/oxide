"""将 1.14.11949 已确认的新增物品写入网站共用数据。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "dist/static"
ANALYSIS = ROOT / "apk-analysis-1012/新增物品数据.json"
SNAPSHOT = STATIC / "apk-11949-new-items.json"
ENGLISH_NAMES = {"knight.shield": "Knight Shield"}
MATERIAL_NAMES = {
    "gun.powder": ("火药", "Gun Powder"),
    "metal.fragment": ("金属碎片", "Metal Fragment"),
    "metal.spring": ("金属弹簧", "Metal Spring"),
    "hq.metal": ("高品质金属", "High Quality Metal"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def material(row):
    zh, en = MATERIAL_NAMES[row["item_id"]]
    return {"name_zh": zh, "name_en": en, "amount": row["amount"]}


def main():
    analysis = read(ANALYSIS if ANALYSIS.exists() else SNAPSHOT)
    assert analysis["old_version"] == "1.13.11920" and analysis["new_version"] == "1.14.11949"
    assert len(analysis["items"]) == 6 and not analysis["removed_item_ids"]
    config_path = STATIC / "config.json"
    config = read(config_path)
    old_count = sum(map(len, config.values()))
    assert old_count in (259, 265), old_count
    recipes_path = STATIC / "crafting-recipes.json"
    recipes = read(recipes_path)
    assert recipes["version"] in ("1.13.11920", "1.14.11949")
    by_image = {Path(row["image"]).stem: row for items in config.values() for row in items if row.get("image")}

    for source in analysis["items"]:
        item_id = source["item_id"]
        image = f"assets/image/{item_id}.png" if (STATIC / "assets/image" / (item_id + ".png")).exists() else None
        name_zh = source["name_zh_explanatory"].removesuffix("（暂译）")
        name_en = source["name_en_raw"] or ENGLISH_NAMES[item_id]
        row = {
            "name_en": name_en, "name_zh": name_zh, "attack_power": None,
            "crafting_materials": [material(x) for x in (source["craft_inputs"] or [])],
            "image": image, "acquisition_methods": [], "recycling_sources": [],
            "recycling_outputs": [
                {**material(x), "item_id": x["item_id"], "skip_chance": x["skip_chance_raw"]}
                for x in (source["recycle_outputs"] or [])
            ],
            "crafting_output_per_batch": source["craft_count"],
        }
        # 没有图标的结构条目保留在原始分类中；现有站点只为有图物品生成详情页。
        existing = by_image.get(item_id)
        if existing is None and image is None:
            matches = [x for x in config[source["category"]] if x["name_zh"] == name_zh]
            assert len(matches) <= 1, item_id
            existing = matches[0] if matches else None
        if existing:
            assert existing == row, item_id
        else:
            config[source["category"]].append(row)
            if image:
                by_image[item_id] = row
        if row["crafting_materials"]:
            assert image, item_id
            recipes["recipes"][item_id] = {
                "output": source["craft_count"],
                "materials": {x["item_id"]: x["amount"] for x in source["craft_inputs"]},
            }

    for item_id in MATERIAL_NAMES:
        source_rows = [
            (source, output) for source in analysis["items"] for output in (source["recycle_outputs"] or [])
            if output["item_id"] == item_id
        ]
        if not source_rows:
            continue
        target = by_image.get(item_id)
        assert target is not None, item_id
        for source, output in source_rows:
            name = source["name_zh_explanatory"].removesuffix("（暂译）")
            entry = {"name_zh": name, "name_en": source["name_en_raw"] or ENGLISH_NAMES[source["item_id"]],
                     "amount": output["amount"]}
            if entry not in target["recycling_sources"]:
                target["recycling_sources"].append(entry)
        target["recycling_sources"].sort(key=lambda x: -x["amount"])

    assert sum(map(len, config.values())) == 265
    recipes["source"] = "apk-1012/split_UnityDataAssetPack.apk; apk-analysis-1012/新增物品数据.json"
    recipes["version"] = "1.14.11949"
    write(config_path, config)
    write(recipes_path, recipes)
    write(SNAPSHOT, analysis)
    print("已更新 6 个物品、2 个配方及相关回收来源。")


if __name__ == "__main__":
    main()
