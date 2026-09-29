"""补齐共用配方的单次产量，核对材料后生成计算器数据。"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis', type=Path, help='包含 output-staging 的 APK 分析目录')
    args = parser.parse_args()
    records = {row['item_id']: row for path in (args.analysis / 'output-staging').glob('*/*.json')
               if 'item_id' in (row := json.loads(path.read_text()))}
    config = json.loads((ROOT / 'static/config.json').read_text())
    recipes = {}
    count = 0
    for items in config.values():
        for item in items:
            if not item.get('crafting_materials'):
                item['crafting_output_per_batch'] = None
                continue
            if item.get('image'):
                slug = Path(item['image']).stem
            else:
                # 缺图物品按中英文名称同时匹配，重名或无匹配时停止，不猜测 ID。
                matches = [key for key, row in records.items()
                           if row['name_en'] == item['name_en'] and row['name_zh'] == item['name_zh']]
                assert len(matches) == 1, (item['name_zh'], matches)
                slug = matches[0]
            recipe = records[slug]['crafting']
            assert recipe['is_craftable'] and recipe['output_per_batch'] > 0, slug
            current = {(m['name_en'], m['amount']) for m in item['crafting_materials']}
            extracted = {(m['name_en'] or m['item_id'], m['amount']) for m in recipe['ingredients']}
            assert current == extracted, (slug, current, extracted)
            output = recipe['output_per_batch']
            assert isinstance(output, int) and output > 0, slug
            item['crafting_output_per_batch'] = output
            count += 1
            if not item.get('image'):
                continue
            recipes[slug] = {'output': item['crafting_output_per_batch'],
                             'materials': {m['item_id']: m['amount'] for m in recipe['ingredients']}}
    snapshot = {'source': str(args.analysis / 'output-staging'),
                'version': '1.13.11920', 'recipes': recipes}
    (ROOT / 'static/config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'static/crafting-recipes.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    print(f'已补齐 {count} 个共用配方；计算器包含 {len(recipes)} 个有图物品。')


if __name__ == '__main__':
    main()
