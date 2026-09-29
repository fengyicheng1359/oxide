"""验证配方变更不能静默保留计算器旧数据。"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crafting_page import validate_recipes


class RecipeConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'static/config.json').read_text())
        self.recipes = json.loads((ROOT / 'static/crafting-recipes.json').read_text())['recipes']
        self.bandage = next(row for rows in self.config.values() for row in rows
                            if row.get('image') == 'assets/image/bandage.png')

    def test_current_data_matches(self):
        validate_recipes(self.config, self.recipes)

    def test_changed_amount_is_rejected(self):
        self.bandage['crafting_materials'][0]['amount'] = 99
        with self.assertRaisesRegex(ValueError, 'bandage 配方不同步'):
            validate_recipes(self.config, self.recipes)

    def test_changed_material_is_rejected(self):
        replacement = next(row for rows in self.config.values() for row in rows
                           if row.get('image') == 'assets/image/stone.png')
        for key in ('name_zh', 'name_en'):
            self.bandage['crafting_materials'][0][key] = replacement[key]
        with self.assertRaisesRegex(ValueError, 'bandage 配方不同步'):
            validate_recipes(self.config, self.recipes)

    def test_missing_or_removed_recipe_is_rejected(self):
        del self.recipes['bandage']
        with self.assertRaisesRegex(ValueError, '物品集合不同步'):
            validate_recipes(self.config, self.recipes)
        self.recipes['bandage'] = {'output': 1, 'materials': {'cloth': 5}}
        self.bandage['crafting_materials'] = []
        with self.assertRaisesRegex(ValueError, '物品集合不同步'):
            validate_recipes(self.config, self.recipes)

    def test_output_mismatch_is_rejected(self):
        self.bandage['crafting_output_per_batch'] = 2
        with self.assertRaisesRegex(ValueError, 'bandage 配方不同步'):
            validate_recipes(self.config, self.recipes)


if __name__ == '__main__':
    unittest.main()
