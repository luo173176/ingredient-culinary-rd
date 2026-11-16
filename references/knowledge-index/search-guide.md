# 检索指南

## 1. 命令

```bash
python scripts/search.py "花椒 温中止痛" --top 6
python scripts/search.py "西红柿" --mode semantic --top 8
python scripts/search.py "盐 渗透 入味" --source FS-SFAH-2023
python scripts/search.py "鲷鱼 加热烹调" --source DK-INGREDIENTS
python scripts/search.py --herb 花椒
python scripts/search.py --page CN-DIDAO-2011:40
```

## 2. 参数

| 参数 | 作用 |
|---|---|
| `--top` | 返回条数，默认 8 |
| `--source` | 限定一本书：`MM-ZYX-2016` / `CN-DIDAO-2011` / `FS-SFAH-2023` / `DK-INGREDIENTS` |
| `--mode keyword` | 所有词都要命中，精度高，适合已知术语 |
| `--mode semantic` | 任一词命中 + 字符 n-gram 重排，召回高，适合口语/别名 |
| `--content-type` | `text` / `recipe` / `attribute` / `heading` |
| `--page-kind` | `content` / `front_matter_or_appendix` |
| `--json` | 机器可读输出 |

## 3. 查询构造

### 3.1 食材名

先 canonical，再别名：

```bash
python scripts/search.py "番茄" --top 8
python scripts/search.py "西红柿" --mode semantic --top 8
```

### 3.2 属性词

```bash
python scripts/search.py "花椒 性味 归经 功效" --top 6
python scripts/search.py "花椒 产地 品种 采收" --top 6
```

### 3.3 工艺词

```bash
python scripts/search.py "盐 渗透 扩散 提前加盐" --source FS-SFAH-2023
python scripts/search.py "油脂 香气 乳化" --source FS-SFAH-2023
python scripts/search.py "酸 平衡 脂肪" --source FS-SFAH-2023
python scripts/search.py "热 传导 对流 辐射 美拉德" --source FS-SFAH-2023
```

### 3.4 章节过滤

```bash
python scripts/search.py "配伍 相须 相使 相畏 相杀" --source MM-ZYX-2016
python scripts/search.py "十八反 十九畏 妊娠禁忌" --source MM-ZYX-2016
```

## 4. 读结果

每条结果包含：

```text
[1] 《中药学》PDF 396 · 第十四章 温里药 · text · conf=high
    （证据摘要）
    score=12.5 exact=4 sem=0.0
```

- `citation`：直接用于回答的引用。
- `chapter/section`：定位。
- `content_type`：text/recipe/attribute。
- `conf`：OCR 可信度。
- `score`：排序分，不是事实置信度。
- `exact`：查询词在原文中的命中数。
- `sem`：字符 n-gram 相似度（仅 semantic 模式）。

## 5. 回溯整页

```bash
python scripts/search.py --page MM-ZYX-2016:396
python scripts/search.py --herb 花椒
```

写引用卡或关键结论前，必须回看整页，避免断章取义。

## 6. 常见问题

| 现象 | 处理 |
|---|---|
| 搜不到 | 换别名/上位词/章节词；确认该书是否收录 |
| 结果太多 | 用 `--mode keyword`、加书过滤、加属性词 |
| 结果不相关 | 用 `--mode semantic` 或换更具体的术语 |
| OCR 错字 | 用页面图像复核；不要用错字做关键词 |
| 页码是 null | 该书没有可观察的印刷页码，引用 PDF 页 |

## 7. 不要做

- 不要直接把 snippet 当全文引用。
- 不要用排序分证明“更正确”。
- 不要跨书拼凑一句话。
- 不要把 `query_hint` 别名当书里的原话。
