# 图像与表格候选清单

当前统计（十书，2026-11-17）：

- 视觉记录：6,811
- 内容图片：2,913
- 整页扫描：2,392
- 表格候选：1,506

分书明细见 `data/images/stats.json` 与 `references/knowledge-index/coverage.md`。
整页扫描记录数可能超过 PDF 页数，因为一页可包含多个全页图像 xref。

`manifest.jsonl` 保存：

- 图片或整页扫描的 `source_id`、PDF 页、可观察到的印刷页；
- xref、像素尺寸、bbox、覆盖比例；
- 邻近文字 `caption_candidate`；
- `caption_status`（一律为待人工复核或无可疑图注）；
- PyMuPDF 文本/线框启发式得到的 `table_candidate`（含 bbox、行列数与预览）。

注意：

1. **不把邻近文字冒充已确认图注**。`needs_human_review` 表示需要回看原页图像。
2. 扫描书的整页图片标为 `page_scan`，不与独立食材照片混为一谈。
3. `table_candidate` 只是线框密度候选，不是已结构化表格。
4. 本项目不重新分发书籍图片；原始 PDF 仍需由使用者合法持有。

重新生成：

```bash
python scripts/extract_visuals.py
```
