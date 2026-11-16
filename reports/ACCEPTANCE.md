# 第一阶段验收报告

**项目：Ingredient Research & Culinary R&D（专业食材研究与美食研发 Skill）**  
**验收日期：2026-11-16（Asia/Shanghai）**  
**知识库版本：four-book-v1**

---

## 1. 验收结论

本项目已从零构建为可被 AI Agent 调用、可检索、可引用、可测试的 Skill：

- 四本指定书 **4/4 找到并完成解析**，未引入第五本书或互联网资料作为事实依据；
- 建立 **1,975 条页记录、2,589 条知识片段、558 条本草结构化记录**；
- 建立 FTS5 检索、别名归一化、中文子串回退、页级引用和引用校验；
- 建立 5 个专业模块、8 种工作流、5 类 JSON Schema、12 张食材卡、41 张本草卡；
- 建立 10 个专业评测用例；自动可验证部分 **10/10 通过，900/900**；
- `pytest` **30 passed**；知识库一致性检查 **81/81 通过，0 失败**。

**边界说明：** 自动测试不能证明“菜一定好吃”，也不能替代医生、药师或厨师。  
评测中的“专业正确性 10 分/例”仍标记为人工复核项，未被脚本伪装成已评分。

---

## 2. 交付物清单

| 交付项 | 位置 | 状态 |
|---|---|---|
| Skill 入口与 YAML frontmatter | `SKILL.md` | 已完成 |
| 项目说明 | `README.md` | 已完成 |
| 五个专业模块 | `references/materia-medica/`、`chinese-ingredients/`、`flavor-science/`、`global-ingredients/`、`workflows/` + `evals/` | 已完成 |
| 八种工作流 | `workflows/01`–`08` | 已完成 |
| 统一食材模型 | `schemas/ingredient.schema.json` | 已完成 |
| 菜谱模型 | `schemas/recipe.schema.json` | 已完成 |
| 研究报告模型 | `schemas/research-report.schema.json` | 已完成 |
| 知识记录/来源模型 | `schemas/knowledge-record.schema.json`、`source.schema.json` | 已完成 |
| 书籍导入与 OCR | `scripts/ingest_digital.py`、`ocr_book.py` | 已完成 |
| 本草结构化 | `scripts/extract_herbs.py` + `data/herbs.jsonl` | 已完成 |
| 页内切分与索引 | `scripts/segment.py`、`build_index.py` | 已完成 |
| 检索与引用 | `scripts/search.py`、`validate_output.py` | 已完成 |
| 图像/表格候选清单 | `scripts/extract_visuals.py` + `data/images/` | 已完成候选清单，图注待人工审 |
| 知识新鲜度与一致性检查 | `scripts/validate_kb.py` | 81 项通过 |
| 评测集与运行器 | `evals/cases/`、`scripts/run_evals.py` | 10 例，自动部分全通过 |
| pytest 测试 | `tests/` | 30 passed |
| 图标 | `assets/icon.svg` | 已完成 |

---

## 3. 四本书实际导入情况

| source_id | 书名 | 文件大小 | PDF 页数 | 解析方式 | 实际状态 |
|---|---|---:|---:|---|---|
| `MM-ZYX-2016` | 《中药学》第4版，钟赣生主编，中国中医药出版社，2016 | 21,288,770 B | 841 | PyMuPDF 文本层 | 已导入；832 页有 ≥20 字符文本，9 页近空 |
| `CN-DIDAO-2011` | 《中国地道食材图录大全》，李清，武汉出版社，2011 | 61,009,781 B | 239 | RapidOCR | 已导入；239 页有文本，8 页低置信 |
| `FS-SFAH-2023` | 《盐，脂，酸，热：制造美味的新科学》，萨明·诺斯拉特，中信出版社，2023 | 39,859,673 B | 364 | PyMuPDF 文本层 | 已导入；325 页有 ≥20 字符文本，39 页近空 |
| `DK-INGREDIENTS` | 《食材百科全书》，英国DK出版社，丛龙岩译 | 200,363,567 B | 531 | RapidOCR | 已导入；505 页有 ≥20 字符文本，26 页近空 |

四本书 SHA-256 已写入 `config/book_hashes.json`：

```text
MM-ZYX-2016   edf95057dde2f1484809244e34de4fd7c75472b78efb99226bc490116f2497f9
CN-DIDAO-2011 8864acf46b2ee97a7203e139e2a258c76bdb7fc6fe7f0812f425d0117f21c901
FS-SFAH-2023  968bf96921ad5662c7828f5110ea88f18c946cdb5410a849b5ff8c80887dee11
DK-INGREDIENTS c0ac3fd4d2cda4c92537d860625ce8e8028312a0029af20c7bd316b51d9278b3
```

**没有导入的书籍：** 没有第五本书、论文、网页或外部营养数据库。  
**没有伪造的内容：** 四本书中找不到的内容统一标记为「当前四本书知识库暂无充分依据。」

---

## 4. 页级解析与知识片段

| 指标 | 实际数值 |
|---|---:|
| 页记录总数 | 1,975 |
| 有 ≥20 字符文本的页 | 1,901 |
| 近空页（<20 字符） | 74 |
| OCR 硬失败页 | 0 |
| OCR 低置信页（mean_score < 0.72） | 36（CN 8、DK 28） |
| 知识片段总数 | 2,589 |

各书片段数：

| source_id | 页记录 | 知识片段 | 说明 |
|---|---:|---:|---|
| `MM-ZYX-2016` | 841 | 856 | 832 页可用文本；9 页近空 |
| `CN-DIDAO-2011` | 239 | 240 | 239 页有文本；8 页低置信 |
| `FS-SFAH-2023` | 364 | 418 | 325 页可用文本；39 页近空 |
| `DK-INGREDIENTS` | 531 | 1,075 | 505 页有片段；26 页近空 |
| **合计** | **1,975** | **2,589** | 页记录 100% 生成；近空页不等于解析崩溃 |

**口径说明：**

- “成功解析”按“生成了页记录，并且该页有可检索文本”分别统计；
- 74 个近空页主要是章节扉页、版权页、整页图片或扫描留白，不能算作知识正文；
- 0 个 OCR 硬失败页表示 `data/ocr/*/failures.jsonl` 为空，不表示 OCR 每字都正确；
- 低置信页只可作为检索线索，关键引用必须回看原页。

---

## 5. 《中药学》结构化本草

| 指标 | 实际数值 |
|---|---:|
| 目录定位记录总数 | 558 |
| 主条目（`is_attached=false`） | 434 |
| 附药（`is_attached=true`） | 124 |
| 有功效字段的条目 | 436（434 主条目 + 2 附药） |
| 主条目中功效/应用/用法完整 | 434 / 434 / 434 |
| 主条目高置信 | 432 |
| 主条目中置信（缺“药性”字段） | 2（苏木、旋覆花） |

结构化字段来源为“目录定位 + 原文正则解析”，不是人工逐条校对。  
具体药性、剂量、禁忌在引用前必须回查原页；教材剂量不能转成对用户的个体化用药指导。

---

## 6. 参考卡与视觉清单

| 类型 | 数量 | 位置 |
|---|---:|---|
| 本草主题卡 | 8 | `references/materia-medica/topics/` |
| 本草单药卡 | 41 | `references/materia-medica/herbs/` |
| 本草全量索引 | 434 行 | `references/materia-medica/herb-index.md` |
| 中国食材卡 | 8 | `references/chinese-ingredients/ingredients/` |
| 全球食材卡 | 4 | `references/global-ingredients/ingredients/` |
| 风味科学卡 | 5 + README | `references/flavor-science/` |
| 食材 JSON 卡 | 12 | `data/ingredients/` |

视觉清单 `data/images/manifest.jsonl`：

| 类型 | 数量 | 说明 |
|---|---:|---|
| 视觉记录总数 | 1,152 | 每条的页号、xref、bbox、邻近文字候选均可回查 |
| 内容图片 | 353 | MM 42、FS 192、CN 119 |
| 整页扫描 | 769 | CN 239、DK 530，不能当作独立食材照片 |
| 表格候选 | 30 | MM 21、FS 9；文本/线框启发式，尚未单元格级人工校验 |

`caption_candidate` 是邻近文字候选，全部标记为待人工复核；  
`table_candidate` 只是文本/线框启发式，不是已解析表格。项目没有重新分发书籍图片。

---

## 7. 引用与防伪造

已建立的检查：

1. 每条页级 chunk 保留 `source_id`、`book_title`、`chapter`、`section`、`printed_page`、`pdf_page`、`content_type`、`confidence`、`extraction_method`、`citation`；
2. `printed_page` 与 `pdf_page` 分开存储，不按固定偏移反推；
3. 2,589 条 chunk 的 `citation` 与页码字段一致；
4. 12 张食材卡的 184 条 quote 全部回查页面文本命中；
5. 10 个评测参考答案经 `validate_output.py` 校验，引用错误 0 条；
6. 测试集验证了“伪造页码”和“伪造引文”会被校验器拒绝；
7. 四本书文件大小与 SHA-256 在 81 项检查中逐本核对。

引用格式示例：

```text
[E2] 《中国地道食材图录大全》p.37（PDF 40），第一章，芸豆条。
[E3] 《盐，脂，酸，热》PDF 30，第一章，“盐与风味”。
```

找不到准确页码时只写章节，不编造页码；找不到内容时写固定缺口句。

---

## 8. 测试结果

完整命令输出见 `reports/verification.log`。

### 8.1 知识库一致性

执行：

```text
python ingredient-culinary-rd\scripts\validate_kb.py
```

实际结果：

```text
checks: 81
failed: 0
```

### 8.2 pytest

执行：

```text
python -m pytest ingredient-culinary-rd\tests -q
```

实际结果：

```text
30 passed
```

覆盖：页数与页号连续性、printed/pdf 分离、检索与别名、本草计数、Schema、引文回查、伪造页码/伪造引文拒绝、评测集完整性。

### 8.3 专业评测集

执行：

```text
python ingredient-culinary-rd\scripts\run_evals.py
```

实际结果：

```text
cases: 10
auto_passed: 10
auto_pass_rate: 100%
auto_score: 900.0/900
citation_errors: 0
hard_failures: 0
```

10 个用例覆盖：

1. 单一食材完整研究（花椒）；
2. 两种食材对比（绿豆 vs 黑豆）；
3. 多食材配伍分析（花椒 + 生姜）；
4. 盐脂酸热菜谱优化（提前加盐与烤鸡）；
5. 本草 × 烹饪交叉（生姜）；
6. 多书交叉引用（番茄）；
7. 四书没有的问题（奇亚籽）；
8. 来源定位与页码准确性；
9. 医疗安全边界（附子）；
10. 别名识别（西红柿/土豆/青小豆）。

**通过率口径：** 这里 100% 指自动可核验的 90 分维度；专业正确性 10 分/例仍是人工复核项。  
因此不能宣称“综合 100 分”，也不能宣称菜谱已经在厨房验证成功。

---

## 9. 已完成与尚未完成

### 已完成

- Skill 目录、SKILL.md、README；
- 四本书登记、哈希、页级解析、OCR、章节映射；
- 中药学目录定位与 558 条结构化本草；
- 2,589 条页级知识片段与 SQLite FTS5 索引；
- 中文别名归一化 + 子串回退检索；
- 五个专业模块与八种工作流；
- 食材、菜谱、研究报告、知识记录、来源五类 Schema；
- 引用校验器、知识库校验器、评测运行器；
- 12 张食材卡、41 张本草卡、8 张主题卡、5 张风味卡；
- 图像/整页扫描/表格候选清单；
- 10 例专业评测与 30 项 pytest；
- 本验收报告与图标。

### 尚未完成或受限

- **人工逐页校对**：页级自动解析覆盖全书，但人工卡片只覆盖少量高频食材/药材；
- **表格结构化**：已生成 30 个表格候选，但未完成单元格级人工校验与结构化解析；
- **图注确认**：有邻近文字候选，但没有人工逐张确认图注，也没有整页缩略图副本；
- **神经语义检索**：当前为 FTS5 + 字符 n-gram + 中文子串回退，不是 embedding/vector 检索；
- **真实烹饪实验**：没有厨房批次、感官面板、仪器测量记录，因此没有 `kitchen_tested` 菜谱；
- **医学边界**：不提供个体化处方、剂量、停药/换药建议；这不是功能缺失，而是硬边界；
- **扩展资料**：未导入第五本书、论文或网络资料。

---

## 10. 已知问题

1. **OCR 阅读顺序**：CN/DK 为扫描版，多栏、竖排、图注混排时可出现串栏；短引用已回查，长段语义需人工复核。
2. **低置信页**：36 页 `mean_score < 0.72`，只能作为检索线索，不能直接当原文结论。
3. **印刷页码部分可观察**：CN 194/239 页、DK 76/531 页可观察到页脚/页眉数字；其余只能写 PDF 页。DK 的 3 个 OCR 误识别页已清除，原值保留在 `printed_page_raw`。
4. **数字版无印刷页码**：MM/FS 为 calibre 转换 PDF，引用只能写 `PDF n`，不得反推 `p.n`。
5. **本草字段不完整**：附药多为短段落；434 条主条目完整，436/558 条有功效字段，不能把所有条目当成同等深度。
6. **别名表是检索工具**：`config/ingredient_lexicon.json` 只用于查询归一化，不是食材事实来源；不能把别名当成新食材，也不能用别名补写书里没有的内容。
7. **图像清单不是图像理解**：已保存页号、bbox、xref、邻近文字，但未对每张图做视觉识别；图注仍需人工确认。
8. **菜谱未做真实实验**：`recipe.schema.json` 强制 `validation_status`，没有实验记录时只能 `not_tested` 或 `designed_only`。

---

## 11. 下一阶段建议

1. **人工抽检与扩卡**：优先复核 12 张食材卡、41 张本草卡和高频药材；再扩到更多中国食材与 DK 食材。
2. **表格解析**：用 `pdfplumber` / PyMuPDF `find_tables` 建立表格单元格级记录，补上 `content_type=table` 的正文与结构。
3. **图注工作流**：对 353 张内容图逐张建立“图注候选 → 人工确认 → 已确认”的状态；不要把邻近文字直接当图注。
4. **混合检索**：在保留 FTS5 可解释性的基础上增加 embedding 召回，并用页级引用约束生成。
5. **真实实验**：建立 `data/experiments/`，记录批次、配方、温度、时间、感官评分与失败批次；只有有记录时才允许 `kitchen_tested`。
6. **新增资料**：为每本新书申请新的 `source_id`，保留旧页码与旧引用；新增资料不得覆盖或重写旧来源。
7. **医学与食品安全审校**：对毒性药材、妊娠禁忌、过敏原、生食风险建立人工审校清单。

---

## 12. 复现命令

在项目根目录执行：

```powershell
python ingredient-culinary-rd\scripts\validate_kb.py
python ingredient-culinary-rd\scripts\run_evals.py
python -m pytest ingredient-culinary-rd\tests -q
```

若当前目录已进入 `ingredient-culinary-rd/`，则使用：

```powershell
python scripts\validate_kb.py
python scripts\run_evals.py
python -m pytest tests -q
```

重建视觉清单：

```powershell
python scripts\extract_visuals.py
```

---

## 13. 验收判定

| 验收项 | 判定 |
|---|---|
| 项目骨架与 Skill 规范 | 通过 |
| 四本书实际导入 | 4/4 通过（原始文件由用户提供） |
| 页级解析与页码分离 | 通过；1,975 页记录，0 硬失败 |
| 知识片段与检索 | 通过；2,589 片段，FTS5 + 子串回退 |
| 本草结构化 | 通过；558 条记录，434 主条目 |
| 五个模块与八种工作流 | 通过 |
| 食材/菜谱/报告 Schema | 通过 |
| 引用溯源与防伪造 | 通过自动检查 |
| 专业评测自动部分 | 10/10，900/900 |
| 人工专业正确性 | 待复核，未冒充完成 |
| 真实烹饪实验 | 未进行，未声称成功 |

**最终状态：可用于“四书范围内的可溯源食材研究与研发辅助”，但不是完整百科、不是医学处方系统、不是已经完成厨房验证的菜谱库。**
