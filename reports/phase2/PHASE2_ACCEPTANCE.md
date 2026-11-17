# Phase 2 验收报告

**项目：Ingredient Research & Culinary R&D（专业食材研究与美食研发 Skill）**  
**阶段：Phase 2 · Professional Food Science & Culinary Knowledge Expansion**  
**验收日期：2026-11-17（Asia/Shanghai）**  
**知识库版本：`ten-book-v2`**  
**结论：技术链路有条件通过。** 六份新增 PDF 已找到并导入，原有四书数据保持，自动检索/引用/一致性测试通过；专业正确性的人工复核、真实厨房实验和 OCR 逐字校对仍未完成。

---

## 1. 核心结果

| 指标 | 实际结果 |
|---|---:|
| 指定书籍 | 10 本/册（Phase 1 四本 + Phase 2 六本） |
| 新增 PDF 找到 | **6/6** |
| 新增 PDF 成功建立来源 | **6/6** |
| 总来源 | **10** |
| 总页记录 | **4,780** |
| 总知识片段 | **6,656** |
| FTS5 行数 | **6,656** |
| Phase 1 页 / 片段基线 | **1,975 / 2,589，保持不变** |
| Phase 2 页 / 片段 | **2,805 / 4,067** |
| 本草结构化记录 | **558**（434 主条目 + 124 附药） |
| 结构化食材卡 | **18**（Phase 1 12 + Phase 2 6；Phase 2 均为 `partial`） |
| 食品化学主题 | **2,319**（24 章，863 个有主题页） |
| Flavor Bible 原始搭配 | **14,090**（13,503 direct + 587 derived） |
| Flavor Bible SQLite 去重搭配 | **13,758**（13,503 direct + 255 derived） |
| 搭配人工复核队列 | **6,905** |
| 跨来源复核候选 | **2**（均标记 `review`，不是已确认冲突） |
| 视觉清单 | **6,811** 条（内容图 2,913 / 整页扫描 2,392 / 表格候选 1,506） |
| OCR 硬失败页 | **0** |
| 知识库一致性 | **171/171 通过，0 失败** |
| 自动评测 | **30/30 用例通过，2700/2700** |
| 引用硬错误 | **0** |
| pytest | **58 passed** |
| 真实厨房实验 | **未执行** |
| 专业正确性人工评分 | **30 例均 `manual_pending`** |

> 自动评测验证的是页码、引用回查、检索命中、缺口表述和安全模板，不是“菜一定好吃”或“专业正确性已被人工确认”。
>
> 另一个重要口径：`run_evals.py` 评测的是每个用例内置的 `reference_answer`（金标准答案模板），不是本次现场调用语言模型生成的 30 个回答。30/30 表示“金标准答案模板的自动可核验部分通过”，不表示“Agent 现场生成 30/30 通过”。

---

## 2. 六份新增资料的实际导入情况

| source_id | 文件 | PDF 页 | 知识片段 | 解析方式 | 当前状态 |
|---|---|---:|---:|---|---|
| `MCG-V1-2013` | 01 食物与厨艺 面食·酱料·甜点·饮料.pdf | 326 | 396 | RapidOCR | 已导入 |
| `MCG-V2-2013` | 02 食物与厨艺 蔬·果·香料·谷物.pdf | 363 | 408 | RapidOCR | 已导入 |
| `MCG-V3-2013` | 03 食物与厨艺 奶·蛋·肉·鱼.pdf | 367 | 415 | RapidOCR | 已导入 |
| `FC-BELITZ-2009` | Food Chemistry (Belitz 4th ed 2009).pdf | 1,114 | 1,112 | PyMuPDF 文本层 | 已导入 |
| `FB-PAGE-2008` | The Flavor Bible (Karen Page, Andrew Dornenburg 2008).pdf | 391 | 1,289 | PyMuPDF 文本层 | 已导入 |
| `CR-WXY-2003` | 烹饪原料学 王向阳 2003.pdf | 244 | 447 | RapidOCR | 已导入 |

六本书均建立独立 `source_id`。三册《食物与厨艺》分别保留 `series=食物与厨艺`、`volume=1/2/3`，引用时不得只写总书名。

---

## 3. 十二项验收标准对照

| # | 标准 | 结果 | 说明 |
|---:|---|---|---|
| 1 | 六份 PDF 找到并解析，或明确标记缺失 | **通过** | 6/6 找到、6/6 有页记录与 chunk 文件 |
| 2 | 三册《食物与厨艺》独立来源 | **通过** | 三个独立 `source_id` 与卷册字段 |
| 3 | 新增知识保留书名/章节/页码溯源 | **通过（机器可核验）** | 页级 `pdf_page` 与 chunk citation 一致；Flavor Bible 有 25 条 `printed_page` 异常，已列入 known issues |
| 4 | Flavor Bible 独立搭配索引 | **通过** | 640 条目、13,758 去重关系、292 affinities、复核队列 |
| 5 | Food Chemistry 独立化学索引 | **通过** | 2,319 主题、24 章、863 页 |
| 6 | 原有四书数据与引用不损坏 | **通过** | Phase 1 基线 1,975 页 / 2,589 片段保持不变 |
| 7 | 五个专业模块能调用新增知识 | **通过（指令层）** | SKILL、references、workflows 已加入 Phase 2 来源分工 |
| 8 | 八种工作流能调用新增知识 | **通过（指令层）** | `workflows/01`–`08` 均已增加 Phase 2 规则 |
| 9 | 原有测试全部通过 | **通过** | E01–E10 与第一阶段基线逐字节一致，自动部分 900/900 |
| 10 | 新增测试全部执行并记录 | **通过** | E11–E30 共 20 例，1800/1800；pytest 58 passed |
| 11 | 不伪造页码、引文、实验结论 | **机器检查通过，人工语义仍待复核** | 引用校验 0 错；未做实验，所有菜谱只能标设计/待验证 |
| 12 | 完整报告与回滚方案 | **通过** | 本目录 7 份报告 + `backups/` 回滚材料 |

第 11 项不得由自动脚本证明“所有语义都正确”。例如 OCR 错字、The Flavor Bible 三栏串行、表格候选误判，均需人工回页复核。因此报告使用“机器检查通过”而不是“专业正确性已确认”。

> `backups/` 是本地回滚材料，已加入 `.gitignore`，不随 Git 仓库发布；仓库只保留可重建的脚本、配置和当前知识库数据。

---

## 4. 已完成的交付

| 交付项 | 位置 | 状态 |
|---|---|---|
| Skill 入口与十书范围 | `SKILL.md` | 已完成，版本 0.2.0 |
| 项目说明 | `README.md` | 已更新为十书状态 |
| 食品化学模块 | `references/food-chemistry/`、`data/chemistry_topics.jsonl` | 已完成索引与边界说明 |
| 风味搭配引擎 | `references/flavor-pairing/`、`data/flavor_pairings.jsonl` | 已完成索引、复核队列与证据分级 |
| 烹饪原料参考 | `references/culinary-ingredients/` | 已完成 |
| 八种工作流 | `workflows/01`–`08` | 已完成 Phase 2 升级 |
| 统一食材模型 | `schemas/ingredient.schema.json` | 已增加 20 个可选 Phase 2 字段 |
| 搭配模型 | `schemas/flavor-pairing.schema.json` | 已创建并通过 Draft 2020-12 校验 |
| 冲突复核工具 | `scripts/build_conflict_candidates.py` | 已创建；2 条候选，0 条已确认冲突 |
| 中文专业词检索桥 | `config/professional_terms.json` + `scripts/search.py` | 已创建；30 个词头、52 个英文扩展 |
| 视觉候选清单 | `data/images/manifest.jsonl` | 已扩展到十书，6,811 条 |
| 专业测试集 | `evals/cases/E01`–`E30` | 30 例；E01–E10 保持原样；E26/E27 的未核实 rosemary 已改为可核验的 TARRAGON–CHICKEN |
| 自动验证 | `scripts/validate_kb.py`、`run_evals.py`、`pytest` | 171/171、2700/2700、58 passed |

---

## 5. 版本与知识边界

- *Food Chemistry* 是 **2009 年第 4 版**，不是现行食品安全标准，也不是最新法规或营养指南。
- 《烹饪原料学》是 **2003 年教材**，其分类、品质检验和行业规范不得直接当作现行标准。
- *The Flavor Bible* 是 **创意搭配参考**，不是经过统一感官实验验证的相容性数据库。
- 传统本草内容来自《中药学》，属于传统理论，不是现代医学疗效证据，也不构成个体化处方或用药建议。
- 十书没有覆盖的内容统一标记为「当前十书知识库暂无充分依据。」
- 现有菜谱只代表**设计参数**，没有厨房实验或消费者感官数据；不得写 `kitchen_tested`。

### 5.1 备份与回滚

| 备份 | 实际内容 | 验证 |
|---|---|---|
| `backups/20261117-pre-phase2.zip` | 升级前项目快照，18,878,204 B | SHA-256 `1CE7CAE7F201CB31D3966C294011690DE12A5E7BD4938CF2E7318FA9D1D409DD` |
| `backups/knowledge-phase1.sqlite` | 第一阶段数据库 | `integrity_check=ok`；sources=4；pages=1,975；chunks=2,589 |
| `backups/phase1_baseline.json` | 第一阶段页/chunk/引用基线 | 与 `validate_kb.py` 基线检查一致 |
| `backups/visual-manifest-phase1.jsonl` | 第一阶段视觉清单 | 保留，未覆盖 |

回滚原则：

1. 不删除当前 `data/index/knowledge.sqlite`，先复制为带时间戳的回滚副本。
2. 用 `backups/knowledge-phase1.sqlite` 恢复第一阶段数据库。
3. 恢复 `backups/phase1_baseline.json` 与 `backups/visual-manifest-phase1.jsonl`。
4. 重新运行 `validate_kb.py`、`run_evals.py --strict`、`pytest`，确认回到 1,975 页 / 2,589 片段基线。
5. 原始 PDF 保留在项目根目录，不移动、不删除、不提交。

---

## 6. 尚未完成的工作

1. 30 个评测用例的专业正确性 10 分项仍需人工/厨师/食品科学专家逐例复核。
2. 没有进行真实厨房实验、感官盲评、重复性验证或食品安全微生物检测。
3. 六张 Phase 2 食材卡仍为 `partial`；许多化学、品种、产地、季节字段为空，空值代表缺口，不代表已研究。
4. OCR 仍有错字和版面串行；低置信页只能作检索线索，不得单独支撑关键结论。
5. Flavor Bible 的 6,905 条复核队列尚未逐条人工确认；部分条目会混入菜名、厨师语录或 OCR 噪声。
6. Flavor Bible 有 25 条条目的 `printed_page` 与全书主流偏移明显不一致（涉及 12 个 PDF 页）；引用时应优先核对 PDF 页与原页页眉。
7. 表格候选 1,506 条尚未做单元格级结构化；图片图注尚未人工审核。
8. 没有引入向量数据库或神经语义检索；当前为 FTS5 + 字符 n-gram + 中文子串回退 + 少量专业词英译桥接。
9. 冲突复核队列只有候选机制，尚无经人工确认的真实冲突结论。
10. 自动评测使用内置参考答案，尚未做“现场生成回答”的独立评测。

---

## 7. 最终验证命令

```powershell
python ingredient-culinary-rd\scripts\validate_kb.py
python ingredient-culinary-rd\scripts\run_evals.py --strict
python -m pytest ingredient-culinary-rd\tests -q
```

最终结果：

```text
知识库一致性：171/171，0 失败
自动评测：30/30，2700/2700，引用硬错误 0
pytest：58 passed
```

详细记录见：

- `reports/phase2/BOOK_IMPORT_REPORT.md`
- `reports/phase2/KNOWLEDGE_EXPANSION_REPORT.md`
- `reports/phase2/FLAVOR_PAIRING_REPORT.md`
- `reports/phase2/FOOD_CHEMISTRY_REPORT.md`
- `reports/phase2/EVALUATION_REPORT.md`
- `reports/phase2/KNOWN_ISSUES.md`
- `reports/verification.log`（Phase 2 段）

**最终定位：** 可作为“十书范围内的可溯源食材研究、食品化学解释和研发辅助 Skill”使用；不是完整百科、不是医学处方系统、不是已经完成厨房验证的菜谱库。
