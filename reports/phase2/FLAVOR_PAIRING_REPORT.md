# Phase 2 风味搭配索引报告

**模块：Flavor Pairing Engine**  
**来源：*The Flavor Bible*（Karen Page, Andrew Dornenburg, 2008）**  
**生成日期：2026-11-17（Asia/Shanghai）**  
**结论：已建立可检索的搭配索引、affinity 组合索引和人工复核队列；它是创意参考，不是科学相容性数据库。**

---

## 1. 数据源与边界

| 项目 | 内容 |
|---|---|
| `source_id` | `FB-PAGE-2008` |
| 书名 | *The Flavor Bible* |
| 作者 | Karen Page, Andrew Dornenburg |
| 出版年 | 2008 |
| PDF 页 | 391 |
| 解析方式 | PyMuPDF 文本层 + 版面重建 |
| 组织方式 | 按食材字母顺序排列的条目 + Flavor Affinities 组合 |

这本书的知识组织方式不是教材章节，而是“食材条目 + 搭配词列表 + 厨师/菜品上下文”。因此没有按固定字数切分全文，而是优先识别：

- 食材条目名；
- 条目下的搭配词；
- 大写/强标记候选；
- `+` 连接的 Flavor Affinities 组合；
- 条目所在 PDF 页与可观察印刷页；
- 邻近的菜品、菜系、厨师或餐厅上下文。

**边界：**书中“同列”不等于经过感官实验证明“相容”。搭配索引只能作为创意候选，不得推导营养协同、药理协同或食品安全保证。

---

## 2. 抽取方法

### 2.1 条目识别

从文本层中识别字母序条目名，生成 `data/flavor_entries.jsonl`。当前：

| 指标 | 数量 |
|---|---:|
| 处理页数 | 391 |
| 识别条目 | 640 |
| 有识别条目的页 | 259 |
| 带 `printed_page` 字段的条目 | 640 |

### 2.2 直接搭配

条目下的搭配词逐项写入 `flavor_pairings`，证据等级为：

```text
explicit_pairing_listing
```

这类记录表示“书中该条目直接列出了这个词”，可以写成“书中搭配”，但必须附页码与原文上下文。

### 2.3 Affinity 组合

书中用 `+` 连接的组合，例如：

```text
avocado + bacon + scallions + tomatoes
```

写入 `flavor_affinities`，共有 292 条组合。把组合拆成两两关系时，证据等级为：

```text
derived_from_affinity_combination
```

这类关系是索引推导，不得写成“书中逐字写出的二元搭配”。

### 2.4 复核队列

不符合搭配词过滤规则的候选写入 `data/flavor_review_queue.jsonl`，共 6,905 条。它们可能是：

- 菜名或菜品描述；
- 厨师语录；
- 版面串行造成的误识别；
- 大小写/单复数/别名未统一；
- 被过滤掉的短词或停用词。

复核队列保留原始上下文与页码，供人工回页判断。没有把队列里的内容直接当作知识。

---

## 3. 数量口径

必须同时保留原始 JSONL 与 SQLite 去重口径，不得只挑一个数字。

| 口径 | 总数 | 直接列出 | affinity 推导 |
|---|---:|---:|---:|
| JSONL 原始记录 | 14,090 | 13,503 | 587 |
| SQLite 去重后 | 13,758 | 13,503 | 255 |
| 差异 | 332 | 0 | 332 |

差异原因：`pairing_id` 作为 SQLite 主键，332 条重复的 affinity 推导记录被合并。原始 JSONL 保留全部记录，便于审计。

其他指标：

| 指标 | 数量 |
|---|---:|
| Flavor Affinities 组合 | 292 |
| 人工复核队列 | 6,905 |
| 强标记候选 | 493 |
| 数据库中的 `explicit_affinity_combination` 行 | 0 |
| 数据库中的 self-pair 噪声 | 5 |

`strong_marker` 只是大写、粗体或星号候选，不是人工确认的“主推荐”。

---

## 4. 证据等级

| `evidence_level` | 含义 | 可写成什么 | 不得写成什么 |
|---|---|---|---|
| `explicit_pairing_listing` | 条目直接列出搭配词 | “书中该条目列出 X” | “科学实验证明 X 与 Y 相容” |
| `explicit_affinity_combination` | 书中一条组合整体 | “书中给出组合 X + Y + Z” | “每两个两两搭配都经过验证” |
| `derived_from_affinity_combination` | 从组合拆出的两两关系 | “由书中组合拆出的关系” | “书中逐字写出的二元搭配” |
| `ai_hypothesis` | AI 为研发提出的新组合 | “待验证假设” | “Flavor Bible 推荐” |

当前数据库只有前两类直接条目和第三类推导条目；`ai_hypothesis` 是输出层保留等级，不是书籍证据。

---

## 5. 已核对示例

以下示例只核对“页码与条目位置”，不是感官验证。

### 5.1 BASIL

- 条目在 p.58（PDF 73），续页到 p.59（PDF 74）。
- PDF 73 直接列出 `GARLIC`、`OLIVE OIL` 等。
- PDF 74 的续页列出 `TOMATOES and tomato sauces`；文本层将 `TOMATOES` 识别成带噪声的 `,~iOMATOES`，因此数据库中的写法保留了噪声，但原页上下文可以确认番茄方向。
- 这些可以标为 `explicit_pairing_listing`；比例、成熟度和加热方式仍需设计。

### 5.2 TARRAGON → CHICKEN

- `TARRAGON` 条目在 p.342（PDF 358）直接列出 `CHICKEN`。
- 这是明确的书籍搭配记录，可用于烤鸡的香草方向。
- 早期 `chicken.json` 曾把 `CHICKEN + ROSEMARY` 写成书中搭配，但 PDF 130 的 CHICKEN 条目没有直接列出 rosemary；该条已移除。E26/E27 已改用本条可核验的 `TARRAGON + CHICKEN`。

### 5.3 CHICKEN

- 条目在 p.115（PDF 130）。
- 条目列出多种香草、香料、蔬菜、酱汁和菜品类型，其中包括 `GARLIC`、`BASIL`、`thyme`、`fines herbes` 等。
- 不得因为同列词很多，就推断它们在同一道菜里一定和谐。
- 不得用 CHICKEN 条目反推所有“鸡肉 + 香草”组合都成立。

### 5.4 BANANAS

- 条目在 p.56（PDF 71），续页到 p.57（PDF 72）。
- 直接列出 `CARAMEL`、`CHOCOLATE`、`VANILLA` 等甜点方向搭配。
- “甜香叠加”属于机制解释或跨来源推理，不是书本给出的实验结论。

### 5.5 Flavor Affinities 示例

```text
AVOCADOS: avocado + bacon + scallions + tomatoes
AVOCADOS: avocado + basil + red onions + tomatoes + balsamic vinegar
AVOCADOS: avocado + cilantro + lime juice
```

这些是书中组合整体，可以拆出两两关系并标 `derived_from_affinity_combination`；不得把拆出的每一对都写成书中逐字列出的搭配。

---

## 6. 检索与调用

### 6.1 专用命令

```powershell
python scripts\search.py --pairing BASIL --top 20
python scripts\search.py --pairing CHICKEN --top 20
python scripts\search.py --pair BASIL TOMATOES
python scripts\search.py --pair TARRAGON CHICKEN
python scripts\search.py "basil peaches" --source FB-PAGE-2008
python scripts\search.py --page FB-PAGE-2008:73
```

`--pair` 只做规范化精确匹配；没有命中不等于书中没有关系。可以改查单侧 `--pairing`、普通全文检索、条目页上下文，或复核队列。

### 6.2 输出三层

**A. 书籍明确支持**

```text
[原文] 《The Flavor Bible》p.342（PDF 358），TARRAGON 条目直接列出 CHICKEN。
```

**B. 根据书籍信息推理**

```text
[跨来源推理] BASIL 条目列出 peaches、raspberries 等水果；食品化学关于香气与基质的章节
说明香气感知受基质影响。因此可以提出“罗勒 + 核果”的清爽方向，但比例和温度仍需试验。
```

**C. AI 创新**

```text
[创新假设] 罗勒 + 未在书中列出的某水果，属于待验证组合；不得写成
“Flavor Bible 推荐”。需要设置对照、固定成熟度并做盲评。
```

---

## 7. 与菜谱研发的接口

菜谱研发使用 Flavor Bible 时，按以下顺序：

1. 先查主食材条目的直接搭配；
2. 再查辅食材反向条目，确认关系是否双向出现；
3. 查 affinity 组合，寻找多食材结构；
4. 回页核对原文、否定词、版面串行和页码；
5. 把“书中明确支持”“跨来源推理”“AI 假设”分开；
6. 设计比例、温度、时间和质地，不把搭配词直接当成配方。

搭配不决定用量。书中给出“BASIL + TOMATOES”不等于给出罗勒与番茄的比例、盐度、酸度或加热时间。

---

## 8. 质量检查

### 8.1 自动检查

`tests/test_flavor_pairings.py` 覆盖：

- 原始 JSONL 与统计文件一致；
- SQLite 去重数量与证据等级；
- 搭配记录 Schema 与必填字段；
- 已验证示例（BASIL、CHICKEN、BANANAS、strong marker）。

当前 pytest 结果：58 passed。相关测试没有失败。

### 8.2 评测

风味搭配组 E21–E25 自动得分 450/450：

| 用例 | 主题 | 自动分 |
|---|---|---:|
| E21 | 罗勒与番茄、蒜、橄榄油 | 90 |
| E22 | 鸡肉与龙蒿、蒜 | 90 |
| E23 | 香蕉、焦糖、香草 | 90 |
| E24 | 罗勒与水果的创新假设 | 90 |
| E25 | 三种证据等级 | 90 |

自动评测验证检索命中、引用页码、关键词、缺口与安全话术；专业正确性 10 分/例仍为人工待评。

---

## 9. 已知问题

1. **三栏串行**：文本层中条目名与搭配词会交错，导致条目名变形或搭配词混入菜名。
2. **OCR 式噪声**：如 `LO BSTER`、`ROseMARY`、`SUI`、`JngelicJ` 等；不得直接当标准食材名。
3. **印刷页异常**：640 条条目中 25 条记录的 `printed_page` 与全书主流偏移明显不一致，涉及 12 个 PDF 页；例如 PDF 45 被标成印刷页 235。引用时应优先核对 PDF 页与原页页眉。
4. **self-pair**：数据库有 5 条 `X + X` 噪声（如 `MINT + MINT`），不得当作真实搭配。
5. **强标记未确认**：493 条 strong marker 只是格式候选，不是人工确认的主推荐。
6. **复核队列未清空**：6,905 条候选尚未逐条人工处理。
7. **组合拆分有限**：affinity 组合拆出的两两关系只覆盖 255 条去重记录，不得代表全书所有多食材关系。
8. **不是科学数据库**：没有统一感官实验、阈值测定或消费者接受度数据。

---

## 10. 下一步建议

1. 对 6,905 条复核队列做分层抽样，先清理高频食材与经典搭配。
2. 为每条搭配增加 `review_status` 与 `reviewer_note`，区分“机器候选”“人工确认”“人工否决”。
3. 对 12 个印刷页异常页面逐页回看 PDF 图像，修正或清空 `printed_page`。
4. 建立别名归一化表，统一 `BASIL` / `basil`、单复数、带修饰词的条目。
5. 在不引入向量库的前提下，先做搭配同义词与菜系词表，提高召回。
6. 设计小规模感官试验：固定食材品种、成熟度、比例和温度，做对照与盲评；没有数据前继续标“未验证”。

---

## 11. 结论

Flavor Pairing Engine 已能回答：

- 书中是否直接记录某两个食材的搭配；
- 某条目下有哪些搭配方向；
- 某条关系是直接列出还是 affinity 推导；
- 某个组合是否有原页可回溯；
- 哪些组合只是 AI 假设。

它不得回答：

- 某搭配是否经过感官实验证明；
- 某比例是否最好吃；
- 某组合是否有营养协同或药理协同；
- 某搭配对所有人都安全。

**最终定位：可溯源的创意搭配候选库，不是科学相容性数据库，也不是菜谱验证报告。**
