#!/usr/bin/env python3
"""
WokWise — AI菜谱引擎核心
输入菜名 → 结构化菜谱 + 厨具自适应 + 食材替换
"""
import json
import os
import sys
from datetime import datetime

# ─── 数据模型 ──────────────────────────────────────────────

RECIPE_SCHEMA = {
    "name": "",           # 菜名（中英文）
    "difficulty": "",     # easy / medium / hard
    "prep_time": "",      # 准备时间（分钟）
    "cook_time": "",      # 烹饪时间（分钟）
    "cuisine": "",        # 菜系（川/粤/鲁/苏/湘/闽/浙/徽）
    "description": "",    # 简短描述
    "ingredients": [],    # [{"name":"","amount":"","substitutes":[]}]
    "equipment": [],      # 需要的厨具
    "steps": [            # [{"order":1,"action":"","duration":"","warning":""}]
    ],
    "tips": [],           # 技巧提示
    "common_mistakes": [], # 常见错误
}

# ─── 厨具映射数据库 ──────────────────────────────────────

STOVE_MAPPING = {
    "gas": {
        "label": "燃气灶 Gas Stove",
        "low": "小火（燃气最小火）",
        "medium_low": "中小火（火焰高度约2cm）",
        "medium": "中火（火焰高度约3cm）",
        "medium_high": "中高火（火焰高度约5cm）",
        "high": "大火（最大火）",
        "wok_hei": "✅ 可产生锅气"
    },
    "electric": {
        "label": "电炉 Electric Coil",
        "low": "2档/6",
        "medium_low": "3档/6",
        "medium": "4档/6",
        "medium_high": "5档/6",
        "high": "6档/6（最高）",
        "wok_hei": "❌ 无法产生锅气，建议用厚底锅"
    },
    "induction": {
        "label": "电磁炉 Induction",
        "low": "3档/9",
        "medium_low": "4-5档/9",
        "medium": "6档/9",
        "medium_high": "7档/9",
        "high": "8-9档/9",
        "wok_hei": "⚠️ 需要平底炒锅，可接近锅气效果"
    },
    "ceramic": {
        "label": "陶瓷炉 Ceramic Hob",
        "low": "2档/6",
        "medium_low": "3档/6",
        "medium": "4档/6",
        "medium_high": "5档/6",
        "high": "6档/6",
        "wok_hei": "❌ 升温慢，不适合爆炒"
    }
}

# ─── 食材替换数据库 ──────────────────────────────────────

INGREDIENT_SUBSTITUTES = {
    "绍兴酒": {
        "en": "Shaoxing wine",
        "substitutes": [
            {"name": "干雪利酒 Dry Sherry", "ratio": "1:1", "note": "最接近的选择"},
            {"name": "清酒 Sake", "ratio": "1:1", "note": "清淡版"},
            {"name": "米酒+少许糖", "ratio": "1:1 + 1/2tsp糖", "note": "家常替代"}
        ]
    },
    "老抽": {
        "en": "Dark soy sauce",
        "substitutes": [
            {"name": "生抽+少许糖", "ratio": "3:1 + 1/2tsp糖", "note": "颜色变深"},
            {"name": "普通酱油+molasses", "ratio": None, "note": "0.5tsp糖浆调色"}
        ]
    },
    "生抽": {
        "en": "Light soy sauce",
        "substitutes": [
            {"name": "普通酱油 All-purpose soy sauce", "ratio": "1:1", "note": "最接近"},
            {"name": "Tamari（无麸质）", "ratio": "1:1", "note": "无麸质选择"}
        ]
    },
    "蚝油": {
        "en": "Oyster sauce",
        "substitutes": [
            {"name": "素食蚝油 Vegan oyster sauce", "ratio": "1:1", "note": "蘑菇基"},
            {"name": "酱油+少许糖", "ratio": "2:1", "note": "可不加糖"}
        ]
    },
    "豆瓣酱": {
        "en": "Doubanjiang (Chili bean paste)",
        "substitutes": [
            {"name": "Gochujang 韩式辣酱", "ratio": "1:1", "note": "稍甜"},
            {"name": "辣豆瓣酱+豆豉", "ratio": "1:1", "note": "风味最接近"}
        ]
    },
    "陈醋": {
        "en": "Chinkiang vinegar (Black vinegar)",
        "substitutes": [
            {"name": "意大利香醋 Balsamic vinegar", "ratio": "1:1", "note": "稍微偏甜"},
            {"name": "苹果醋+少许酱油", "ratio": "3:1", "note": "可替代"}
        ]
    },
    "花椒": {
        "en": "Sichuan peppercorns",
        "substitutes": [
            {"name": "花椒油 Sichuan pepper oil", "ratio": "1tsp代替", "note": "最后加"},
            {"name": "青花椒 Green Sichuan pepper", "ratio": "1:1", "note": "更麻"}
        ]
    },
    "芝麻油": {
        "en": "Sesame oil",
        "substitutes": [
            {"name": "烤芝麻碾碎 Toasted sesame seeds", "ratio": None, "note": "最后撒"},
            {"name": "花生油", "ratio": "1:1", "note": "少香味"}
        ]
    },
    "豆豉": {
        "en": "Fermented black beans",
        "substitutes": [
            {"name": "味噌 miso paste", "ratio": "1:2", "note": "风味不同，可替代咸味"},
            {"name": "酱油+少许酵母酱", "ratio": None, "note": "应急替代"}
        ]
    }
}

# ─── 菜谱加载 ──────────────────────────────────────────────

def load_all_recipes():
    """加载内置菜谱和用户自定义菜谱"""
    recipes = {}
    base = os.path.dirname(os.path.abspath(__file__))

    # 内置菜谱
    builtin = os.path.join(base, "recipes_builtin.json")
    if os.path.exists(builtin):
        with open(builtin) as f:
            recipes.update(json.load(f))

    # 自定义菜谱（AI生成 + 用户上传）
    custom = os.path.join(base, "recipes_custom.json")
    if os.path.exists(custom):
        with open(custom) as f:
            recipes.update(json.load(f))

    return recipes

TEMPLATE_RECIPES = load_all_recipes()

class WokWiseEngine:
    def __init__(self):
        self.stove_type = "gas"  # 默认燃气灶

    def set_kitchen(self, stove_type="gas", wok_type="round"):
        """设置用户厨房"""
        self.stove_type = stove_type
        return f"厨房已设置：{STOVE_MAPPING.get(stove_type, {}).get('label', stove_type)}"

    def get_recipe(self, dish_name, lang="en"):
        """获取菜谱（按菜名查找模板）"""
        for name_cn, recipe in TEMPLATE_RECIPES.items():
            if dish_name.lower() in name_cn.lower() or dish_name.lower() in recipe["name"].lower():
                return self._adapt_recipe(recipe)
        return {"error": f"暂未收录「{dish_name}」，请尝试宫保鸡丁或麻婆豆腐"}

    def _adapt_recipe(self, recipe):
        """根据厨房设置自适应菜谱"""
        adapted = json.loads(json.dumps(recipe))  # 深拷贝
        stove = STOVE_MAPPING.get(self.stove_type, STOVE_MAPPING["gas"])

        # 火候翻译映射
        heat_map = {
            "小火": stove["low"],
            "中小火": stove["medium_low"],
            "中火": stove["medium"],
            "中高火": stove["medium_high"],
            "大火": stove["high"],
        }
        for step in adapted["steps"]:
            action = step["action"]
            for cn_heat, en_heat in heat_map.items():
                if cn_heat in action:
                    action = action.replace(cn_heat, f"{cn_heat}({en_heat})")
                    step["action"] = action
                    break

        # 替换食材
        for ing in adapted["ingredients"]:
            name = ing["name"]
            if name in INGREDIENT_SUBSTITUTES:
                sub_data = INGREDIENT_SUBSTITUTES[name]
                ing["alt_name"] = sub_data["en"]
                ing["substitutes"] = [s["name"] for s in sub_data["substitutes"]]

        # 添加厨具提示
        adapted["stove_info"] = stove["wok_hei"]

        return adapted

    def search_substitute(self, ingredient):
        """查询食材替代方案"""
        if ingredient in INGREDIENT_SUBSTITUTES:
            data = INGREDIENT_SUBSTITUTES[ingredient]
            result = f"「{ingredient}」({data['en']}) 替代方案：\n"
            for s in data["substitutes"]:
                result += f"  • {s['name']}"
                if s.get("ratio"):
                    result += f"（比例 {s['ratio']}）"
                if s.get("note"):
                    result += f" — {s['note']}"
                result += "\n"
            return result
        return f"暂未收录「{ingredient}」的替代方案"

# ─── CLI 测试 ──────────────────────────────────────────────

def main():
    engine = WokWiseEngine()

    if len(sys.argv) < 2:
        print("WokWise AI菜谱引擎")
        print()
        print("命令:")
        print("  recipe <菜名>     获取菜谱")
        print("  set <燃气/电炉/电磁炉>  设置厨具")
        print("  sub <食材名>      查询食材替换")
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "set":
        stove_map = {"燃气":"gas","电炉":"electric","电磁炉":"induction","陶瓷炉":"ceramic"}
        key = args[0] if args else ""
        stove = stove_map.get(key, "gas")
        print(engine.set_kitchen(stove))

    elif cmd == "recipe":
        dish = " ".join(args) if args else "宫保鸡丁"
        recipe = engine.get_recipe(dish)
        if "error" in recipe:
            print(recipe["error"])
            return
        print(f"\n{'='*50}")
        print(f"  {recipe['name']}")
        print(f"  难度: {recipe['difficulty']}  时间: {recipe['prep_time']+recipe['cook_time']}分钟")
        print(f"  菜系: {recipe['cuisine']}  |  锅气: {recipe.get('stove_info','')}")
        print(f"{'='*50}")
        print(f"\n📋 食材")
        for ing in recipe["ingredients"]:
            alt = f" ({ing['name']})" if ing.get("alt_name") else ""
            subs = ing.get("substitutes", [])
            sub_str = f"  → 替代: {', '.join(subs[:2])}" if subs else ""
            ing_name = ing.get("alt_name") or ing["name"]
            print(f"  • {ing['amount']} {ing_name}{sub_str}")
        print(f"\n👨‍🍳 步骤")
        for step in recipe["steps"]:
            warn = f"\n    ⚠️ {step['warning']}" if step.get("warning") else ""
            print(f"  {step['order']}. {step['action']}{warn}")
        print(f"\n💡 技巧")
        for tip in recipe["tips"]:
            print(f"  • {tip}")
        print(f"\n❌ 常见错误")
        for err in recipe["common_mistakes"]:
            print(f"  • {err}")

    elif cmd == "sub":
        ing = " ".join(args) if args else "绍兴酒"
        print(engine.search_substitute(ing))

    else:
        print(f"未知命令: {cmd}")

if __name__ == "__main__":
    main()
