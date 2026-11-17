# 十书知识库覆盖与口径

> 统计日期：2026-11-17（Asia/Shanghai）。数字来自实际生成物，不是估算。
> 重新生成：`python scripts/validate_kb.py`（刷新 `data/manifest.json`）。

## 1. 页级解析

| source_id | PDF 页 | 有文本页（≥20 字符） | 近空页（<20 字符） | 页级低置信 | 知识片段 |
|---|---:|---:|---:|---:|---:|
| `MM-ZYX-2016` | 841 | 832 | 9 | 0 | 856 |
| `CN-DIDAO-2011` | 239 | 239 | 0 | 8 | 240 |
| `FS-SFAH-2023` | 364 | 325 | 39 | 0 | 418 |
| `DK-INGREDIENTS` | 531 | 505 | 26 | 28 | 1,075 |
| `MCG-V1-2013` | 326 | 322 | 4 | 7 | 396 |
| `MCG-V2-2013` | 363 | 361 | 2 | 30 | 408 |
| `MCG-V3-2013` | 367 | 360 | 7 | 28 | 415 |
| `FC-BELITZ-2009` | 1,114 | 1,112 | 2 | 0 | 1,112 |
| `FB-PAGE-2008` | 391 | 376 | 15 | 0 | 1,289 |
| `CR-WXY-2003` | 244 | 244 | 0 | 2 | 447 |
| **合计** | **4,780** | **4,676** | **104** | **103** | **6,656** |

第一阶段合计：1,975 页 / 2,589 片段。  
第二阶段合计：2,805 页 / 4,067 片段。

说明：

- “近空页”不等于“解析失败”；多数是章节扉页、整页图片、版权页或扫描留白。
- 失败页单独记录在 `data/ocr/<source>/failures.jsonl`；本次扫描书硬失败均为 0。
- 页级低置信与片段级低置信不是同一口径。片段级低置信数：

```text
MCG-V1-2013  35
MCG-V2-2013 205
MCG-V3-2013 163
CR-WXY-2003  13
```

- 页级记录保留 `text`、`printed_page`、`printed_page_raw`、`method`、`mean_score`、`low_confidence_lines`、`layout`、`warnings`。
- 数字版 PDF 的近空页主要是章节分隔与插图页。

## 2. 结构化本草

| 指标 | 数量 |
|---|---:|
| 目录定位条目总数 | 558 |
| 主条目（`is_attached=false`） | 434 |
| 附药（`is_attached=true`） | 124 |
| 解析出功效字段的条目 | 436（434 主条目 + 2 附药） |
| 主条目中解析出功效/应用/用法 | 434 / 434 / 434 |
| 主条目高置信 | 432 |
| 主条目中置信（缺“药性”字段） | 2（苏木、旋覆花） |

口径说明：

- 总记录 558 条（434 主条目 + 124 附药），其中 436 条有功效字段。
- 附药多为短段落，常无独立【功效】【应用】【用法用量】字段。
- 结构化字段来自目录定位 + 正则解析，不等同于人工逐条校对。
- 具体药性、剂量、禁忌引用前必须回查原页。

## 3. 食材卡

| 阶段 | 数量 | 位置 | 状态 |
|---|---:|---|---|
| 第一阶段 | 12 | `data/ingredients/` | partial/结构化 |
| 第二阶段 | 6 | `data/ingredients-phase2/` | 全部 `partial` |
| **合计** | **18** | | |

第二阶段六张卡：罗勒、鸡、小麦面粉、蛋、乳、鲑鱼。  
所有卡通过 `schemas/ingredient.schema.json`；空字段表示知识库缺口，不是“已研究但省略”。

## 4. 检索索引

| 表 | 行数 | 说明 |
|---|---:|---|
| `sources` | 10 | 十本书元数据 |
| `pages` | 4,780 | 页级记录 |
| `chunks` | 6,656 | 页内知识片段 |
| `chunks_fts` | 6,656 | FTS5，与 chunks 同步 |
| `herbs` | 558 | 本草结构化记录 |
| `aliases` | 813 | 书名/别名归一化 |
| `flavor_pairings` | 13,758 | 去重后的搭配关系 |
| `flavor_affinities` | 292 | Flavor Affinities 组合 |
| `chemistry_topics` | 2,319 | Food Chemistry 主题 |
| `culinary_sections` | 154 | 十书章节结构 |
| `conflict_candidates` | 2 | 跨来源并列表述的人工复核候选，不是已判定冲突 |

Flavor Pairing 还有两套原始口径：

- JSONL 原始 14,090 条（13,503 direct + 587 derived）。
- SQLite 去重 13,758 条（13,503 direct + 255 derived）。
- 差异来自 332 条重复 `pairing_id` 被主键合并。

## 5. 参考卡

| 类型 | 数量 | 位置 |
|---|---:|---|
| 本草主题卡 | 8 | `references/materia-medica/topics/` |
| 本草单药卡 | 41 | `references/materia-medica/herbs/` |
| 本草全量索引 | 1 | `references/materia-medica/herb-index.md`（434 主条目） |
| 中国食材卡 | 8 | `references/chinese-ingredients/ingredients/` |
| 全球食材卡 | 4 | `references/global-ingredients/ingredients/` |
| 风味科学卡 | 5 + README | `references/flavor-science/` |
| 食品化学参考 | 3 | `references/food-chemistry/` |
| 风味搭配参考 | 3 | `references/flavor-pairing/` |
| 烹饪原料学参考 | 1 | `references/culinary-ingredients/README.md` |
| 食物与厨艺参考 | 1 | `references/food-and-cooking/README.md` |

## 6. 图像、整页扫描与表格候选

| 类型 | 数量 | 说明 |
|---|---:|---|
| 视觉记录总数 | 6,811 | `data/images/manifest.jsonl` |
| 内容图片 | 2,913 | 页内嵌图/xref 记录 |
| 整页扫描 | 2,392 | 整页图像记录，不等于独立食材照片 |
| 表格候选 | 1,506 | PyMuPDF 文本/线框启发式，不是已解析表格 |

分书统计：

| source_id | 内容图片 | 整页扫描 | 表格候选 |
|---|---:|---:|---:|
| `MM-ZYX-2016` | 42 | 0 | 21 |
| `CN-DIDAO-2011` | 119 | 239 | 0 |
| `FS-SFAH-2023` | 192 | 0 | 9 |
| `DK-INGREDIENTS` | 0 | 530 | 0 |
| `MCG-V1-2013` | 0 | 652 | 0 |
| `MCG-V2-2013` | 161 | 363 | 0 |
| `MCG-V3-2013` | 112 | 365 | 0 |
| `FC-BELITZ-2009` | 1,448 | 0 | 1,100 |
| `FB-PAGE-2008` | 839 | 0 | 376 |
| `CR-WXY-2003` | 0 | 243 | 0 |

注意：

- 整页扫描记录数可以超过 PDF 页数（例如 MCG-V1 326 页产生 652 个全页图像 xref），因为一页可能有多个全页图像对象。不能把记录数当页数。
- `caption_candidate` 是邻近文字候选，全部标记待人工复核。
- `table_candidate` 是文本/线框启发式，不是单元格级表格解析。
- 没有提取或再分发整页图片。
- Flavor Bible 有 25 条条目的 `printed_page` 与全书主流偏移明显不一致（涉及 12 个 PDF 页）；引用时优先核对 PDF 页与原页页眉。

## 7. 没有覆盖的部分

- **不等于整本书都被“理解”**：页级检索覆盖全书，但人工精编卡片只覆盖少量高频食材/药材。
- 图片、图注、表格结构只保留页码、位置、xref/bbox 与邻近文字候选；复杂图注仍需人工审核。
- 未做神经语义向量检索；当前是 FTS5 + 字符 n-gram 重排 + 中文子串回退 + 少量专业词英译检索桥接（`config/professional_terms.json`）。
- 未做真实烹饪实验；所有“预期风味”只能标为假设。
- `scripts/build_conflict_candidates.py` 只把同一知识域中不同来源的并列表述送入复核队列；当前 2 条候选均为互补/不同处理维度，尚未确认任何真冲突。
- 十书未覆盖的现代营养、毒理、临床证据、食品添加剂限量和现行法规，统一标：

> 当前十书知识库暂无充分依据。

