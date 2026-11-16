# 全球食材（DK）· 卡片索引

> 来源：《食材百科全书》（英国DK出版社，丛龙岩译，中国轻工业出版社）。扫描版 OCR；页脚可见时保留 `p.X（PDF Y）`。

当前有 **4** 张人工校对的食材卡。DK 全书 531 个 PDF 页、1075 个知识片段；未建卡的食材请直接检索。

## 卡片

| 食材 | 英文 | 证据条数 | 主要来源 | 卡片 |
|---|---|---|---|---|
| 番茄 | tomato | 18 | DK | [ingredients/番茄.md](ingredients/番茄.md) |
| 鲷鱼 | sea bream / snapper | 18 | DK | [ingredients/鲷鱼.md](ingredients/鲷鱼.md) |
| 橄榄油 | olive oil | 18 | DK / FS | [ingredients/橄榄油.md](ingredients/橄榄油.md) |
| 黄油 | butter | 8 | DK / FS | [ingredients/黄油.md](ingredients/黄油.md) |

## 全书检索

```bash
python scripts/search.py "番茄 品种 搭配" --source DK-INGREDIENTS --top 8
python scripts/search.py "鲷鱼 替代" --source DK-INGREDIENTS --mode semantic
python scripts/search.py --page DK-INGREDIENTS:41
```

## 使用注意

1. DK 为多栏图录，OCR 可能把相邻词条串在一起；引用短句前回看页面图像。
2. 英文名/学名常被 OCR 破坏；不确定就不写学名。
3. 书中的品种、产地、季节以原书为准，不补外部资料。
4. 鱼类/贝类按题目提示过敏原、生食风险与可持续性；书中提及的才写入“原文”。
