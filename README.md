# Ingredient Research & Culinary R&D

**专业食材研究与美食研发 Skill** · 十书知识库 · 页级引用 · 食品化学 · 风味搭配 · 可执行测试

这不是一个“输入食材、输出菜谱”的生成器，而是一套可被 AI Agent 调用的研究工作台：

- 把十本指定书籍拆成**页级知识片段**，保留 PDF 页码、可见印刷页码、章节、OCR 可信度；
- 把《中药学》解析成 **558 条结构化本草记录**（434 条主条目 + 124 条附药）；
- 为《Food Chemistry》建立 **2,319 条主题索引**；
- 为《The Flavor Bible》建立 **搭配索引 + 复核队列**；
- 用 SQLite FTS5、中文分词、别名归一化和专用过滤做**可溯源检索**；
- 用五个基础模块 + 食品化学模块 + 风味搭配引擎组织研究与研发；
- 用 JSON Schema 约束食材、菜谱、研究报告、知识记录、来源和搭配；
- 用自动测试检查页码真实性、引用回查、知识缺口、安全边界和索引一致性。

---

## 1. 当前状态（诚实版）

> 最终数字以 `data/manifest.json`、`reports/phase2/PHASE2_ACCEPTANCE.md` 和 `reports/verification.log` 为准。

| 项目 | 当前状态 |
|---|---|
| 指定书籍 | 10 本/册（第一阶段 4 + 第二阶段 6） |
| PDF 找到情况 | 10/10 找到 |
| 页记录 | 4,780 |
| 知识片段 | 6,656 |
| 第一阶段页/chunks 基线 | 1,975 / 2,589，保持不变 |
| 第二阶段页/chunks | 2,805 / 4,067 |
| 本草结构化 | 558 条：434 主条目 + 124 附药 |
| 结构化食材卡 | 18 张：第一阶段 12 + 第二阶段 6（Phase 2 均为 `partial`） |
| 食品化学主题 | 2,319 |
| Flavor Bible 条目 | 640 |
| 搭配原始记录 | 14,090（13,503 direct + 587 derived） |
| SQLite 去重搭配 | 13,758（13,503 direct + 255 derived） |
| 搭配复核队列 | 6,905 |
| OCR 硬失败页 | 0（不等于 OCR 每字正确） |
| 自动化评测 | E01–E30，结果见 `evals/results/` |
| 人工专业正确性 | 每例 10 分仍为 `manual_pending` |
| 真实厨房实验 | **没有做** |

### 书籍版本边界

- 《食物与厨艺》三册分别独立登记，页码引用必须写清卷册。
- *Food Chemistry* 是 **2009 年第4版**，不是现行食品安全标准。
- 《烹饪原料学》是 **2003 年历史教材**，不是现行行业规范。
- *The Flavor Bible* 是**创意参考**，不是经过科学实验验证的相容性数据库。

> 十书没有覆盖的内容统一标：
>
> **当前十书知识库暂无充分依据。**

PDF 是用户提供的原始资料，**不放进 Skill 包内部分发**。`config/books.json` 只保存相对路径、元数据和 SHA-256。

---

## 2. 快速开始

### 2.1 环境

- Python 3.11+（本机验证：3.14）
- `pymupdf`、`jieba`、`numpy`、`jsonschema`
- 扫描 OCR 额外需要：`rapidocr-onnxruntime`、`onnxruntime`
- 测试：`pytest`
- 可选：`pdfplumber`（表格辅助）

以下命令默认当前目录为 Skill 根目录 `ingredient-culinary-rd/`。若在项目根目录执行，
请在路径前加 `ingredient-culinary-rd/`。

```bash
python -m pip install pymupdf jieba numpy jsonschema rapidocr-onnxruntime onnxruntime pytest
```

### 2.2 检索

```bash
python scripts/search.py "花椒 温中止痛" --top 8
python scripts/search.py "西红柿" --mode semantic --top 8
python scripts/search.py "盐 渗透 入味" --source FS-SFAH-2023
python scripts/search.py "淀粉 糊化 酱汁" --source MCG-V1-2013
python scripts/search.py "water activity" --source FC-BELITZ-2009
python scripts/search.py "肌肉 蛋白质 加热" --series 食物与厨艺 --volume 3
python scripts/search.py --pairing BASIL --top 20
python scripts/search.py --pair BASIL TOMATOES
python scripts/search.py --chemistry Maillard --top 8
python scripts/search.py --herb 花椒
python scripts/search.py --page FB-PAGE-2008:73
```

输出包含：书名、印刷页/PDF 页、章节、片段类型、OCR 可信度、证据摘要、排序分。

### 2.3 重建知识库

```bash
# 1) 数字版 PDF
python scripts/ingest_digital.py --all-digital

# 2) 扫描版 PDF（已 OCR 完成；不要无理由全量重跑）
python scripts/ocr_book.py --book MCG-V1-2013 --workers 2 --dpi 110

# 3) 本草结构化
python scripts/extract_herbs.py

# 4) 别名/检索词表
python scripts/build_lexicon.py

# 5) 页内切分
python scripts/segment.py --all

# 6) Phase 2 结构索引
python scripts/extract_flavor_pairings.py
python scripts/extract_food_chemistry.py
python scripts/build_culinary_sections.py

# 7) SQLite FTS5
python scripts/build_index.py

# 8) 图像、整页扫描与表格候选
python scripts/extract_visuals.py
```

> `build_index.py` 会重建表。生产库升级前必须备份 `data/index/knowledge.sqlite`，并按验收报告的回滚步骤操作。

### 2.4 质量检查

```bash
python scripts/validate_kb.py
python scripts/run_evals.py --strict
python -m pytest tests -q
```

---

## 3. 目录结构

```text
ingredient-culinary-rd/
├── SKILL.md                     # Agent Skills 入口（YAML frontmatter + 执行契约）
├── README.md
├── config/
│   ├── books.json               # 十本书元数据、source_id、路径
│   ├── book_hashes.json         # 文件大小、SHA-256、页数
│   ├── chapter_maps.json        # 卷册/章节起页
│   ├── query_hints.json         # 仅用于检索归一化的同义词（非事实依据）
│   └── ingredient_lexicon.json  # 书名别名 + 检索别名（生成物）
├── references/
│   ├── materia-medica/          # 模块 A：本草理论、主题卡、药材卡、全量索引
│   ├── chinese-ingredients/     # 模块 B：中国地道食材
│   ├── global-ingredients/      # 模块 B：DK 全球食材
│   ├── culinary-ingredients/    # 模块 B：《烹饪原料学》
│   ├── flavor-science/          # 模块 C：盐/脂/酸/热/平衡
│   ├── food-and-cooking/        # 模块 F：三册《食物与厨艺》
│   ├── food-chemistry/          # 模块 F：Food Chemistry
│   ├── flavor-pairing/          # 模块 G：Flavor Bible 证据政策
│   └── knowledge-index/         # 书目、覆盖、引用政策、检索指南
├── workflows/                   # 八种工作模式
├── schemas/                     # 食材/菜谱/研究报告/知识记录/来源/搭配
├── evals/                       # E01–E30、评分规则、运行结果
├── scripts/                     # 导入、OCR、解析、切分、索引、检索、校验
├── data/
│   ├── pages/                   # 页级原文
│   ├── chunks/                  # 知识片段
│   ├── index/knowledge.sqlite   # FTS5 + 结构化表
│   ├── ingredients/             # Phase 1 食材卡
│   ├── ingredients-phase2/      # Phase 2 partial 食材卡
│   ├── flavor_*.jsonl           # 搭配、affinity、复核队列
│   ├── chemistry_topics.jsonl   # 化学主题
│   └── images/                  # 图像/整页扫描/表格候选清单
├── tests/                       # pytest 单元/集成测试
├── assets/                      # 图标与可选审阅素材
├── backups/                     # 本地回滚备份（已 gitignore，不随仓库发布）
└── reports/
    ├── ACCEPTANCE.md            # 第一阶段历史验收（保留）
    ├── verification.log         # 验证日志
    └── phase2/                  # 第二阶段报告
```

---

## 4. 数据流水线

```text
PDF
 ├─ 数字版 → PyMuPDF 文本层 → data/pages/<source>.jsonl
 └─ 扫描版 → RapidOCR → 行框 + 置信度 + 阅读顺序
                → data/pages/<source>.ocr.jsonl
                        ↓
              页内清洗 / 去水印 / 章节映射
                        ↓
              data/chunks/<source>.jsonl（页级片段）
                        ↓
        SQLite FTS5（jieba）
        + herbs + aliases + flavor_pairings
        + chemistry_topics + culinary_sections
                        ↓
                 scripts/search.py
```

### 页码策略

- `printed_page`：**只在页眉/页脚直接看到数字时**填写。
- `pdf_page`：PDF 物理页序号。
- 扫描书常见 `p.37（PDF 40）`；数字版可能只有 PDF 页。
- 绝不按固定偏移“推算”印刷页码并伪装成已观察到。

### OCR 策略

- 110–150 DPI 灰度；RapidOCR。
- 行框按列聚类重建阅读顺序；竖排/多栏页面保留警告。
- 每页保存 `mean_score`、低置信行数、布局类型、warnings。
- 低置信页只能作为检索线索；写关键结论必须回看页面图像。

---

## 5. 模块

| 模块 | 解决的问题 | 入口 |
|---|---|---|
| A 本草研究 | 四气五味、归经、功效、配伍、禁忌、炮制 | `references/materia-medica/README.md` |
| B 食材研究 | 分类、产地、品种、时令、品质、加工、替代 | 食材 references + `schemas/ingredient.schema.json` |
| C 风味科学 | 盐脂酸热、香气、质地、温度、调味顺序 | `references/flavor-science/` |
| D 美食研发 | 菜品定位、配比、工艺、温度时间、迭代 | `workflows/05`–`07` |
| E 研究与验证 | 课题拆解、交叉验证、假设、实验、结论 | `workflows/08`、`evals/` |
| F 食品化学研究 | 组成、变性、糊化、氧化、美拉德、香气、加工 | `references/food-chemistry/` |
| G 风味搭配引擎 | 直接搭配、组合推导、创新假设、证据溯源 | `references/flavor-pairing/` |

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
[E2] 《中国地道食材图录大全》p.230（PDF 234），花椒条。
[E3] Food Chemistry (Belitz et al., 4th ed., 2009) p.271（PDF 315）。
[E4] 《The Flavor Bible》p.58（PDF 73），BASIL 条目。
[E5] 《食物与厨艺：奶·蛋·肉·鱼》p.346（PDF 348）。
[E6] 《烹饪原料学》p.66（PDF 77）。
```

四类标签：

- `[原文]`：书里直接写了什么。
- `[跨来源推理]`：两本以上书组合出的判断。
- `[创新假设]`：待验证的研发假设。
- `[知识库缺口]`：固定表述「当前十书知识库暂无充分依据。」

**禁止**：编造书名、章节、页码；把传统功效写成现代医学结论；把中药材默认当食品；给个体化剂量/处方；把 Flavor Bible 搭配当科学证明；把 Food Chemistry 2009 当现行标准；把未做的实验写成已完成。

---

## 8. 测试

`evals/cases/` 现覆盖 30 例：

### 第一阶段：E01–E10

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

### 第二阶段：E11–E30

- 食品化学：E11–E15
- 食材研究：E16–E20
- 风味配伍：E21–E25
- 综合研发：E26–E30

每例记录：问题、预期来源、预期要点、引用检查、专业正确性、安全性、评分。

```bash
python scripts/run_evals.py --strict
```

结果写入 `evals/results/latest.json` 与 `latest.md`。

> 自动测试验证的是**检索命中、引用存在性、页面对应、关键词覆盖、缺口识别、禁用表述**；专业正确性 10 分/例是人工复核项，脚本不填。菜谱可执行性也不能由自动脚本假装“味道已验证”。

### 图像与图注

`data/images/manifest.jsonl` 记录图片/整页扫描的页号、xref、bbox、邻近文字候选
与审核状态。`caption_candidate` 不是已确认图注；`table_candidate` 只是文本/线框启发式，
不是已解析表格。详见 `data/images/README.md`。

---

## 9. 已知限制

- 扫描版 OCR 对复杂版式、竖排、艺术字、表格仍有错字；`mean_score < 0.72` 的页面不可直接当原文引用。
- 《食物与厨艺》V2 有 205 条、V3 有 163 条、V1 有 35 条低置信片段；《烹饪原料学》有 13 条。
- 《食物与厨艺》V2 第三章章首页未被可靠定位，项目没有猜测补写。
- DK 页眉页码与 PDF 序存在个别不连续，按“直接观察到的页码”记录，未强行统一偏移。
- 数字版《中药学》《盐，脂，酸，热》是 calibre 转换 PDF，无印刷页码，只能引 PDF 页。
- 《中药学》结构化字段来自目录定位 + 正则解析，附药条目字段常不完整。
- Food Chemistry 主题索引主要来自章节标题，不是全书逐句摘要；`Retrogradation` 等术语可能需全文检索。
- The Flavor Bible 的三栏文本层有串行、大小写和 OCR 式噪声；搭配索引保留 6,905 条复核队列。
- The Flavor Bible 有 25 条条目的 `printed_page` 与全书主流偏移明显不一致（涉及 12 个 PDF 页）；引用时优先核对 PDF 页与原页页眉。
- 图片只保留页、位置、尺寸、邻近文本候选与 xref/bbox；未生成缩略图副本，复杂图注仍需人工审核。
- 当前检索是 FTS5 + 字符 n-gram 重排 + 中文子串回退，不是神经语义向量。
- `run_evals.py` 评测内置 `reference_answer` 模板，不是现场生成回答；专业正确性 10 分/例仍为人工待评。
- **没有真实厨房实验**；所有菜谱默认 `designed_only` / `not_tested`。

---

## 10. 未来扩展

- 新增食品科学/营养/法规/地方志/论文：在 `config/books.json` 注册新 `source_id`，走同一流水线。
- 新版 Food Chemistry 或食品法规：新来源，不覆盖 2009 版引用。
- 增加嵌入模型：先做收益/成本分析；保留 FTS 作为可解释兜底。
- 增加表格解析：`pdfplumber` / `PyMuPDF find_tables`，输出 `content_type=table`。
- 增加真实烹饪实验：`data/experiments/` 记录批次、配方、温度、感官评分，与理论假设分离。
- 增加多语言：英文术语与中文食材名对齐。

---

## 11. 许可与资料

代码与本项目自写文档：MIT。

十本书的版权归原作者/出版方所有。仓库不包含书籍 PDF；使用者需自行合法持有资料。引用仅用于研究、评论与溯源。

