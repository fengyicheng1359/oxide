"""按 APK 分析差异更新网站数据，保留网站独立补充的生命值、医疗说明和旧名称。"""
import argparse
import copy
import json
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def read(path): return json.loads(path.read_text())
def write(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def records(folder):
    return {d['item_id']: (p, d) for p in folder.glob('*/*.json') if 'item_id' in (d := read(p))}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis', type=Path, help='含 output-before 和 output-staging 的分析目录')
    args = parser.parse_args()
    analysis = args.analysis.resolve()
    before = records(analysis / 'output-before')
    after = records(analysis / 'output-staging')
    config_path = ROOT / 'dist/static/config.json'
    config = read(config_path)
    existing = {}
    # 有图物品用稳定 ID 匹配；缺图物品用旧中英文名称共同匹配，禁止猜测重名项。
    for group in config.values():
        for item in group:
            slug = Path(item['image']).stem if item.get('image') else None
            if not slug:
                matches = [i for i, (_, d) in before.items() if d['name_zh'] == item['name_zh'] and d['name_en'] == item['name_en']]
                assert len(matches) == 1, (item, matches)
                slug = matches[0]
            assert slug not in existing
            existing[slug] = item
    names = {i: {'name_zh': existing.get(i, d)['name_zh'], 'name_en': existing.get(i, d)['name_en']} for i, (_, d) in after.items()}
    # 名称原值改变时同步新版名称，保留其他经过人工整理的名称。
    for i, (_, d) in after.items():
        if i not in before or before[i][1]['name_en'] != d['name_en']:
            names[i] = {k: d[k] for k in ['name_zh', 'name_en']}
    def material(row): return {'name_en': names[row['item_id']]['name_en'], 'name_zh': names[row['item_id']]['name_zh'], 'amount': row['amount']}
    result = {category: [] for category in config}
    for i, (path, d) in sorted(after.items()):
        item = copy.deepcopy(existing.get(i, {'acquisition_methods': []}))
        item.update(names[i])
        item['attack_power'] = (d.get('combat') or {}).get('base_damage')
        item['crafting_materials'] = [material(x) for x in d['crafting']['ingredients']] if d['crafting']['is_craftable'] else []
        item['recycling_outputs'] = [material(x) for x in d['recycling']['outputs']]
        item['recycling_sources'] = sorted([
            {**names[x['source_item']['item_id']], 'amount': x['result_raw']['m_Amount']}
            for x in d['acquisition']['recycling_sources']], key=lambda x: -x['amount'])
        item['image'] = 'assets/image/' + i + '.png' if d['image']['path'] else None
        if item['image']:
            shutil.copy2(path.parent / d['image']['path'], ROOT / 'dist/static' / item['image'])
        if i not in existing and d['acquisition']['loot_table_candidates']:
            item['acquisition_methods'].append({'type': '掉落', 'detail': '可通过掉落获得'})
        result.setdefault(d['category'], []).append(item)
    assert sum(map(len, result.values())) == len(after)
    write(config_path, result)
    stats_path = ROOT / 'dist/static/game-stats.json'
    stats = read(stats_path)
    stats['weapon_ammunition'] = {i: d['attributes']['config_values'].get('ammoItemShortName', '') for i, (_, d) in after.items() if d['category'] in ('Weapon', 'Tool')}
    for i in set(after) - set(before):
        if after[i][1]['category'] == 'Weapon': stats['weapon_attack_types'][i] = '远程攻击'
    write(stats_path, stats)
    print(f'Updated {len(after)} items and images; preserved independent game statistics.')
if __name__ == '__main__': main()
