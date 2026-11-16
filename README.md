# Ingredient Research & Culinary R&D

**专业食材研究与美食研发 Skill** · 四书知识库 · 页级引用 · 可执行测试

这不是一个“输入食材、输出菜谱”的生成器。它是一套可被 AI Agent 调用的研究工作台：

- 把四本专业书拆成**页级知识片段**，保留 PDF 页码、可见印刷页码、章节、OCR 可信度；
- 把《中药学》的 558 条记录（434 条主条目 + 124 条附药）解析成**结构化记录**（性味归经、功效、应用、用法、注意、现代研究）；
- 用 SQLite FTS5 + 中文分词 + 别名归一化做**可溯源检索**；
- 用五个专业模块和八种工作模式组织研究与研发；
- 用 JSON Schema 约束食材、菜谱、研究报告和知识记录；
- 用可运行测试检查引用真实性、知识缺口、安全边界和检索命中。

---

## 1. 当前状态（诚实版）

| 项目 | 状态 |
|---|---|
| 项目骨架、SKILL.md、README | 已完成 |
| 四本书文件识别 | 4/4 找到 |
| 数字版文本层提取 | 2/2 完成 |
| 扫描版 OCR | 2/2 完成（见验收报告的实际页数） |
| 《中药学》单味药结构化 | 558 条 = 434 条主条目 + 124 条附药；436 条有功效字段 |
| 页级知识片段 | 见 `reports/ACCEPTANCE.md` |
| SQLite FTS5 索引 | 已构建 |
| 五个模块参考 | 已完成 |
| 八种工作流 | 已完成 |
| 五类 JSON Schema | 已完成 |
| 测试集与运行结果 | 已完成，见 `evals/results/` |
| 图片/图注 | `data/images/manifest.jsonl` 已登记 1,152 条视觉记录（353 张内容图、769 张整页扫描、30 个表格候选）；图注候选均标记待人工复核 |
| 知识库覆盖 | **不等于整本书都被“理解”**；以页级检索与结构化条目为准 |

> 四本书的 PDF 是用户提供的原始资料，**不放进 Skill 包内部分发**。`config/books.json` 只保存相对路径、元数据和 SHA-256。

---

## 2. 快速开始

### 2.1 环境

- Python 3.11+（本机验证：3.14.7）
- `pymupdf`、`jieba`、`numpy`、`jsonschema`
- 扫描版 OCR 额外需要：`rapidocr-onnxruntime`、`onnxruntime`
- 测试：`pytest`
- 可选：`pdfplumber`（表格辅助）

以下命令默认当前目录为 Skill 根目录 `ingredient-culinary-rd/`。若在项目根目录执行，
请使用 `python ingredient-culinary-rd/scripts/...`。

```bash
python -m pip install pymupdf jieba numpy jsonschema rapidocr-onnxruntime onnxruntime pytest
```

### 2.2 检索

```bash
python scripts/search.py "花椒 温中止痛" --top 6
python scripts/search.py "西红柿" --mode semantic --top 8
python scripts/search.py "盐 渗透 入味" --source FS-SFAH-2023
python scripts/search.py --herb 花椒
python scripts/search.py --page FS-SFAH-2023:31
```

输出包含：书名、印刷页/PDF 页、章节、片段类型、OCR 可信度、证据摘要、排序分。

### 2.3 重建知识库

```bash
# 1) 数字版 PDF
python scripts/ingest_digital.py --all-digital

# 2) 扫描版 PDF（断点续跑；先小页数试跑）
python scripts/ocr_book.py --book CN-DIDAO-2011 --workers 2 --dpi 110
python scripts/ocr_book.py --book DK-INGREDIENTS --workers 2 --dpi 110

# 3) 《中药学》单味药结构化
python scripts/extract_herbs.py

# 4) 别名/检索词表
python scripts/build_lexicon.py

# 5) 页内切分
python scripts/segment.py --all

# 6) 建索引
python scripts/build_index.py

# 7) 图像、整页扫描与表格候选清单
python scripts/extract_visuals.py
```

### 2.4 质量检查

```bash
python scripts/validate_kb.py
python scripts/run_evals.py
python -m pytest tests -q
```

---

## 3. 目录结构

```text
ingredient-culinary-rd/
├── SKILL.md                     # Agent Skills 入口（YAML frontmatter + 执行契约）
├── README.md
├── config/
│   ├── books.json               # 四本书元数据、source_id、路径
│   ├── chapter_maps.json        # 扫描书章节起止页
│   ├── query_hints.json         # 仅用于检索归一化的同义词（非事实依据）
│   └── ingredient_lexicon.json  # 书名别名 + 检索别名（生成物）
├── references/
│   ├── materia-medica/          # 模块 A：本草理论、主题卡、药材卡、全量索引
│   ├── chinese-ingredients/     # 模块 B：中国地道食材
│   ├── flavor-science/          # 模块 C：盐/脂/酸/热/平衡
│   ├── global-ingredients/      # 模块 B：DK 全球食材
│   └── knowledge-index/         # 书目、覆盖、引用政策、检索指南
├── workflows/                   # 八种工作模式
├── schemas/                     # 食材/菜谱/研究报告/知识记录/来源
├── evals/                       # 测试用例、评分规则、运行结果
├── scripts/                     # 导入、OCR、解析、切分、索引、检索、校验
├── data/                        # 生成物（页、片段、索引、结构化本草）
│   └── images/                  # 图像/整页扫描/表格候选清单（不重新分发原图）
├── tests/                       # pytest 单元/集成测试
├── assets/                      # 图标与可选的人工审阅素材
└── reports/ACCEPTANCE.md        # 验收报告
```

---

## 4. 数据流水线

```text
PDF
 ├─ 数字版 → PyMuPDF 文本层 → data/pages/<source>.jsonl
 └─ 扫描版 → 150/110 DPI 灰度 → RapidOCR → 行框 + 置信度
                → 列聚类阅读顺序 → data/pages/<source>.ocr.jsonl
                        ↓
              页内清洗 / 去水印 / 章节映射
                        ↓
              data/chunks/<source>.jsonl（页级片段）
                        ↓
        SQLite FTS5（jieba 分词）+ herbs + aliases
                        ↓
                 scripts/search.py
```

### 页码策略

- `printed_page`：**只在页眉/页脚直接看到数字时**写入。扫描书常见 `p.37（PDF 40）`。
- 数字版 calibre PDF 没有印刷页码文本层，`printed_page = null`，引用写 `PDF 396`。
- 绝不按固定偏移量“推算”印刷页码并伪装成已观察到。

### OCR 策略

- 110–150 DPI 灰度；RapidOCR PP-OCRv3。
- 行框按列聚类重建阅读顺序；竖排页面右→左，横排左→右。
- 每页保存 `mean_score`、低置信行数、布局类型、警告。
- 低置信页只能作为检索线索；写引用卡时必须回看页面图像。

---

## 5. 五个模块

| 模块 | 解决的问题 | 入口 |
|---|---|---|
| A 本草研究 | 四气五味、归经、功效、配伍、禁忌、炮制 | `references/materia-medica/README.md` |
| B 食材研究 | 分类、产地、品种、时令、品质、加工、替代 | `references/chinese-ingredients/`、`references/global-ingredients/` |
| C 风味科学 | 盐脂酸热、味觉平衡、香气、质地、温度 | `references/flavor-science/README.md` |
| D 美食研发 | 菜品定位、配比、工艺、温度时间、迭代 | `workflows/05`–`07` |
| E 研究与验证 | 课题拆解、交叉验证、假设、实验、结论 | `workflows/08`、`evals/` |

## 6. 八种工作模式

1. 食材深度研究
2. 食材对比研究
3. 食材配伍分析
4. 风味科学分析
5. 菜谱研发
6. 菜谱优化
7. 创新菜品设计
8. 专题研究报告

每种模式都有独立输入、检索计划、步骤、输出模板和检查表，位于 `workflows/`。

---

## 7. 引用与诚实性

统一引用：

```text
[E1] 《中药学》PDF 396，第十四章 温里药，花椒条。
[E2] 《中国地道食材图录大全》p.37（PDF 40），第一章，芸豆条。
```

四类标签：

- `[原文]`：书里直接写了什么。
- `[跨来源推理]`：两本以上书组合出的判断。
- `[创新假设]`：待验证的研发假设。
- `[知识库缺口]`：固定表述「当前四本书知识库暂无充分依据。」

**禁止**：编造书名、章节、页码；把传统功效写成现代医学结论；把中药材默认当食品；给个体化剂量/处方；把未做的实验写成已完成。

---

## 8. 测试

`evals/cases/` 覆盖用户要求的 10 类问题：

1. 单一食材完整研究
2. 两种食材对比
3. 多食材搭配
4. 盐脂酸热菜谱优化
5. 中药学 × 烹饪交叉
6. 多书交叉引用
7. 书中没有的问题
8. 来源定位与页码准确性
9. 医疗安全边界
10. 别名识别

每例记录：问题、预期来源、预期要点、引用准确性、专业正确性、安全性、评分。运行：

```bash
python scripts/run_evals.py
```

结果写入 `evals/results/latest.json` 与 `evals/results/latest.md`。

> 说明：自动测试验证的是**检索命中、引用存在性、页面对应、缺口识别、禁用表述**；菜谱的可执行性与专业判断由人工评分项覆盖，不能用一个脚本假装“味道已验证”。

### 图像与图注

`data/images/manifest.jsonl` 记录图片/整页扫描的页号、xref、bbox、邻近文字候选
与审核状态。`caption_candidate` 不是已确认图注；`table_candidate` 只是文本/线框启发式，
不是已解析表格。详见 `data/images/README.md`。

---

## 9. 已知限制

- 扫描版 OCR 对复杂版式、竖排、艺术字、表格仍有错字；`mean_score < 0.72` 的页面不可直接当原文引用。
- DK 书页眉页码与 PDF 页序存在个别不连续（扫描/装订导致），已按“直接观察到的页码”记录，未强行统一偏移。
- 数字版《中药学》《盐，脂，酸，热》是 calibre 转换 PDF，无印刷页码，只能引 PDF 页。
- 《中药学》结构化字段来自目录定位 + 正则解析，`附药` 条目多为短段落，字段不完整，已标记。
- 图片只保留页、位置、尺寸、邻近文本候选与 xref/bbox；未生成缩略图副本，复杂图注仍需人工审核。
- 当前检索是 FTS5 + 字符 n-gram 重排 + 中文子串回退，不是神经语义向量；同义改写很强时仍需人工换词。

---

## 10. 未来扩展

- 新增食品科学/营养/地方志/论文：在 `config/books.json` 注册新 `source_id`，走同一流水线。
- 增加嵌入模型：在 `scripts/search.py` 加向量召回，保留 FTS 作为可解释兜底。
- 增加表格解析：`pdfplumber` / `PyMuPDF find_tables`，输出 `content_type=table`。
- 增加真实烹饪实验：`data/experiments/` 记录批次、配方、温度、感官评分，与理论假设分离。
- 增加多语言：DK 原文英文术语对齐。

---

## 11. 许可与资料

代码与本项目自写文档：MIT。

四本书的版权归原作者/出版方所有。仓库不包含书籍 PDF；使用者需自行合法持有资料。引用仅用于研究、评论与溯源。
