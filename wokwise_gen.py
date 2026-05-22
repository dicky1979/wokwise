#!/usr/bin/env python3
"""
WokWise LLM菜谱生成器
输入任何菜名 → AI生成结构化菜谱 → 保存到模板库
"""
import json
import os
import sys
import subprocess

TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "recipes_custom.json")

def load_custom_recipes():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE) as f:
            return json.load(f)
    return {}

def save_custom_recipes(recipes):
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("用法: wokwise-gen <菜名> [英文菜名] [菜系]")
        return

    dish_cn = sys.argv[1]
    dish_en = sys.argv[2] if len(sys.argv) > 2 else ""
    cuisine = sys.argv[3] if len(sys.argv) > 3 else "川"

    # 输出结构化菜谱模板（供AI填充）
    template = {
        "name": f"{dish_cn} / {dish_en or dish_cn}",
        "difficulty": "medium",
        "prep_time": 15,
        "cook_time": 15,
        "cuisine": cuisine,
        "description": "",
        "ingredients": [],
        "equipment": [],
        "steps": [],
        "tips": [],
        "common_mistakes": []
    }

    print(json.dumps(template, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
