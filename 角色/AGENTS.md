# 人物条目写作规范（角色目录）

本规范适用于 `角色/九州人物/`、`角色/神族人物/` 及本目录树下全部人物条目（含 `.md` 正文与 `.json` 底谱）。全仓库通用的文件结构、交叉引用、标签规则见仓库根目录的 `AGENTS.md`，本文件只写人物类别的增量约束。

## 双文件铁律

人物条目以 Markdown 为正篇、以 JSON 为底谱，两者缺一不可，新建、扩写、重写时必须同步产出或同步修订：

- `md` 层承载叙事与氛围——观感、因果、气味、动作、人物与世界的勾连。
- `json` 层承载结构与索引——字段边界、枚举关系、阶段节点、可复用标签。

既不把人物写成冷冰冰的表格，也不让关键细节淹没在大段抒写里难以抽取。

## Markdown 层：固定六段

不必逐字照搬，但六段职责必须稳定：

1. **概述**：用一到三段立住人物的整体气象，不交代履历清单，先让读者知道这人站出来时天地会变成什么样子；随后点出人格类型，让人物先立住再展开。
2. **核心设定**：直接点明此人之于世界观的功能——他代表哪一股时代力量、修行逻辑补上了什么空缺、与旧秩序的根本冲突在哪里。
3. **身世与行历**：按因果写，不按流水账写。重要的不是"几年做了什么"，而是"哪件事把他推成了现在这个样子"。
4. **修行与能力**：不只列招式名称。每个核心能力同时带上三件事——它解决什么问题、它呈现什么视觉或感官印象、它潜藏什么代价或边界。
5. **关系与位置**：人物不是孤岛。写清他与同道、对手、宗门、法统、地理、时代之间的连接线。
6. **传闻与遗音**：用一两则小事或一两句余音收尾，比单独堆"名言"更容易留下人物余温。

## JSON 层：底谱骨架

底谱以 `角色/九州人物/东阳.json` 为基准样本（`schema_version` 2.0）。新写底谱按下述结构取用；`governance_profile` 仅掌权、治事人物需要，其余人物可省略。`canonical_name` 的值按既有惯例写成与双链同名的字符串（如 `"[[东阳]]"`）。

```json
{
  "schema_version": "2.0",
  "id": "ascii_id",
  "canonical_name": "[[东阳]]",
  "public_titles": ["称呼一", "称呼二"],
  "narrative_role": "",
  "demographics": {
    "gender": "",
    "apparent_age": 0,
    "actual_stage": ""
  },
  "identity_matrix": {
    "core_drive": "",
    "worldview": "",
    "greatest_fear": "",
    "fatal_flaw": "",
    "public_mask": "",
    "private_truth": ""
  },
  "embodied_presence": {
    "silhouette": "",
    "face": "",
    "hair": "",
    "eyes": "",
    "scent": "",
    "voice": "",
    "notable_marks": []
  },
  "biography": {
    "origin": {
      "birth_region": "",
      "family_background": "",
      "father": "",
      "mother": "",
      "social_position": ""
    },
    "turning_points": [
      {
        "stage": "",
        "summary": "",
        "sensory_impression": "",
        "world_effect": ""
      }
    ]
  },
  "cultivation_profile": {
    "current_realm": "",
    "path": "",
    "doctrine": "",
    "signature_methods": [],
    "artifacts": []
  },
  "governance_profile": {
    "faction": "",
    "position": "",
    "leadership_style": "",
    "strategic_strength": "",
    "strategic_blind_spot": ""
  },
  "relations": {
    "allies": [],
    "rivals": [],
    "mentors": []
  },
  "motifs": {
    "colors": [],
    "elements": [],
    "symbols": []
  },
  "writing_hooks": {
    "scene_seeds": [],
    "taboos": []
  }
}
```

结构化列表元素用对象而非裸字符串，字段沿用既有底谱：

- `turning_points` 元素：`stage`（人生阶段）、`summary`（事件）、`sensory_impression`（感官印象）、`world_effect`（对世界的改变）。
- `signature_methods` 元素：`name`、`gist`（要旨）、`imagery`（意象）、`cost`（代价）。
- `artifacts` 元素：`name`、`type`、`description`、`function`。
- `relations` 各列表元素：`name`、`bond`（关系纽带）、`dynamic`（关系动态）。

## 底谱设计原则

1. **JSON 记"稳定事实"，MD 负责"表现事实"**："他衣上有潮木和药灰气息"这类可复用细节进 `scent`；那气息在雨夜里如何让人联想到旧炉堂，留给 MD 展开。
2. **字段直接服务扩写**：`turning_points`、`scene_seeds`、`signature_methods` 是为后续写场景、写支线、写回忆时可直接调用而设，不是把人物资料塞满。
3. **禁止现实映射裸露在表层**：不得使用"历史映射""原型对应"类直白字段。即便人物确实借现代历史为骨，字段也要写成世界内语言——保留"时代角色""权力逻辑""阵营关系"，不保留"现实原型是谁"的明示标签。
4. **把"代价"写进结构**：限制、代价、禁忌、失控条件必须在底谱中存在（`taboos`、能力的 `cost` 等）。正文不一定每次展开，但设定层不能缺席——人物一旦只有能力和光环，神秘感会很快变廉价。

## 撰写顺序

- 人物定位复杂：先定 `json` 骨架、明确边界，再写 `md`，避免正文越写越散。
- 人物气质难抓：先把 `md` 写熟，再把稳定设定沉淀回 `json` 结构。
