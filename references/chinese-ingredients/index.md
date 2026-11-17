# 中国地道食材 · 卡片索引

> 来源：《中国地道食材图录大全》（李清，武汉出版社，2011）。扫描版 OCR；页脚可见时保留 `p.X（PDF Y）`。

当前有 **8** 张人工校对的食材卡。未建卡的食材请直接用 `search.py` 检索页级原文；**卡片数量不等于全书覆盖**。

## 卡片

| 食材 | 英文 | 证据条数 | 主要来源 | 卡片 |
|---|---|---|---|---|
| 绿豆 | mung bean | 17 | CN | [ingredients/绿豆.md](ingredients/绿豆.md) |
| 芸豆 | kidney bean | 12 | CN | [ingredients/芸豆.md](ingredients/芸豆.md) |
| 黑豆 | black bean | 9 | CN | [ingredients/黑豆.md](ingredients/黑豆.md) |
| 苦瓜 | bitter melon / balsam pear | 20 | CN | [ingredients/苦瓜.md](ingredients/苦瓜.md) |
| 莲藕 | lotus root | 16 | CN | [ingredients/莲藕.md](ingredients/莲藕.md) |
| 香菇 | shiitake | 15 | CN | [ingredients/香菇.md](ingredients/香菇.md) |
| 花椒 | Sichuan pepper / prickly ash | 22 | CN / MM | [ingredients/花椒.md](ingredients/花椒.md) |
| 八角 | star anise | 11 | CN | [ingredients/八角.md](ingredients/八角.md) |

## 章节起止页（PDF）

| 章 | 起始 PDF 页 |
|---|---|
| 第一章 谷物和米面制品 | 27 |
| 第二章 乳制品和蛋 | 61 |
| 第三章 蔬菜 | 75 |
| 第四章 水果 | 125 |
| 第五章 坚果 | 160 |
| 第六章 肉 | 178 |
| 第七章 鱼虾蟹贝 | 203 |
| 第八章 调味品 | 229 |

## 全书检索

```bash
python scripts/search.py "绿豆 别名" --source CN-DIDAO-2011 --top 8
python scripts/search.py "苦瓜 做法" --source CN-DIDAO-2011 --mode semantic
python scripts/search.py --page CN-DIDAO-2011:40
```

## 使用注意

1. 这本书的 OCR 阅读顺序常被多栏版式打乱；**引用整段前必须回看页面图像**。
2. 卡片只引用可核对的短句，并在证据表标 `conf`；`low` 只作线索。
3. 书中的“性味/功效/食疗”属传统饮食经验，不是现代医学结论。
4. 没有卡片的食材，不要凭模型记忆补写；检索不到就写「当前十书知识库暂无充分依据。」
