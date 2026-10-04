# 人物条目写作规范（角色目录）

本规范适用于 `角色/九州人物/`、`角色/神族人物/` 及本目录树下全部人物条目（含 `.md` 正文与 `.json` 底谱）。全仓库通用的文件结构、交叉引用与标签规则详见根目录 `AGENTS.md`，本文件专门确立人物类别的增量专属约束与规范基准。

## 双文件铁律

人物条目统一采取“Markdown 为正篇叙事、JSON 为底谱结构”的双轨范式，二者相辅相成、缺一不可。凡新建、扩写或重修人物设定，必须同步交付或同步修订双文件：

- **Markdown 层**承载叙事质感与沉浸氛围——神采风貌、命运因果、感官气味、举止动静以及人物与世界的深度羁绊。
- **JSON 层**承载严谨架构与索引基准——字段边界、枚举关系、阶段节点与可复用标签。

既不可将鲜活人物肢解为冰冷干瘪的数据清单，亦不可使核心设定淹没于泛泛抒情之中难以结构化检索。

## Markdown 层：固定六段职责

各篇虽可依人物性情灵活化裁文辞，但以下六段的核心职责必须稳定严谨：

1. **概述**：以一至三段立住人物的巍然气象或苍凉风骨。不堆砌机械履历，先勾勒此人登场时天地风物为之改观的画面感与气场；随之点明其人格底色与精神追求，使人物先立于纸上再徐徐展开。
2. **核心设定**：直接阐明此人于宏观世界观中的枢纽位置——他承载何种时代潮流，其修行法理填补了何处空缺，又与既有秩序存在怎样不可调和的根本冲突。
3. **身世与行历**：遵循严密的命运因果而非流水账式的年纪编年。重心不在于“何年何月经历何事”，而在于“哪几场刻骨铭心的劫波与抉择，将其塑造成了如今的风貌”。
4. **修行与能力**：严禁罗列孤立的招式名称。每一项标志性手段均须交代三项要素：它应对何种现实困局、展现出何等震撼的感官与天地异象、潜藏着怎样沉重的反噬代价或法理边界。
5. **关系与位置**：人物绝非孤岛。深刻剖析其与同道知己、宿敌对头、宗门道统、地脉风物及时代大潮之间的纵横牵连。
6. **传闻与遗音**：以一两则坊间流言、故人追忆或一两句苍凉余音作结，使人物风骨与余韵自然绵延，胜过孤立罗列名言警句。

## JSON 层：底谱骨架

底谱以 `角色/九州人物/东阳.json` 为基准范式（`schema_version` 2.0）。新撰底谱统一遵循下述架构；其中 `governance_profile` 仅执掌权柄、经纬天下的人物需要，寻常修者或市井人物可予省略。`canonical_name` 依既定规约录入与双链同名的字符串（如 `"[[东阳]]"`）。

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

结构化列表元素必须使用对象封装而非裸字符串，字段严格契合既有底谱规范：

- `turning_points` 元素：`stage`（人生阶段）、`summary`（关键转折）、`sensory_impression`（感官印记）、`world_effect`（对世界格局之深远影响）。
- `signature_methods` 元素：`name`（功法术名）、`gist`（法理要旨）、`imagery`（天地意象）、`cost`（反噬代价）。
- `artifacts` 元素：`name`（器物名称）、`type`（器物类型）、`description`（器相描述）、`function`（核心威能与权责）。
- `relations` 各列表元素：`name`（人物双链）、`bond`（羁绊纽带）、`dynamic`（交互张力与动态）。

## 底谱设计原则

1. **JSON 沉淀“稳定事实”，Markdown 升华“叙事呈现”**：例如“其袍袖间常带潮湿旧木与药灰气息”作为稳定感官印记存入 `scent`；而该气息如何在雨夜中勾起旧时炉堂回忆，则交由 Markdown 正文铺展。
2. **字段直接赋能正文扩写**：`turning_points`、`scene_seeds` 与 `signature_methods` 的设立，旨在为后续场景构建、支线推演与追忆回叙提供可随时调用的抓手，而非单纯为了填塞空泛资料。
3. **严禁现实原型标签化裸露**：不得设立“现实映射”、“原型对照”等直白标签。即便人物确实借鉴了现实历史之风骨，字段亦必须全然转译为世界内话语——保留“时代角色”、“权力逻辑”与“阵营博弈”，彻底剔除“现实原型为何人”的直白痕迹。
4. **将“代价与制约”融入结构**：弱点、代价、禁忌与失控条件必须在底谱中有明确载体（如 `taboos` 及能力的 `cost` 等）。正文虽未必篇篇详述，但底层架构中不可或缺；人物一旦唯余神威与光环，其神秘感与命运厚度必迅速流失。

## 撰写推进时序

- **若人物定位繁复厚重**：宜先构筑 JSON 底谱骨架、划定法理边界与人际网络，而后执笔 Markdown 正文，防止行文漫无边际。
- **若人物气质玄妙多变**：宜先通过 Markdown 正文深描探索人物神采与语态，待其风貌凝定之后，再将核心事实沉淀归入 JSON 底谱结构。
