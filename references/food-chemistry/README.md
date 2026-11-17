# 食品化学研究参考

> `source_id`: `FC-BELITZ-2009`  
> 书目：H.-D. Belitz, W. Grosch, P. Schieberle, *Food Chemistry*, 4th revised and extended edition, Springer, 2009.

## 1. 这个模块能做什么

它把书中的章节、主题标题、页码和原文页组织成可检索的食品化学索引，用于：

1. 找到蛋白质、脂质、碳水化合物、酶、香气、色素和食品加工反应的原书入口。
2. 解释烹饪现象背后的化学机制，而不是只给操作步骤。
3. 为配方研发提出有来源的机制假设。
4. 回到原页核对实验条件、数值和术语。

它**不是**一张“把任何食材输入后自动输出完整化学成分”的表，也不是现行食品安全标准数据库。

## 2. 覆盖范围

| 指标 | 实际值 |
|---|---:|
| PDF 页记录 | 1,114 |
| 知识片段 | 1,112 |
| 章节 | 24 |
| 化学主题索引 | 2,319 |
| 有主题索引的页 | 863 |
| 印刷页与 PDF 页偏移 | 通常为 44（p.1 = PDF 45） |

24 章覆盖水、蛋白质、酶、脂质、碳水化合物、香气、维生素、矿物质、添加剂、污染物、乳、蛋、肉、鱼、食用油脂、谷物、豆类、蔬菜、水果、糖与蜂蜜、酒精饮料、咖啡茶可可、香料盐醋、饮用水。

## 3. 索引结构

`data/chemistry_topics.jsonl` 与 SQLite `chemistry_topics` 表保存：

| 字段 | 含义 |
|---|---|
| `topic_id` | 主题记录 ID |
| `chapter` / `section` | 书内章节标题与子标题 |
| `topic` | 可检索的化学主题名 |
| `source_id` | 固定为 `FC-BELITZ-2009` |
| `printed_page` / `pdf_page` | 两套页码，不混用 |
| `evidence_quote` | 页面标题或上下文短语，不是完整摘要 |
| `keywords` | 检索关键词 |
| `confidence` | 结构抽取置信度 |

主题索引主要来自章节标题和明确的化学术语，属于“定位工具”，没有把每页正文自动改写成完整语义摘要。因此：**找到主题页 ≠ 已读懂整页；必须打开页记录。**

## 4. 常用检索入口

```bash
python scripts/search.py --chemistry "water activity" --top 8
python scripts/search.py --chemistry "Maillard" --top 8
python scripts/search.py "starch gelatinization" --source FC-BELITZ-2009
python scripts/search.py "lipid peroxidation" --source FC-BELITZ-2009
python scripts/search.py "aroma compounds" --source FC-BELITZ-2009
python scripts/search.py --page FC-BELITZ-2009:315
```

也可以用 `search.py` 的普通全文检索查中文或英文术语；主题索引适合精确定位章节，普通检索适合找正文解释。

## 5. 已核对的机制入口

以下页码是索引和页记录中实际存在的入口，不是凭记忆写出的引用：

| 主题 | 位置 | 用途 |
|---|---|---|
| 水分活度 | p.4（PDF 48） | 水分、保藏、反应速率与微生物生长的关系 |
| 蛋白质 | 第 1 章，PDF 52 起 | 氨基酸、肽、蛋白质结构与功能 |
| 脂质 | 第 3 章，PDF 202 起 | 脂质分类、氧化与风味 |
| 脂质过氧化 | p.191（PDF 235） | 不饱和脂质的过氧化 |
| 抑制脂质过氧化 | p.214（PDF 258） | 抗氧化与抑制路径 |
| 碳水化合物 | 第 4 章，PDF 292 起 | 单糖、多糖、淀粉与反应 |
| 美拉德反应初始阶段 | p.271（PDF 315） | 还原糖与氨基化合物的早期反应 |
| 美拉德反应抑制 | p.289（PDF 333） | 影响褐变与香气形成的条件 |
| 淀粉糊化 | p.317（PDF 361） | 淀粉颗粒吸水、膨胀与增稠 |
| 糊化温度表/曲线 | p.319–320（PDF 363–364） | 需要回看原表，不能只记一个温度 |
| 香气化合物 | 第 5 章，PDF 384 起 | 香气物质、气味值、香气分析 |
| 肉类与肌肉蛋白 | p.610（PDF 654） | 肉的结构、蛋白质与持水/加热 |

## 6. 如何在研发中使用

1. **先提问题，再查机制**：例如“面糊为什么变稠”先查 gelatinization，而不是先猜加多少淀粉。
2. **区分机制与参数**：书中的实验条件、温度、浓度和样品体系必须一起引用；不能把实验室条件直接说成家用配方。
3. **用原文页核对数值**：主题表只用于定位，具体数值回到 `pdf_page`。
4. **把推断写清楚**：从机制推出烹饪动作时标 `[跨来源推理]`；没有做实验时标 `[创新假设]`。
5. **安全性单独处理**：2009 年版不提供当前法规限量、过敏原清单或最新风险评估。

## 7. 引用格式

```text
[E1] Food Chemistry (Belitz et al., 4th ed., 2009) p.271（PDF 315），
     4 Carbohydrates / 4.2.4.4.1 Initial Phase of the Maillard Reaction。
[E2] Food Chemistry (Belitz et al., 4th ed., 2009) p.317（PDF 361），
     4 Carbohydrates / Gelatinization。
```

没有观察到印刷页时只写 `PDF xxx`；有 `printed_page` 时同时写两者。

## 8. 边界

- 出版年是 2009；不能把它称为最新版或现行食品安全标准。
- 书中的实验数据有特定样品、方法和条件，不能无条件推广。
- 食品化学机制不等于临床营养或医疗结论。
- 索引来自标题和术语抽取，可能漏掉 `Retrogradation` 等未以独立标题出现的主题；遇到缺口应回到全文检索。
- 没有真实实验数据时，不得声称某个配方已经验证。

