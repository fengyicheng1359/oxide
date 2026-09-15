"""从本地 APK 导出数据和语言表提取站点所需的 token。"""
from pathlib import Path
import json
r=Path(__file__).resolve().parents[2];out=r/'dist/static/i18n';out.mkdir(exist_ok=True)
langs=['zh','en','ja','ko','fr','de','es','pt','ru'];tables={l:json.loads((r/f'resource/localization/json/{l}.json').read_text()) for l in langs}
overrides={'zh':'大型背包','en':'Large Backpack','ja':'大型バックパック','ko':'대형 배낭','fr':'Grand sac à dos','de':'Großer Rucksack','es':'Mochila grande','pt':'Mochila grande','ru':'Большой рюкзак'}
(out/'game-overrides.json').write_text(json.dumps({'reason':'APK 中 backpack.big 的名称 token 在下载的官方语言表中缺失，以下为站点补译。','backpack.big':overrides},ensure_ascii=False,indent=2)+'\n')
for l in langs:tables[l]['backpack.big']=overrides[l]
raw=[o['data'] for o in json.loads((r/'apk-analysis-20260911/data-items-dataso.json').read_text())['objects'] if 'm_ShortName' in o.get('data',{})];byshort={d['m_ShortName']:d for d in raw}
config=json.loads((r/'dist/static/config.json').read_text());names={};items={};used=set();missing=[]
for group in config.values():
 for item in group:
  if not item.get('image'):continue
  slug=Path(item['image']).stem;d=byshort.get(slug)
  if not d:missing.append(slug);continue
  token=d['m_DisplayName']['token'];desc=d['m_Description'].get('token');craft=d['m_CraftDescription'].get('token')
  assert all(token in tab for tab in tables.values()),(slug,token)
  items[slug]={'name':token,'description':desc if desc and all(desc in t for t in tables.values()) else None,'craft_description':craft if craft and all(craft in t for t in tables.values()) else None}
  names[item['name_zh']]=token
  for key in items[slug].values():
   if key:used.add(key)
# 这两个旧中文标签对应的原始短名已在 APK 数据中确认，英文回退名有重名。
for label,token in {'圣诞倒数日历（用途待核实）':'xmas.advent','贴纸（原英文显示名为袜子花环）':'sticker'}.items():
 names[label]=token;used.add(token)
# 材料与回收来源还包含没有独立页面的物品，按导出数据中的英文名或短名精确匹配。
for group in config.values():
 for item in group:
  for field in ['crafting_materials','recycling_sources','recycling_outputs']:
   for material in item.get(field,[]):
    if material['name_zh'] in names:continue
    matches=[d for d in raw if material['name_en'] in [d['m_Name'],d['m_ShortName'],d['m_DisplayName'].get('english')]]
    ts={d['m_DisplayName']['token'] for d in matches}
    if len(ts)==1:
     token=ts.pop()
     if all(token in tab for tab in tables.values()):names[material['name_zh']]=token;used.add(token);continue
    missing.append(material)
assert not missing,missing
(out/'item-tokens.json').write_text(json.dumps({'source':'m_ShortName → m_DisplayName / m_Description / m_CraftDescription','items':items,'legacy_names':names},ensure_ascii=False,indent=2)+'\n')
(out/'game').mkdir(exist_ok=True)
for l,t in tables.items():(out/f'game/{l}.json').write_text(json.dumps({k:t[k] for k in sorted(used)},ensure_ascii=False,indent=2)+'\n')
print('items',len(items),'names',len(names),'tokens',len(used))
