# Flavor Pairing Index

> 所有页码均以 `FB-PAGE-2008` 的记录为准。索引是创意检索工具，不是科学证明。

## 1. 高价值条目入口

| 条目 | 直接搭配数 | 印刷页 | PDF 页 | 用途 |
|---|---:|---:|---:|---|
| BASIL | 72 | 58–59 | 73–74 | 香草、番茄、蒜、橄榄油、水果 |
| CHICKEN | 61 | 115 | 130 | 香草、香料、蔬菜、炖烤方向 |
| BANANAS | 52 | 56 | 71 | 焦糖、香草、巧克力、奶油 |

计数是当前去重后数据库中 `ingredient_a` 的直接/推导记录数；并不是“科学相容性评分”。

## 2. 读取一条记录

```json
{
  "pairing_id": "…",
  "ingredient_a": "BASIL",
  "ingredient_b": "GARLIC",
  "relationship": "flavor_pairing",
  "evidence_level": "explicit_pairing_listing",
  "source_id": "FB-PAGE-2008",
  "printed_page": 58,
  "pdf_page": 73,
  "original_context": "…",
  "book_evidence": "…",
  "confidence": "high"
}
```

- `confidence=high` 表示该记录在当前抽取流程中较可靠，不等于感官效果已经被实验验证。
- `original_context` 是页面上下文，不应无条件当完整句子引用。
- 引用时优先写 `《The Flavor Bible》p.58（PDF 73）`，并说明是“条目直接列出”还是“组合推导”。

## 3. 查询模板

```bash
# 单侧条目
python scripts/search.py --pairing BASIL --top 30

# 精确二元关系
python scripts/search.py --pair BASIL TOMATOES

# 普通全文，适合处理大小写、别名和跨页
python scripts/search.py "basil tomato" --source FB-PAGE-2008 --top 20

# 回看条目页
python scripts/search.py --page FB-PAGE-2008:73
```

## 4. 组合推导的处理

Flavor Affinities 往往写成：

```text
A + B + C + D
```

索引会拆成 A–B、A–C、B–C 等二元记录，并标 `derived_from_affinity_combination`。这种关系表示“它们出现在同一组推荐中”，不表示书中逐字写了“A 和 B 是固定配对”，更不表示两两等强度。

## 5. 创新搭配的三层输出

| 层 | 允许的说法 | 必须附 |
|---|---|---|
| 书中直接 | “条目列出 / 书中记录” | 书名、页、条目 |
| 跨条目或跨书推理 | “可能形成 / 可探索” | 两条以上依据、推理链 |
| AI 假设 | “提出假设 / 待验证” | 变量、对照、感官指标 |

## 6. 禁止事项

- 不把 OCR 噪声当成食材名。
- 不把菜名、厨师名、餐厅名当成食材。
- 不用“同页出现”证明“可以同吃”。
- 不把搭配推荐解释为健康、营养或药理协同。
- 不在没有实验时声称验证成功。

