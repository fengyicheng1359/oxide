"""核对已有回收产量，补齐稳定物品 ID 和跳过产出的概率。"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis', type=Path)
    args = parser.parse_args()
    records = {row['item_id']: row for p in (args.analysis / 'output-staging').glob('*/*.json')
               if 'item_id' in (row := json.loads(p.read_text()))}
    path = ROOT / 'static/config.json'
    config = json.loads(path.read_text())
    count = 0
    for items in config.values():
        for item in items:
            if not item.get('recycling_outputs'):
                continue
            if item.get('image'):
                slug = Path(item['image']).stem
            else:
                matches = [key for key, row in records.items()
                           if row['name_en'] == item['name_en'] and row['name_zh'] == item['name_zh']]
                assert len(matches) == 1, item['name_zh']
                slug = matches[0]
            outputs = records[slug]['recycling']['outputs']
            assert len(outputs) == len(item['recycling_outputs']), slug
            for output in item['recycling_outputs']:
                matches = [row for row in outputs
                           if (row['name_en'] or row['item_id']) == output['name_en'] and row['amount'] == output['amount']]
                assert len(matches) == 1, (slug, output)
                raw = matches[0]
                chance = raw.get('skip_chance_raw')
                assert chance is None or 0 <= chance <= 1, (slug, chance)
                output.update(item_id=raw['item_id'], skip_chance=chance)
                count += 1
    # 全部核对通过后才写入，保留原有材料名称和回收数量。
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    print(f'已核对 {count} 条回收产物的 ID 和概率。')


if __name__ == '__main__':
    main()
