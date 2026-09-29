"""制作计算器页面与各语种运行数据；配方使用稳定物品 ID，不按译名合并。"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
LABELS = ['制作计算器', '添加', '移除', '制作数量', '制作次数', '实际产出', '每次产出', '材料',
          '需要', '已有', '还缺', '清单为空', '从左侧选择要制作的物品。', '没有找到匹配的物品。',
          '已保存到此浏览器', '无法保存，刷新后清单可能丢失', '已复制', '复制失败，请手动复制下方清单',
          '材料已备齐', '还缺 {count} 种材料', '已选 {count} 种物品', '所有物品', '全部清除',
          '清除清单和库存？', '物品百科', '查看回收来源', '收起回收来源', '暂无已收录的回收来源。',
          '每件回收产量', '补足缺口需回收', '概率产出，不保证数量',
          '各方案单独补足当前缺口，不会自动扣减清单或库存。',
          '回收数量按当前数据估算，实际产出可能受物品状态或服务器规则影响。']


def validate_recipes(config, recipes):
    """阻止两份配方静默分叉：校验可制作集合、单次产量和每一种材料。"""
    ids_by_name = {}
    for rows in config.values():
        for row in rows:
            if row.get('image'):
                key = (row['name_zh'], row['name_en'])
                ids_by_name.setdefault(key, []).append(Path(row['image']).stem)
    expected = {}
    for rows in config.values():
        for row in rows:
            if not row.get('image') or not row.get('crafting_materials'):
                continue
            slug = Path(row['image']).stem
            materials = {}
            for material in row['crafting_materials']:
                matches = ids_by_name.get((material['name_zh'], material['name_en']), [])
                if len(matches) != 1:
                    raise ValueError(f'{slug} 材料无法唯一对应物品 ID：{material["name_zh"]}')
                material_id = matches[0]
                materials[material_id] = materials.get(material_id, 0) + material['amount']
            expected[slug] = {'output': row['crafting_output_per_batch'], 'materials': materials}
    if expected.keys() != recipes.keys():
        raise ValueError(f'可制作物品集合不同步：{expected.keys() ^ recipes.keys()}')
    for slug, recipe in expected.items():
        if recipe != recipes[slug]:
            raise ValueError(f'{slug} 配方不同步：共用数据 {recipe}，计算器 {recipes[slug]}')


def localized_data(translator, mapping):
    from build_static import display_category, category_name
    config = json.loads((ROOT / 'static/config.json').read_text())
    recipes = json.loads((ROOT / 'static/crafting-recipes.json').read_text())['recipes']
    validate_recipes(config, recipes)
    english = json.loads((ROOT / 'static/i18n/game/en.json').read_text())
    from build_i18n import game_text
    items = {}
    for category, rows in config.items():
        for row in rows:
            if not row.get('image'):
                continue
            slug = Path(row['image']).stem
            token = mapping['items'][slug]['name']
            items[slug] = {'name': game_text(translator.game[token]), 'english': game_text(english[token]),
                           'image': row['image'], 'category': translator.text(category_name(display_category(category)))}
    for slug, recipe in recipes.items():
        assert slug in items and set(recipe['materials']) <= items.keys(), slug
        items[slug]['recipe'] = recipe
    recycling_sources = {}
    for category, rows in config.items():
        for row in rows:
            if not row.get('image'):
                continue
            source = Path(row['image']).stem
            for output in row.get('recycling_outputs', []):
                material = output['item_id']
                if material not in items or output['amount'] <= 0 or output.get('skip_chance') == 1:
                    continue
                recycling_sources.setdefault(material, []).append({
                    'id': source, 'amount': output['amount'], 'skipChance': output.get('skip_chance'),
                    'priority': 0 if category in {'Component', 'Resource'} else 1})
    # 占位文案直接读字典，保留 {count} 给浏览器替换。
    return {'items': items, 'recyclingSources': recycling_sources, 'labels': {key: translator.ui.get(key, key) for key in LABELS}}


def page(header, footer):
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>制作计算器</title><link rel="stylesheet" href="./styles.css"><link rel="stylesheet" href="./static/crafting.css"><script defer src="./static/crafting.js"></script></head><body>''' + header('./', selected='crafting') + '''
<main class="craft-shell" id="craft-app">
  <div class="craft-intro"><div><span class="eyebrow">OXIDE / FIELD WORKBENCH</span><h1>制作计算器</h1><p>选好要制作的装备，算清出发前还缺哪些材料。</p></div><a class="craft-jump" href="#craft-plan">查看制作清单 ↓</a></div>
  <div class="craft-layout">
    <section class="craft-catalog" aria-labelledby="craft-catalog-title">
      <div class="craft-heading"><span class="craft-step">01</span><h2 id="craft-catalog-title">选择物品</h2></div>
      <label class="craft-search"><span class="visually-hidden">搜索名称或英文名</span><input id="craft-search" type="search" placeholder="搜索名称或英文名" autocomplete="off"></label>
      <label class="craft-filter"><span>物品分类</span><select id="craft-category"><option value="">所有物品</option></select></label>
      <p id="craft-catalog-status" class="craft-muted" role="status"></p>
      <div id="craft-items" class="craft-items"></div>
    </section>
    <section class="craft-plan" id="craft-plan" aria-labelledby="craft-plan-title">
      <div class="craft-heading"><span class="craft-step">02</span><h2 id="craft-plan-title">制作清单</h2><button id="craft-clear" class="craft-text-button" type="button">全部清除</button></div>
      <p class="craft-help">数量指想得到的成品数量；材料按完整制作批次计算。</p>
      <div id="craft-targets"></div>
      <div class="craft-material-heading"><div class="craft-heading"><span class="craft-step">03</span><h2>材料缺口</h2></div><p class="craft-help">填写手头已有的材料，自动扣除库存。</p></div>
      <p id="craft-summary" class="craft-summary" role="status" aria-live="polite"></p>
      <div class="craft-table-wrap"><table class="craft-table"><thead><tr><th scope="col">材料</th><th scope="col">需要</th><th scope="col">已有</th><th scope="col">还缺</th></tr></thead><tbody id="craft-materials"></tbody></table></div>
      <div class="craft-actions"><button id="craft-copy" type="button">复制材料清单</button><span id="craft-save" class="craft-muted" role="status"></span></div>
      <textarea id="craft-copy-fallback" hidden readonly aria-label="材料清单"></textarea>
      <p id="craft-message" class="craft-muted" role="status"></p>
      <details class="craft-notes"><summary>计算方式</summary><p>仅统计配方直接需要的材料，不继续拆解火药等半成品，也不把它们视为可自动回收的库存。</p><p>实际产出可能略多于目标数量。相同材料合并后只扣一次库存；库存不会因计算而被消耗。</p><p>配方依据游戏版本 1.13.11920 的本地数据，未包含蓝图解锁、工作台条件与服务器自定义改动。</p></details>
    </section>
  </div>
  <noscript><p>请启用 JavaScript 使用计算器；也可以在物品百科查看配方。</p><a href="./items.html">物品百科</a></noscript>
</main><script id="craft-data" type="application/json">{}</script>''' + footer() + '</body></html>'
