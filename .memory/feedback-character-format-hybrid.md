---
name: character-format-hybrid
description: 用户偏好人物条目采用 Markdown 主文加 JSON 底谱，并按固定职责拆分叙事层与结构层
type: feedback
---

规则：人物设定优先写成可直接阅读的 Markdown 正文，但应同时保留一层结构化 JSON，用于承载稳定字段、关系索引、能力边界与可复用细节。Markdown 主文默认覆盖概述、核心设定、身世行历、修行能力、关系位置、余响六类内容；JSON 底谱默认沉淀 identity、presence、turning_points、methods、relations、motifs、writing_hooks 等稳定结构。

**原因：** 用户认为人物写成 md 更适合阅读与沉浸，但 json 更适合表现人物各方面细节，希望两者结合。

**应用场景：** 编写角色小传、人物卡、阵营核心成员档案、主角与配角设定时，默认采用“md 主文 + json 底谱”的双层结构；需要批量扩写人物、维护人物数据库、统一角色卡格式时也优先按此方法执行。
