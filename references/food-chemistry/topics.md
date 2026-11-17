# Food Chemistry 主题地图

> 本页是**检索地图**，不是教材摘要。每个主题都应回到对应 PDF 页核对条件、单位和上下文。

## 1. 章节索引

| 章 | 主题 | PDF 起页 | 主题条目数 |
|---|---|---:|---:|
| 0 | Water | 45 | 13 |
| 1 | Amino Acids, Peptides, Proteins | 52 | 180 |
| 2 | Enzymes | 137 | 140 |
| 3 | Lipids | 202 | 175 |
| 4 | Carbohydrates | 292 | 213 |
| 5 | Aroma Compounds | 384 | 92 |
| 6 | Vitamins | 447 | 64 |
| 7 | Minerals | 465 | 35 |
| 8 | Food Additives | 473 | 110 |
| 9 | Food Contamination | 511 | 53 |
| 10 | Milk and Dairy Products | 542 | 95 |
| 11 | Eggs | 590 | 62 |
| 12 | Meat | 607 | 137 |
| 13 | Fish, Whales, Crustaceans, Mollusks | 661 | 78 |
| 14 | Edible Fats and Oils | 684 | 77 |
| 15 | Cereals and Cereal Products | 714 | 150 |
| 16 | Legumes | 790 | 58 |
| 17 | Vegetables and Vegetable Products | 814 | 73 |
| 18 | Fruits and Fruit Products | 851 | 124 |
| 19 | Sugars, Sugar Alcohols and Honey | 906 | 93 |
| 20 | Alcoholic Beverages | 936 | 140 |
| 21 | Coffee, Tea, Cocoa | 982 | 106 |
| 22 | Spices, Salt and Vinegar | 1015 | 42 |
| 23 | Drinking Water, Mineral and Table Water | 1030 | 9 |

## 2. 研发问题入口

### 2.1 水分与保藏

- 先查 `water activity`、`moisture sorption`、`shelf life`。
- 入口：p.3–5（PDF 47–49）。
- 用途：理解水分活度、保藏稳定性、非酶褐变和脂质氧化的相对关系。
- 不要从一页表值直接推出“某种食品在家庭冰箱能放几天”。

### 2.2 蛋白质变性与持水

- 先查 `protein`、`denaturation`、`gelation`、`muscle protein`。
- 入口：第 1 章（PDF 52 起）；肉类 PDF 607 起；具体肌肉蛋白 PDF 654。
- 用途：解释加热后收缩、持水变化、凝胶与质地。
- 书中的温度/时间要连同样品体系引用，不能直接变成禽肉中心温度。

### 2.3 淀粉糊化与老化

- 先查 `gelatinization`、`starch`、`amylose`、`amylopectin`。
- 入口：第 4 章（PDF 292 起）；糊化 PDF 361；表/曲线 PDF 363–364；谷物章 PDF 714 起。
- 用途：解释增稠、颗粒膨胀、冷却后的结构变化。
- 已知限制：`Retrogradation` 未稳定成为独立主题标题，需用全文检索补查，不能宣称索引已完整覆盖。

### 2.4 美拉德反应与褐变

- 先查 `Maillard`、`Amadori`、`melanoidin`、`browning`。
- 入口：p.271（PDF 315）；抑制 p.289（PDF 333）。
- 用途：解释还原糖与氨基化合物的反应、褐色产物和香气物质。
- “褐变好看/好闻”不是无条件结论；反应也可能产生不需要的颜色和风味。

### 2.5 脂质氧化与异味

- 先查 `lipid`、`autoxidation`、`peroxidation`、`hydroperoxide`、`antioxidant`。
- 入口：第 3 章（PDF 202 起）；过氧化 p.191（PDF 235）；抑制 p.214（PDF 258）。
- 用途：解释油脂酸败、加热和储存中的氧化路径。
- 不能把实验室抗氧化数据直接当作人体健康结论。

### 2.6 香气与风味

- 先查 `aroma`、`odor`、`threshold`、`aroma value`、`impact compound`。
- 入口：第 5 章（PDF 384 起）；具体香气化合物 PDF 407 起。
- 用途：区分“有挥发性物质”和“对气味有贡献”；理解阈值、基质和香气分析。
- 不能用单个化合物名称替代整道菜的感官评价。

### 2.7 乳、蛋、肉、鱼

- 乳：PDF 542 起；蛋：PDF 590 起；肉：PDF 607 起；鱼贝：PDF 661 起。
- 先查具体蛋白、脂质、酶和加工小节，再回到原料书籍找烹饪应用。
- 食材的食品安全结论必须另查现行权威资料；本书 2009 年版不充当现行限量标准。

## 3. 检索命令

```bash
python scripts/search.py --chemistry "water activity" --top 10
python scripts/search.py --chemistry "gelatinization" --top 10
python scripts/search.py --chemistry "Maillard" --top 10
python scripts/search.py --chemistry "peroxidation" --top 10
python scripts/search.py --chemistry "aroma value" --top 10
python scripts/search.py "retrogradation starch" --source FC-BELITZ-2009 --top 10
```

## 4. 读结果的顺序

1. 主题索引给出章节与大致入口。
2. 普通检索找正文中的具体机制词。
3. `--page` 打开整页，确认条件、样品、温度、单位和否定词。
4. 需要烹饪应用时，再交叉引用《食物与厨艺》或《烹饪原料学》。
5. 写结论时说明“书本机制”“跨来源推理”还是“待验证假设”。

## 5. 缺口

- 索引不是全书逐句语义标注。
- 部分小节没有被独立标题捕获，需全文检索。
- 图表和化学结构没有被转成可计算数据。
- 书籍年代为 2009，不能代替现行法规与安全评估。

