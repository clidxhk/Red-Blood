# 世界约束卡

本目录将选定来源中的法理摘要整理为人工审阅用的约束卡。本轮提供字段约定、十张卡片和判断示例，不提供激活器、自动判错引擎或正式设定写回功能。

## 文件

| 文件 | 用途 |
| --- | --- |
| [BASELINE.md](BASELINE.md) | 十项规则的来源与适用边界 |
| [CONFLICTS.md](CONFLICTS.md) | 三项待裁定事项及一项解释说明 |
| [cards.json](cards.json) | 来源、规则、边界与待裁定关联 |
| [examples.json](examples.json) | 25 个短判断示例及人工预期标签 |

这些文件属于派生索引，不新增正式设定，不证明全库没有冲突。示例均为技术假设，不代表世界中真实发生的事件。

## 卡片字段

`cards.json` 使用 `format_version: 1`、`document_type: world_constraint_cards`、`authority: derived_index`，并通过 `baseline`、`conflict_register` 指向本目录两份索引。

| 字段 | 必须保留的内容 |
| --- | --- |
| `sources` | 来源列表；每项有唯一 `id`、项目相对 POSIX `path`、全文件原始字节 `sha256` |
| `rules` | 规则列表；每项有 `id`、`status`、`statement`、`scope`、`boundaries`、`evidence`、`retrieval_hints`、`pending_conflict_ids`、`review_mode` |
| `scope` | 主题 `domains`、适用条件 `applies_when` 与时间状态 `temporal_status` |
| `boundaries` | 边界列表；每项含 `basis` 和 `text`，区分明文与缺证推导 |
| `evidence` | 来源定位列表；每项含 `source_id` 与 `line_ranges`，行段含 `start`、`end`，从 1 开始、首尾均包含 |
| `retrieval_hints` | 检索词 `keywords` 与关联 `related_rule_ids`，仅用于提示相关性 |
| `pending_items` | 待裁定列表；每项有 `id`、`status`、`type`、`summary`、`evidence`、`safe_usage` |
| `interpretation_notes` | 解释说明列表；每项有 `id`、`status`、`summary`、`evidence` |

编号在各自列表内唯一；所有来源、规则、待裁定及解释说明引用必须存在。数组无内容时保留空数组，不能用缺字段表示无关联。

`status: confirmed_in_selected_sources` 仅表示命题得到列明来源支持，不代表已完成全库核定。`temporal_status: unspecified_in_sources` 表示本轮未从来源提取统一起止边界，不能理解为没有任何时代条件或创世以来永久有效。

`boundaries.basis` 分为 `source_stated` 与 `unsupported_inference`。后者标出缺乏支持的推导，不能改写成“原文明禁”或“世界中绝不可能”。已知适用例外通过条件与边界表达，未列例外不等于证明不存在例外。

检索词和关联关系不是逻辑表达式，也不要求无限递归加载。`pending_conflict_ids` 提醒审阅关联事项，不推翻规则中独立成立的明文。`pending_items` 的 `pending_resolution` 不进入已确认规则。

`review_mode: human_semantic_review` 表示需要人工及专业审校代理理解和应用。不设置规则优先级数字、战力换算值或未经来源规定的永久起止时间。本轮无 JSON Schema 或可复用校验器；字段约定以本文和对应 JSON 为准。

## 判断示例

`examples.json` 使用 `format_version: 1`、`document_type: human_review_examples`、`authority: illustrative_not_canon`，通过 `cards` 引用卡片文件。

每例包含 `id`、`rule_ids`、`pending_conflict_ids`、`interpretation_note_ids`、`statement_type`、`text`、`expected_assessment`、`rationale`，至少关联一条规则、待裁定项或解释说明。

`statement_type` 分为 `world_fact`、`character_claim`、`hypothesis`、`comparison`。其中 `world_fact` 表示待审文本以事实口吻作断言，不代表该文本已经成立。

`expected_assessment` 是人工审阅的预期标签，不是程序推理结果：

| 标签 | 含义 |
| --- | --- |
| `compatible_with_selected_rule` | 与所选规则相容；不因此证明事件已经发生 |
| `conflicts_with_selected_rule` | 陈述与所选规则直接抵触 |
| `needs_evidence` | 现有依据不足，须补查机制、条件或实际效果 |
| `pending_resolution` | 判断依赖尚未裁定的来源口径或比较边界 |

先辨认陈述类型，再判断内容。人物可以表达错误主张；主张能否被表达与声称的功能是否成立要分开审阅。E21 的缺证标签针对功能的事实确认，不否认人物能说出此话，也不表示补证可以自动推翻 R03。不得因出现“消业”等词就直接判定冲突。

## 人工使用顺序

1. 明确主体、时代、对象及陈述类型。
2. 按相关性查找规则，同时阅读条件、边界和待裁定关联。
3. 回读证据原文；真实创作仍须完整加载目标目录类别 `AGENTS.md`，并按根规则补齐相关规范。
4. 对照示例作人工判断，记录理由与需要补查的问题。
5. 来源哈希变化时，重读原文并核对摘要、行号和边界，不能只刷新哈希。换行或编码变化也会使原始字节哈希失效。
6. 待裁定事项交主架构师按任务授权处理，不自行选择全库新口径。

结构与引用核对通过，不等于语义审阅通过。约束卡不能替代检索依据表、多维审校或主架构师决断，目前也未接入 `scene_runtime`。

下一步再设计按任务检索与激活规则的流程；不把本轮人工标签统计当作自动判错准确率。
