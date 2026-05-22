# WokWise — AI 智能中餐教学平台

> 让外国人也能轻松做出地道中餐 / Making authentic Chinese cooking accessible to everyone

## 核心引擎

AI菜谱引擎 `engine.py` 提供：

- **结构化菜谱** — 步骤引导 + 计时器 + 翻车预警
- **厨具自适应** — 燃气/电炉/电磁炉，自动调整火候描述
- **食材替换** — 找不到中式食材 → AI推荐替代方案
- **中英双语** — 菜名/食材中英对照

## 使用

```bash
# 设置厨具
python3 engine.py set 电磁炉

# 获取菜谱
python3 engine.py recipe 宫保鸡丁

# 查询食材替换
python3 engine.py sub 绍兴酒
```

## 路线图

- [x] AI菜谱引擎原型
- [ ] LLM驱动菜谱生成（不依赖模板）
- [ ] Web UI（React）
- [ ] 用户上传菜谱
- [ ] 社区功能
- [ ] iOS / Android App
