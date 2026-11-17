# 十书检索指南

## 1. 基本命令

在 Skill 根目录执行：

```bash
python scripts/search.py "花椒 温中止痛" --top 8
python scripts/search.py "西红柿" --mode semantic --top 8
python scripts/search.py "淀粉 糊化 酱汁" --source MCG-V1-2013
python scripts/search.py "Maillard reaction" --source FC-BELITZ-2009
python scripts/search.py --pairing BASIL --top 20
python scripts/search.py --chemistry "water activity" --top 10
python scripts/search.py --herb 花椒
python scripts/search.py --page FB-PAGE-2008:73
```

## 2. 过滤参数

| 参数 | 作用 |
|---|---|
| `--top` | 返回条数，默认 8 |
| `--source` | 限定单本：十书任一 `source_id` |
| `--sources` | 列出全部来源及页数/片段数 |
| `--series` | 限定丛书，如 `食物与厨艺` |
| `--volume` | 限定卷册，如 `1` / `2` / `3` |
| `--domain` | 限定知识域，如 `food-chemistry`、`flavor-pairing` |
| `--chapter` | 限定章节字符串 |
| `--phase` | 限定 `1` 或 `2` |
| `--mode keyword` | 所有词都要命中，精度高 |
| `--mode semantic` | 任一词命中 + n-gram 重排，召回高 |
| `--content-type` | `text` / `recipe` / `attribute` / `heading` |
| `--page-kind` | `content` / `front_matter_or_appendix` |
| `--pairing` | 列出一个食材的搭配 |
| `--pair` | 精确查两个食材的关系 |
| `--chemistry` | 查化学主题标题索引 |
| `--json` | 机器可读输出 |

## 3. 十本书的检索策略

### 食材基础与本草

```bash
python scripts/search.py "花椒 性味 归经 功效" --source MM-ZYX-2016
python scripts/search.py "花椒 产地 品质 选购" --source CN-DIDAO-2011
python scripts/search.py --herb 花椒
```

### 盐、脂、酸、热

```bash
python scripts/search.py "盐 渗透 扩散" --source FS-SFAH-2023
python scripts/search.py "脂肪 香气 乳化" --source FS-SFAH-2023
python scripts/search.py "酸 平衡" --source FS-SFAH-2023
python scripts/search.py "热 传导 对流 辐射" --source FS-SFAH-2023
```

### 《食物与厨艺》三册

```bash
python scripts/search.py "面团 面筋 淀粉" --source MCG-V1-2013
python scripts/search.py "酱汁 增稠 乳化" --source MCG-V1-2013
python scripts/search.py "果实 成熟 香气" --source MCG-V2-2013
python scripts/search.py "香草 香料" --source MCG-V2-2013
python scripts/search.py "肌肉 蛋白质 加热" --source MCG-V3-2013
python scripts/search.py "乳 蛋 肉类 海鲜" --series 食物与厨艺 --volume 3
```

### 食品化学

```bash
python scripts/search.py --chemistry "gelatinization" --top 10
python scripts/search.py --chemistry "Maillard" --top 10
python scripts/search.py "lipid peroxidation" --source FC-BELITZ-2009
python scripts/search.py "aroma compounds" --source FC-BELITZ-2009
python scripts/search.py "water activity" --source FC-BELITZ-2009
```

### 风味搭配

```bash
python scripts/search.py --pairing BASIL --top 30
python scripts/search.py --pair BASIL TOMATOES
python scripts/search.py "basil peaches" --source FB-PAGE-2008
python scripts/search.py --page FB-PAGE-2008:73
```

### 烹饪原料

```bash
python scripts/search.py "烹饪原料 分类" --source CR-WXY-2003
python scripts/search.py "品质检验 保藏" --source CR-WXY-2003
python scripts/search.py "蔬菜 畜禽 蛋乳" --source CR-WXY-2003
```

## 4. 归一化与别名

1. 先查 `config/ingredient_lexicon.json`。
2. 用 canonical 与别名各检一次。
3. 中文别名（西红柿/番茄、土豆/马铃薯）走别名扩展。
4. 英文条目受大小写、单复数和 OCR 噪声影响；可改用词根或普通全文检索。
5. 检索不到时，不直接断言“书里没有”；先查别名、上位词、下位词、章节词和相邻页。

### 中文专业词的英文桥接

`config/professional_terms.json` 只保存检索提示，不是事实依据。`search.py` 会把少量中文专业词扩展为英文补充查询，以便同时命中 *Food Chemistry*、*The Flavor Bible* 等英文来源；原中文查询仍会并行执行，不会被替换。

```bash
python scripts/search.py "蛋白质变性 持水性" --source FC-BELITZ-2009
python scripts/search.py "淀粉糊化" --source FC-BELITZ-2009
python scripts/search.py "水分活度" --source FC-BELITZ-2009
python scripts/search.py "美拉德反应" --source FC-BELITZ-2009
```

英文扩展只改变召回范围；回答中的机制、温度、数值和条件仍必须回查原文页。未收录在 `professional_terms.json` 的词按原查询处理，不得凭模型记忆擅自翻译成“书里的事实”。

## 5. 读结果

每条结果通常包含：

```text
[1] 《食物与厨艺：奶·蛋·肉·鱼》p.346（PDF 348）· 肉类 · text · conf=medium
    （证据摘要）
    score=12.5 exact=4 sem=0.0
```

- `citation` 可直接用于回答，但必须先回页确认。
- `chapter/section` 用于定位；章节缺失时不要补造。
- `content_type` 表示片段类型，不是学科证据等级。
- `conf` 是抽取置信度，不是事实真伪或科学强度。
- `score` 是排序分，不是“更正确”。
- `exact` 是命中数，`sem` 是字符相似度。

## 6. 回溯

```bash
python scripts/search.py --page MM-ZYX-2016:396
python scripts/search.py --page FC-BELITZ-2009:315
python scripts/search.py --page MCG-V3-2013:348
python scripts/search.py --page FB-PAGE-2008:73
python scripts/search.py --page CR-WXY-2003:77
```

写关键结论前，至少检查：

- 整页主题是否与问题一致；
- 否定词、条件从句、单位是否被 OCR 破坏；
- `printed_page` 是否来自该页实际观察；
- 是否混用了相邻页或另一卷册。

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| 搜不到 | 换别名、章节词、英文术语；确认书是否覆盖 |
| 结果太多 | 加 `--source`、`--chapter`、`--mode keyword` |
| 结果不相关 | 改具体术语；用 `--chemistry` / `--pairing` 专用索引 |
| OCR 错字 | 回看原页；不要用错字当检索词 |
| 页码是 null | 该书无可观察印刷页，引用 PDF 页 |
| 搭配索引有怪词 | 查 `data/flavor_review_queue.jsonl`，不要直接采用 |

## 8. 不要做

- 不要把 snippet 当完整原文。
- 不要用排序分证明事实正确。
- 不要跨书拼成一句“原文”。
- 不要把 `query_hint` 或别名当书里的原话。
- 不要把 Food Chemistry 2009 当现行法规。
- 不要把 The Flavor Bible 的搭配当科学验证或健康建议。

