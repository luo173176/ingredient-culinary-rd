# Phase 2 知识体系扩展报告

**项目：Ingredient Research & Culinary R&D（专业食材研究与美食研发 Skill）**  
**阶段：Phase 2 · Professional Food Science & Culinary Knowledge Expansion**  
**生成日期：2026-11-17（Asia/Shanghai）**  
**知识库版本：`ten-book-v2`**  
**结论：六份新增资料已进入统一来源层、页级索引、结构化食材模型、食品化学索引和风味搭配索引；原有四书数据与引用保持不变。**

---

## 1. 升级范围

本次升级在原有四书知识库上做增量扩展，没有重建项目，没有替换原有 `source_id`，没有覆盖第一阶段页记录、知识片段、本草结构化记录、食材卡和评测用例。

| 范围 | 内容 | 状态 |
|---|---|---|
| 原有来源 | 《中药学》《中国地道食材图录大全》《盐，脂，酸，热》《食材百科全书》 | 保留 |
| 新增来源 | 《食物与厨艺》三册、*Food Chemistry*、*The Flavor Bible*、《烹饪原料学》 | 6/6 已登记 |
| 页级记录 | 4,780 条 | 已建立 |
| 知识片段 | 6,656 条 | 已建立 |
| 本草结构化 | 558 条（434 主条目 + 124 附药） | 保持 |
| 食材卡 | 18 张（Phase 1 12 + Phase 2 6） | Phase 2 均为 `partial` |
| 食品化学主题 | 2,319 条 | 已建立 |
| 风味搭配 | SQLite 去重 13,758 条 | 已建立 |
| 自动一致性检查 | 171 项，0 失败 | 通过 |
| 自动评测 | 30 例，2700/2700 自动分 | 通过 |
| pytest | 58 passed | 通过 |

新增资料全部由用户提供，位于项目根目录；没有从互联网下载书籍，没有引入第五本外部资料作为事实依据。

---

## 2. 统一来源层

### 2.1 十个独立来源

| source_id | 书名/卷册 | 系列/卷册 | PDF 页 | 知识片段 | 解析方式 |
|---|---|---|---:|---:|---|
| `MM-ZYX-2016` | 《中药学》第4版 | — | 841 | 856 | PyMuPDF 文本层 |
| `CN-DIDAO-2011` | 《中国地道食材图录大全》 | — | 239 | 240 | RapidOCR |
| `FS-SFAH-2023` | 《盐，脂，酸，热：制造美味的新科学》 | — | 364 | 418 | PyMuPDF 文本层 |
| `DK-INGREDIENTS` | 《食材百科全书》 | — | 531 | 1,075 | RapidOCR |
| `MCG-V1-2013` | 《食物与厨艺：面食·酱料·甜点·饮料》 | 食物与厨艺 / 1 | 326 | 396 | RapidOCR |
| `MCG-V2-2013` | 《食物与厨艺：蔬·果·香料·谷物》 | 食物与厨艺 / 2 | 363 | 408 | RapidOCR |
| `MCG-V3-2013` | 《食物与厨艺：奶·蛋·肉·鱼》 | 食物与厨艺 / 3 | 367 | 415 | RapidOCR |
| `FC-BELITZ-2009` | *Food Chemistry*，第4版，2009 | — | 1,114 | 1,112 | PyMuPDF 文本层 |
| `FB-PAGE-2008` | *The Flavor Bible*，2008 | — | 391 | 1,289 | PyMuPDF 文本层 + 版面重建 |
| `CR-WXY-2003` | 《烹饪原料学》，2003 | — | 244 | 447 | RapidOCR |
| **合计** | **10 本/册** | | **4,780** | **6,656** | |

三册《食物与厨艺》分别登记为独立 `source_id`，并保留 `series=食物与厨艺` 与 `volume=1/2/3`。引用时必须写清卷册，不得只写总书名。

### 2.2 元数据与完整性

- `config/books.json` 登记书名、作者、出版信息、相对路径、`source_id`、系列、卷册和解析方式。
- `config/book_hashes.json` 登记文件大小、SHA-256 与页数。
- `validate_kb.py` 对 10 个原始文件逐一核验存在性、大小和 SHA-256；全部通过。
- 原始 PDF 不进入 Skill 包分发，避免把用户提供的版权资料当作可再分发资产。

### 2.3 页级字段

页级记录保留：

```text
source_id, pdf_page, printed_page, printed_page_raw,
method, text, text_raw, n_lines, mean_score,
low_confidence_lines, layout, warnings, chapter, section, toc_path
```

`printed_page` 与 `pdf_page` 分开存储。没有观察到可靠印刷页时保留 `null`，不按固定偏移反推。数字版与扫描版的页码映射分别处理。

---

## 3. 统一食材知识模型

### 3.1 新增字段

`schemas/ingredient.schema.json` 在原有 18 个顶层字段上增加了 20 个 Phase 2 可选字段：

```text
scientific_name
ingredient_category
botanical_or_animal_origin
physical_properties
chemical_composition
protein_profile
lipid_profile
carbohydrate_profile
aroma_compounds
flavor_characteristics
texture_properties
thermal_behavior
processing_behavior
storage_properties
culinary_applications
food_science_evidence
traditional_materia_medica
safety_information
source_references
gaps
```

这些字段全部允许为空。空字段表示知识库没有足够依据，不表示“已经研究但省略”。

### 3.2 传统本草与食品科学分离

模型保留两条独立路径：

- `tcm_attributes` / `tcm_applications`：传统四气五味、归经、功效、传统应用与理论依据。
- `chemical_composition` / `protein_profile` / `lipid_profile` / `carbohydrate_profile` / `thermal_behavior` 等：食品化学与加工特性。

两条路径不得互相替代。传统功效不得写成现代医学证据；食品化学结论也不得反过来证明传统功效。

### 3.3 食材卡覆盖

| 卡片 | 中文名 | 状态 | 来源数 | 已建立搭配 | 主要缺口 |
|---|---|---|---:|---:|---|
| `basil` | 罗勒 | partial | 2 | 2 | 学名、品种、产地、香气定量 |
| `chicken` | 鸡 | partial | 2 | 0 | 品种、部位差异、中心温度与持水性定量 |
| `wheat-flour` | 小麦面粉 | partial | 2 | 0 | 蛋白质分档、灰分、吸水率、流变学 |
| `egg` | 蛋 | partial | 2 | 0 | 蛋清/蛋黄蛋白定量、凝固曲线、起泡性 |
| `milk` | 乳 | partial | 2 | 0 | 乳蛋白分型、脂肪球结构、热处理风味 |
| `salmon` | 鲑鱼 | partial | 2 | 0 | 品种、养殖/野生差异、脂质组成、寄生虫风险 |

六张 Phase 2 卡全部通过 JSON Schema 校验；`research_status` 均为 `partial`。不得把 `partial` 卡当作已完成的全量食材百科条目。

### 3.4 已修正的证据问题

`chicken.json` 原先尝试记录 `CHICKEN + ROSEMARY`，但引用的 *The Flavor Bible* PDF 130 原文没有直接列出 rosemary。该条已从卡片移除，并保留人工复核缺口说明。对应的 E26/E27 评测也已改用书中可核验的 `TARRAGON + CHICKEN`（PDF 358，印刷页 342），不再把未核实搭配写成书中原文。

---

## 4. 统一检索层

### 4.1 SQLite 表规模

| 表 | 行数 | 用途 |
|---|---:|---|
| `sources` | 10 | 来源元数据 |
| `pages` | 4,780 | 页级原文与页码 |
| `chunks` | 6,656 | 页内知识片段 |
| `chunks_fts` | 6,656 | FTS5 全文索引 |
| `herbs` | 558 | 本草结构化记录 |
| `aliases` | 813 | 书名/食材别名归一化 |
| `flavor_pairings` | 13,758 | 去重后的搭配关系 |
| `flavor_affinities` | 292 | Flavor Affinities 组合 |
| `chemistry_topics` | 2,319 | 食品化学主题定位 |
| `culinary_sections` | 154 | 十书章节结构 |
| `conflict_candidates` | 2 | 跨来源并列表述复核候选 |

### 4.2 检索能力

支持：

- 按食材名称与别名检索；
- 按书名、`source_id`、系列、卷册过滤；
- 按章节/领域过滤；
- FTS5 全文检索与中文字符 n-gram 重排；
- 中文查询无命中时的子串回退；
- `--pairing` / `--pair` 专用搭配检索；
- `--chemistry` 专用化学主题检索；
- `--herb` 本草结构化检索；
- `--page SOURCE:PAGE` 整页回溯；
- 跨书籍联合检索；
- 页码真实性回查。

### 4.3 中文专业词检索桥

`config/professional_terms.json` 收录 30 个中文专业词头与 52 个英文扩展，例如：

```text
美拉德反应 → Maillard reaction
淀粉糊化 → gelatinization
蛋白质变性 → protein denaturation
水分活度 → water activity
脂质氧化 → lipid oxidation
```

该文件只用于检索归一化，不是事实来源。英文补充查询结果的排序分会乘 0.9，避免英文命中压过中文原文。

### 4.4 跨来源冲突复核

`scripts/build_conflict_candidates.py` 生成 `data/conflict_candidates.jsonl`。当前 2 条候选：

| 食材 | 主题 | 来源 A | 来源 B | 状态 |
|---|---|---|---|---|
| 花椒 | 外观品质 | 《中药学》PDF 396 | 《中国地道食材图录大全》PDF 234 | `review` |
| 黄油 | 加工方式 | 《盐，脂，酸，热》PDF 70 | 《食材百科全书》PDF 370 | `review` |

两条都是“同一知识域存在不同表述”的候选，不是已确认矛盾。系统并列保留来源，不取多数票，不用模型记忆裁判。

### 4.5 语义检索扩展评估

当前没有引入向量数据库。现有 FTS5 + n-gram + 子串回退 + 专业词桥接已覆盖专有名词、页码定位和精确短语检索。向量检索的潜在收益是处理“意思相近但用词不同”的问题；成本是新增 embedding 依赖、重建索引、版本管理和阈值调参。Phase 2 不强制引入，建议在真实问题集上统计 FTS5 漏检率后再决定。

---

## 5. 模块与工作流接入

### 5.1 五个基础模块

| 模块 | 新增知识接入 |
|---|---|
| A 本草研究 | 保留《中药学》结构；可用食品化学补充成分/加工信息，但不替代传统理论 |
| B 食材研究 | 增加食品组成、物理特性、加工保存、品质与烹饪适用性 |
| C 风味科学 | 增加 Flavor Pairing Index、香气物质、质地、加工对风味影响、证据等级 |
| D 美食研发 | 增加食品化学依据、搭配依据、工艺解释；书籍依据与 AI 参数分开 |
| E 研究与验证 | 增加食品化学研究、风味组合研究、多书交叉、对照实验与感官评价建议 |

### 5.2 两个跨模块引擎

- **Food Chemistry Research**：机制、成分、反应、加工变化；入口 `references/food-chemistry/` 与 `search.py --chemistry`。
- **Flavor Pairing Engine**：书中直接搭配、affinity 推导、AI 创新三层证据；入口 `references/flavor-pairing/`、`data/flavor_pairings.jsonl`、`data/flavor_review_queue.jsonl`。

### 5.3 八种工作流

| 模式 | 工作流文件 | 主要知识来源 |
|---|---|---|
| 1 食材深度研究 | `workflows/01-ingredient-deep-dive.md` | 食材书 + 食物与厨艺 + 食品化学 |
| 2 食材对比研究 | `workflows/02-ingredient-comparison.md` | 食材书 + 食品化学 + 风味科学 |
| 3 食材配伍分析 | `workflows/03-pairing-analysis.md` | 本草 + 食材 + 风味搭配 |
| 4 风味科学分析 | `workflows/04-flavor-science.md` | 盐脂酸热 + 食品化学 |
| 5 菜谱研发 | `workflows/05-recipe-development.md` | 食品化学 + 食物与厨艺 + Flavor Bible |
| 6 菜谱优化 | `workflows/06-recipe-optimization.md` | 风味科学 + 食品化学 + 搭配 |
| 7 创新菜品设计 | `workflows/07-innovation-design.md` | 食材 + 搭配 + 食品化学 |
| 8 专题研究报告 | `workflows/08-topic-research.md` | 多书交叉 + 实验设计 |

八种工作流均已写入 Phase 2 来源分工与证据等级要求。主 Skill 按任务选择 1 个主模式，必要时加 1 个辅助模式，不机械调用全部模块。

### 5.4 数据结构

| Schema | 约束内容 |
|---|---|
| `schemas/ingredient.schema.json` | 食材基础、感官、传统本草、食品科学、安全、来源、缺口 |
| `schemas/recipe.schema.json` | 定位、研发思路、食材、预处理、步骤、温度时间、调味逻辑、风险、可调参数、证据、验证状态 |
| `schemas/research-report.schema.json` | 问题、范围、检索策略、证据、交叉验证、冲突、假设、实验、结论、局限、下一步 |
| `schemas/knowledge-record.schema.json` | source_id、书名、系列、卷册、章节、印刷页、PDF 页、类型、内容、关键词、置信度、解析方式 |
| `schemas/source.schema.json` | 来源登记与版本信息 |
| `schemas/flavor-pairing.schema.json` | 搭配关系、证据等级、来源页、原始上下文、置信度 |

菜谱 Schema 的 `validation_status` 允许 `designed_only` / `not_tested`，不支持在无实验记录时写 `kitchen_tested`。

---

## 6. 质量与一致性

### 6.1 自动检查

`python scripts/validate_kb.py` 当前结果：

```text
checks: 171
failed: 0
pages: 4780
chunks: 6656
sources: 10
herbs: 558
ingredient_cards: 18
flavor_pairings: 13758
chemistry_topics: 2319
visual_records: 6811
```

检查覆盖：

- 原始文件存在、大小与 SHA-256；
- 页号连续、`printed_page` 合理；
- chunk 页码在范围内、citation 与页码字段一致；
- SQLite `pages` / `chunks` / FTS 行数一致；
-本草主条目字段与页码；
- 食材卡 Schema 与引文回查；
- 视觉记录页码与 `printed_page` 一致；
- 必需参考文件存在。

### 6.2 Phase 1 基线

第一阶段四书保持：

```text
pages: 1975
chunks: 2589
```

`validate_kb.py` 对这两个基线做硬检查；未删除、未覆盖、未改变旧 `source_id`。

### 6.3 解析质量

| source_id | 有文本页 | 近空页 | 页级低置信 |
|---|---:|---:|---:|
| `MCG-V1-2013` | 322 | 4 | 7 |
| `MCG-V2-2013` | 361 | 2 | 30 |
| `MCG-V3-2013` | 360 | 7 | 28 |
| `FC-BELITZ-2009` | 1,112 | 2 | 0 |
| `FB-PAGE-2008` | 376 | 15 | 0 |
| `CR-WXY-2003` | 244 | 0 | 2 |

新增六书 OCR 硬失败为 0；近空页多为章节扉页、整页图、版权页或扫描留白。页级低置信只作为检索线索，关键结论必须回原页核对。

### 6.4 视觉与表格候选

十书视觉清单 6,811 条：

- 内容图片 2,913；
- 整页扫描 2,392；
- 表格候选 1,506。

这些是 xref/bbox/文本启发式候选，不是人工确认的图注或单元格级表格。整页扫描记录数可能超过 PDF 页数，例如 `MCG-V1-2013` 326 页产生 652 个全页图像记录。

### 6.5 已观察到的数据噪声

- *The Flavor Bible* 三栏文本层存在串行、大小写和 OCR 式噪声；已保留 6,905 条复核队列。
- 640 条 Flavor Bible 条目中，25 条记录的 `printed_page` 与全书主流偏移明显不一致（涉及 12 个 PDF 页），例如 PDF 45 被标成印刷页 235。该问题已列入 `KNOWN_ISSUES.md`；引用时应优先核对 PDF 页与原页页眉，不把异常印刷页当作可靠引用。
- Flavor Bible 搭配表中存在 5 条 self-pair 噪声（如 `MINT + MINT`），不得当作真实搭配。
- 《食物与厨艺》三册是 OCR 文本，存在错字、断行、表格串行；低置信片段数分别为 35 / 205 / 163。
- 《烹饪原料学》有 13 条低置信片段。

---

## 7. 规模对比

| 指标 | Phase 1 | Phase 2 新增 | 合计 |
|---|---:|---:|---:|
| 来源 | 4 | 6 | 10 |
| 页记录 | 1,975 | 2,805 | 4,780 |
| 知识片段 | 2,589 | 4,067 | 6,656 |
| 本草结构化 | 558 | 0 | 558 |
| 食材卡 | 12 | 6 | 18 |
| 食品化学主题 | 0 | 2,319 | 2,319 |
| Flavor Bible 原始搭配 | 0 | 14,090 | 14,090 |
| Flavor Bible SQLite 去重搭配 | 0 | 13,758 | 13,758 |
| 视觉记录 | 1,152 | 5,659 | 6,811 |

---

## 8. 尚未完成

1. 30 个评测用例的专业正确性 10 分项仍为 `manual_pending`，没有厨师/食品科学专家逐例签字。
2. 没有真实厨房实验、感官盲评、重复性验证或微生物检测。
3. 六张 Phase 2 食材卡仍为 `partial`；品种、产地、季节、化学定量、香气阈值等大量字段为空。
4. 图片、图注、表格候选尚未人工审核；表格没有单元格级结构化。
5. Flavor Bible 的 6,905 条复核队列尚未逐条确认；搭配索引仍含噪声。
6. 没有引入向量数据库或神经语义检索；专业词桥接只覆盖 30 个词头。
7. 只有 2 条冲突复核候选，尚无经人工确认的真实冲突结论。
8. *Food Chemistry* 2009 与《烹饪原料学》2003 的版本边界必须保留，不得当作现行标准。

---

## 9. 复现命令

```powershell
# 先进入本仓库根目录（SKILL.md 所在目录）
python scripts\validate_kb.py
python scripts\run_evals.py --strict
python -m pytest tests -q
```

仅重建索引时：

```powershell
python scripts\build_conflict_candidates.py
python scripts\build_index.py
```

不要无理由重跑 OCR；六本新增书的 OCR 已完成。

---

## 10. 结论

Phase 2 已把六份新增资料接入统一来源层、页级检索、食品化学索引、风味搭配索引、食材模型、五个基础模块、两个跨模块引擎和八种工作流。原有四书数据与引用保持，自动一致性检查与自动评测通过。

这次升级的真实边界是：**知识可以按页检索，机制可以按来源解释，搭配可以按证据等级区分；但人工专业正确性、真实厨房验证、图表结构和全量语义理解仍未完成。**
