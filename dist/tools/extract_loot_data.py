"""从指定版本 APK 提取军用箱奖励池；不把奖励池条目当作已确认的地图掉落来源。"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def extract(apk, version):
    """沿本包内引用展开可能奖励；保留叶节点证据，不推算实际开箱概率和数量。"""
    import UnityPy

    with zipfile.ZipFile(apk) as package:
        bundles = [name for name in package.namelist()
                   if Path(name).name.startswith('data-loot-items_assets_all_') and name.endswith('.bundle')]
        if len(bundles) != 1:
            raise ValueError('安装包必须包含唯一的物品掉落配置包')
        bundle = bundles[0]
        raw = package.read(bundle)
        config_bundles = [name for name in package.namelist()
                          if Path(name).name.startswith('data-core-local_assets_all_') and name.endswith('.bundle')]
        if len(config_bundles) != 1:
            raise ValueError('安装包必须包含唯一的核心配置包')
        config_raw = package.read(config_bundles[0])
    environment = UnityPy.load(raw)
    nodes = {obj.path_id: obj.read_typetree() for obj in environment.objects
             if obj.type.name == 'MonoBehaviour'}
    roots = [key for key, node in nodes.items() if node.get('m_Name') == 'LootSpawn.MilitaryBox']
    if len(roots) != 1:
        raise ValueError('未找到唯一的军用箱奖励池')
    evidence = []

    def collect(key, parents):
        if key in parents:
            raise ValueError('掉落配置出现循环引用')
        node = nodes[key]
        items = {row['item'] for row in node['items']}
        evidence.append({'path_id': str(key), 'name': node['m_Name']})
        for entry in node['subSpawn']:
            if entry['probability'] <= 0:
                continue
            reference = entry['category']
            if reference['m_FileID'] != 0 or reference['m_PathID'] not in nodes:
                raise ValueError('奖励池引用了当前资源包外的未解析配置')
            items.update(collect(reference['m_PathID'], parents + (key,)))
        return items

    items = collect(roots[0], ())
    bindings = []
    root_object = next(obj for obj in environment.objects if obj.path_id == roots[0])
    configs = UnityPy.load(config_raw)
    for obj in configs.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        config = obj.read_typetree()
        if config.get('m_Name') != 'CandyEffectsConfig':
            continue
        reference = config['JackpotLoot']
        target_file = obj.assets_file.externals[reference['m_FileID'] - 1].path.rsplit('/', 1)[-1]
        if reference['m_PathID'] != roots[0] or target_file != root_object.assets_file.name:
            raise ValueError('糖果大奖配置与当前军用箱奖励池的引用不匹配')
        bindings.append({'bundle': config_bundles[0], 'bundle_sha256': hashlib.sha256(config_raw).hexdigest(),
                         'config': 'CandyEffectsConfig', 'field': 'JackpotLoot',
                         'path_id': str(obj.path_id), 'target_path_id': str(roots[0])})
    return {
        'version': version,
        'evidence': {'apk': apk.name, 'bundle': bundle,
                     'bundle_sha256': hashlib.sha256(raw).hexdigest(),
                     'root_path_id': str(roots[0]), 'nodes': evidence, 'config_references': bindings},
        'sources': [{'id': 'military-crate', 'name': '军用箱奖励池',
                     'binding_status': 'pool_only', 'items': sorted(items)}],
        'extra_items': {'fn.fal': {'name_token': 'fn.fal', 'english': 'FN FAL'}},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--version', required=True, help='经安装包 Manifest 核对的版本号')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'static/loot.json')
    args = parser.parse_args()
    data = extract(args.apk, args.version)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f"已提取 {len(data['sources'][0]['items'])} 种可能奖励；尚未确认箱体绑定、地点、刷新和实际概率。")


if __name__ == '__main__':
    main()
