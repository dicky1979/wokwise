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

# ─── AI菜谱生成（模拟/模板） ──────────────────────────────

TEMPLATE_RECIPES = {
    "宫保鸡丁": {
        "name": "宫保鸡丁 / Kung Pao Chicken",
        "difficulty": "medium",
        "prep_time": 20,
        "cook_time": 10,
        "cuisine": "川",
        "description": "经典川菜，鸡肉滑嫩，花生香脆，麻辣鲜香。全世界最受欢迎的中国菜之一。",
        "ingredients": [
            {"name": "鸡腿肉", "amount": "300g", "substitutes": ["鸡胸肉 Chicken breast"]},
            {"name": "花生米", "amount": "50g", "substitutes": ["腰果 Cashews", "杏仁 Almonds"]},
            {"name": "干辣椒", "amount": "8-10个", "substitutes": ["辣椒碎 Red chili flakes 1tbsp"]},
            {"name": "花椒", "amount": "1tsp", "substitutes": ["花椒油 Sichuan pepper oil 1/2tsp"]},
            {"name": "葱", "amount": "3根", "substitutes": []},
            {"name": "姜", "amount": "3片", "substitutes": []},
            {"name": "蒜", "amount": "3瓣", "substitutes": []},
            {"name": "生抽", "amount": "2tbsp", "substitutes": ["普通酱油 2tbsp"]},
            {"name": "醋", "amount": "1tbsp", "substitutes": ["香醋 Balsamic 1tbsp"]},
            {"name": "糖", "amount": "1tbsp", "substitutes": []},
            {"name": "料酒", "amount": "1tbsp", "substitutes": ["干雪利酒 Dry Sherry 1tbsp"]},
            {"name": "玉米淀粉", "amount": "1tbsp", "substitutes": ["土豆淀粉 Potato starch"]},
            {"name": "芝麻油", "amount": "1tsp", "substitutes": []}
        ],
        "equipment": ["炒锅 Wok", "平底锅 Skillet（替代）"],
        "steps": [
            {"order": 1, "action": "鸡肉切1.5cm丁，用1tbsp生抽+料酒+淀粉腌制15分钟", "duration": 15, "warning": "腌制是关键！肉嫩不嫩就看这步"},
            {"order": 2, "action": "调酱汁：生抽1tbsp+醋+糖+淀粉1/2tsp+水2tbsp混合", "duration": 2},
            {"order": 3, "action": "中高火烧热锅，加2tbsp油", "duration": 1},
            {"order": 4, "action": "放入干辣椒和花椒，爆香30秒（不要焦）", "duration": 0.5, "warning": "⚠️ 辣椒容易糊！闻到香味就进行下一步"},
            {"order": 5, "action": "放入鸡肉，快速翻炒至表面变白（约2分钟）", "duration": 2, "warning": "⚠️ 肉下锅别马上翻！等30秒再炒散"},
            {"order": 6, "action": "加入葱姜蒜，翻炒30秒出香味", "duration": 0.5},
            {"order": 7, "action": "倒入酱汁，快速翻炒至收汁（约1分钟）", "duration": 1},
            {"order": 8, "action": "加入花生米，翻炒均匀，出锅", "duration": 0.5}
        ],
        "tips": ["鸡肉不要炒太久，变白即可", "花生米用烤过的更香", "酱汁提前调好，炒的时候不手忙脚乱"],
        "common_mistakes": ["辣椒炒焦了发苦", "鸡肉炒老了", "花生米不脆了（应该最后放）"]
    },
    "麻婆豆腐": {
        "name": "麻婆豆腐 / Mapo Tofu",
        "difficulty": "easy",
        "prep_time": 10,
        "cook_time": 15,
        "cuisine": "川",
        "description": "麻辣鲜香的经典川菜，嫩豆腐入口即化，配饭绝品。",
        "ingredients": [
            {"name": "嫩豆腐", "amount": "1盒（约400g）", "substitutes": ["中硬豆腐 Medium tofu（口感不同）"]},
            {"name": "猪肉末", "amount": "100g", "substitutes": ["牛肉末", "素肉碎 Plant-based mince"]},
            {"name": "豆瓣酱", "amount": "1.5tbsp", "substitutes": ["Gochujang 1.5tbsp + 少许酱油"]},
            {"name": "花椒粉", "amount": "1/2tsp", "substitutes": ["花椒油 1/4tsp"]},
            {"name": "豆豉", "amount": "1tsp", "substitutes": ["味噌 1/2tsp"]},
            {"name": "葱花", "amount": "适量", "substitutes": []},
            {"name": "蒜末", "amount": "2瓣", "substitutes": []},
            {"name": "生抽", "amount": "1tbsp", "substitutes": []},
            {"name": "玉米淀粉", "amount": "1tbsp + 水2tbsp", "substitutes": []}
        ],
        "equipment": ["炒锅 Wok", "深平底锅"],
        "steps": [
            {"order": 1, "action": "豆腐切2cm方块，沸水加盐焯2分钟，沥干", "duration": 3, "warning": "焯水让豆腐更嫩不易碎"},
            {"order": 2, "action": "中火烧热锅，加1tbsp油，放入肉末炒散", "duration": 2},
            {"order": 3, "action": "加入豆瓣酱和豆豉，小火炒出红油（约1分钟）", "duration": 1, "warning": "⚠️ 小火！豆瓣酱容易糊"},
            {"order": 4, "action": "加蒜末炒香，倒入200ml水", "duration": 1},
            {"order": 5, "action": "轻轻放入豆腐，加生抽，中小火煮5分钟入味", "duration": 5, "warning": "⚠️ 别用铲子乱翻！轻轻晃动锅即可"},
            {"order": 6, "action": "淋入水淀粉勾芡，轻轻推匀", "duration": 1},
            {"order": 7, "action": "撒花椒粉和葱花，出锅", "duration": 0.5}
        ],
        "tips": ["豆腐焯水加盐更入味", "全程少翻动，豆腐才完整", "现磨花椒粉比预磨的香10倍"],
        "common_mistakes": ["豆腐碎了（翻太多次）", "豆瓣酱炒糊了（火太大）", "勾芡太厚（淀粉太多）"]
    }
}

# ─── 核心引擎 ──────────────────────────────────────────────

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
