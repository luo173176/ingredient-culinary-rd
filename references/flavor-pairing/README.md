# Flavor Pairing Engine 参考

> `source_id`: `FB-PAGE-2008`  
> 书目：Karen Page, Andrew Dornenburg, *The Flavor Bible*, 2008.

## 1. 定位

The Flavor Bible 是按食材字母顺序组织的**创意搭配参考**。它不是经过统一感官实验验证的相容性数据库，也不是营养、药理或食品安全数据库。

本模块把书中的直接搭配条目和 Flavor Affinities 组合拆成可检索记录，用于：

- 查某食材在书中与哪些食材、香草、香料、菜品类型同列；
- 追溯搭配词所在的 PDF 页与印刷页；
- 区分“书中明确列出”“由组合条目拆出”“AI 自己提出”三种情况；
- 为菜谱研发提供候选，而不是直接下“好吃”结论。

## 2. 当前索引

| 指标 | 实际值 |
|---|---:|
| 处理页数 | 391 |
| 识别条目 | 640 |
| 有识别条目的页 | 259 |
| JSONL 原始搭配记录 | 14,090 |
| 其中直接列出 | 13,503 |
| 其中由 affinity 组合拆出（原始） | 587 |
| Flavor Affinities 组合 | 292 |
| 人工复核队列 | 6,905 |
| 强标记候选 | 493 |
| SQLite 去重后搭配 | 13,758 |
| 去重后直接列出 | 13,503 |
| 去重后组合推导 | 255 |

**为什么有两个总数？** JSONL 保留原始抽取记录，便于审计；SQLite 以 `pairing_id` 为主键去重，因此有 332 条组合推导记录被合并。报告中必须同时写 raw 与 DB 口径，不能只挑一个数字。

## 3. 证据等级

| `evidence_level` | 含义 | 可否写成“书中搭配” |
|---|---|---|
| `explicit_pairing_listing` | 某食材条目直接列出的搭配词 | 可以，附页码与原文上下文 |
| `explicit_affinity_combination` | 书中一条 affinity 明确列出的组合整体 | 可以，说明是组合而非二元条目 |
| `derived_from_affinity_combination` | 把一条组合拆成两两关系 | 只能写“由书中组合拆出的关系” |
| `ai_hypothesis` | 索引或 AI 为研发新增的组合 | 绝对不能说成书中原文 |

数据库目前有前两类直接条目和第三类推导条目；`ai_hypothesis` 是输出时的保留等级，不是书籍证据。

## 4. 已核对示例（页码与条目位置核对，不是感官验证）

### BASIL

- 条目在 p.58（PDF 73），续页到 p.59（PDF 74）。
- 直接列出 GARLIC、OLIVE OIL、TOMATOES、peaches、nectarines、raspberries 等。
- 可作为“书中明确支持”的搭配；具体比例、加热方式和食材成熟度仍需设计。

### CHICKEN

- 条目在 p.115（PDF 130）。
- 条目列出多种香草、香料、蔬菜和菜品类型；可用于生成搭配候选。
- 不能因为同列的词很多，就推断它们在同一道菜里一定和谐。

### BANANAS

- 条目在 p.56（PDF 71）。
- 列出 CARAMEL、VANILLA、CHOCOLATE、CREAM AND ICE CREAM 等甜点方向搭配。
- “甜香叠加”属于机制解释或跨来源推理，不是书本给出的实验结论。

## 5. 检索

```bash
python scripts/search.py --pairing BASIL --top 20
python scripts/search.py --pairing CHICKEN --top 20
python scripts/search.py --pair BASIL TOMATOES
python scripts/search.py "basil peaches" --source FB-PAGE-2008
python scripts/search.py --page FB-PAGE-2008:73
```

`--pair` 只做规范化的精确匹配；没有命中不等于书中没有关系。可以：

1. 查单侧 `--pairing` 列表；
2. 用普通全文检索查两个词；
3. 打开条目页看上下文；
4. 在 `data/flavor_review_queue.jsonl` 里查被过滤的候选。

## 6. 输出规则

### A. 书籍明确支持

```text
[原文] 《The Flavor Bible》p.58（PDF 73），BASIL 条目直接列出 TOMATOES、GARLIC、OLIVE OIL。
```

### B. 根据书籍信息推理

```text
[跨来源推理] BASIL 条目列出 peaches、raspberries 等水果；《Food Chemistry》
关于香气与基质的章节说明香气感知受基质影响。因此可提出“罗勒 + 核果”
的清爽方向，但比例和温度仍需试验。
```

### C. AI 创新

```text
[创新假设] 罗勒 + 未在书中列出的某水果，属于待验证组合；不得写成
“Flavor Bible 推荐”。需设置对照、固定成熟度并做盲评。
```

## 7. 已知误差

- 三栏版面在文本层中可能交错，条目名和搭配词会串行。
- 已观察到 `LO BSTER`、`ROseMARY`、`SUI`、`combine hamachi...` 等噪声。
- 菜名、厨师语录、菜品描述可能被误识别为食材。
- 大小写、单复数和别名没有完全统一；`BASIL` 与 `basil` 在当前表中可能分开。
- `strong_marker` 只是“大写/粗体/星号候选”，不是人工确认的“主推荐”。
- 6,905 条复核队列必须保留，不能为了数量把噪声当成知识。

## 8. 安全与科学边界

- 搭配关系不等于营养协同、药理协同或安全性保证。
- 不能把“书中同列”解释为“可以大量同食”。
- 过敏原、药物相互作用、妊娠与疾病风险必须另查适用的安全来源；十书没有覆盖时写缺口。
- 没有做感官实验时，不得写“验证过”“最佳比例”“消费者都喜欢”。

