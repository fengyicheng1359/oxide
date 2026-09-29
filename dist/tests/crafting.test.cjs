const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { calculate, normalizeState, quantity } = require('../static/crafting.js');
const recipes = JSON.parse(readFileSync(join(__dirname, '../static/crafting-recipes.json'))).recipes;
const items = {};
for (const [id, recipe] of Object.entries(recipes)) {
  items[id] = { recipe };
  for (const material of Object.keys(recipe.materials)) items[material] ||= {};
}

test('步枪弹按每批 6 发取整：7 发需要两批材料，产出 12 发', () => {
  const result = calculate(items, { 'ammo.rifle': 7 }, {});
  assert.deepEqual(result.products[0], { id: 'ammo.rifle', requested: 7, batches: 2, produced: 12 });
  const amounts = Object.fromEntries(result.materials.map(m => [m.id, m.required]));
  assert.deepEqual(amounts, { 'gun.powder': 8, 'metal.fragment': 12 });
});
test('共享材料先合并，库存只扣一次；超额库存不会出现负缺口', () => {
  const result = calculate(items, { 'ammo.rifle': 6, 'ammo.pistol': 10 }, { 'gun.powder': 5, 'metal.fragment': 100 });
  const powder = result.materials.find(m => m.id === 'gun.powder');
  assert.equal(powder.required, recipes['ammo.rifle'].materials['gun.powder'] + recipes['ammo.pistol'].materials['gun.powder']);
  assert.equal(powder.missing, Math.max(0, powder.required - 5));
  assert.equal(result.materials.find(m => m.id === 'metal.fragment').missing, 0);
});
test('火药按每批 10 份计算，不擅自展开其他配方中的火药', () => {
  const result = calculate(items, { 'gun.powder': 11 }, {});
  assert.equal(result.products[0].produced, 20);
  assert.equal(result.materials.find(m => m.id === 'coal').required, 30);
  assert.equal(result.materials.find(m => m.id === 'sulfur').required, 20);
  assert.deepEqual(calculate(items, { 'ammo.rifle': 1 }, {}).materials.map(m => m.id).sort(), ['gun.powder', 'metal.fragment']);
});
test('损坏或旧版存储、非法数量、未知 ID 和非制作物品不会进入清单', () => {
  assert.deepEqual(normalizeState({ version: 9, targets: { bandage: 3 } }, items).targets, {});
  const result = normalizeState({ version: 1, targets: { bandage: 2, cloth: 2, unknown: 4, 'ammo.rifle': -1, 'ammo.pistol': 1.5 }, inventory: { cloth: 5, unknown: 3, coal: '3', sulfur: -2 } }, items);
  assert.deepEqual(result.targets, { bandage: 2 });
  assert.deepEqual(result.inventory, { cloth: 5 });
  for (const n of [NaN, Infinity, -1, .5, 1000001, '1']) assert.equal(quantity(n), false);
  assert.equal(quantity(0), true);
});
test('修改数量及移除目标不会消耗库存或保留过期材料', () => {
  const inventory = { cloth: 8 };
  assert.equal(calculate(items, { bandage: 2 }, inventory).materials[0].missing, 2);
  assert.equal(calculate(items, { bandage: 1 }, inventory).materials[0].missing, 0);
  assert.deepEqual(calculate(items, {}, inventory), { products: [], materials: [] });
  assert.deepEqual(inventory, { cloth: 8 });
});

const { recyclingOptions } = require('../static/crafting.js');
test('回收补缺按来源分别取整，不将概率产出当作保证结果', () => {
  const sources = [
    { id: 'ammo', amount: 1, skipChance: .5 },
    { id: 'pipe', amount: 5, skipChance: 0 },
    { id: 'unknown', amount: 10, skipChance: null },
    { id: 'disabled', amount: 100, skipChance: 1 }
  ];
  const result = recyclingOptions(sources, 12);
  assert.deepEqual(result.map(r => [r.id, r.count]), [['pipe', 3], ['unknown', null], ['ammo', null]]);
  assert.equal(recyclingOptions(sources, 10)[0].count, 2);
  assert.equal(recyclingOptions(sources, 1)[0].count, 1);
  assert.deepEqual(recyclingOptions(sources, 0), []);
  assert.deepEqual(recyclingOptions([], 12), []);
  assert.equal(sources[1].count, undefined);
});
