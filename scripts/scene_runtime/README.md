# 场景运行层

此工具验证显式策划的材料，按接收者组装 JSON 输入包，并从同一开场依据创建预演分支。它不连接模型、不生成对白、不执行状态变化，也不修改正式正文、人物底谱或时间线。

普通场景可在任务依据表中完成轻量策划，无需运行本工具；长期复用时可存为根目录 `场景/` 下的 `策划.md`。仅复杂信息隔离、多分支或可重放任务启用 `scene.json`、哈希和组包，启用后下述 v1 严格契约全部有效。策划卡不是正式内容来源，不能用作 `target_paths` 或 `accepted.final_source`。入口见 [`场景/README.md`](../../场景/README.md)，规范见 [`场景/AGENTS.md`](../../场景/AGENTS.md)。

实施路径见 [PLAN.md](PLAN.md)。Python 3.10 及以上可运行工具；代理 TOML 检查另需 Python 3.11 及以上的 `tomllib`。仅使用标准库，无需安装依赖。

## 使用

在项目根目录运行，`python` 须指向可用的 Python 环境：

```powershell
python scripts/scene_runtime.py validate 场景/茶馆闲聊/第一回开场/scene.json
python scripts/scene_runtime.py build 场景/茶馆闲聊/第一回开场/scene.json --audience director --output .workbench/runs/replay-director.json
python scripts/scene_runtime.py build 场景/茶馆闲聊/第一回开场/scene.json --audience writer --output .workbench/runs/replay-writer.json
python scripts/scene_runtime.py build 场景/茶馆闲聊/第一回开场/scene.json --audience actor --actor laoshu --output .workbench/runs/replay-laoshu.json
python scripts/scene_runtime.py build 场景/茶馆闲聊/第一回开场/scene.json --audience actor --actor shenxianggong --output .workbench/runs/replay-shenxianggong.json
python scripts/scene_runtime.py fork 场景/茶馆闲聊/第一回开场/scene.json --branch-id alternative --output .workbench/runs/replay-alternative.json
python -m unittest discover -s scripts -p "test_*.py" -v
python scripts/check_crossrefs.py --check-links "故事/茶馆闲聊/灯下短论/1. 茶馆闲聊·英雄.md"
```

`build` 与 `fork` 不给 `--output` 时只打印 JSON。显式输出只允许位于本项目 `.workbench/runs/`，文件必须尚不存在；不覆盖来源、清单或正式内容。重复执行时改用新文件名。

测试可传 `--root` 使用独立夹具根目录；`--temp-output-dir` 仅允许系统临时目录内、项目外的现有独立子目录，不扩展正式内容写权限。默认不联网、不修改输入。

`validate` 验证来源、结构与导演包总预算，退出码 0 表示通过，2 表示失败。演员组包失败只给通用错误，请由导演运行 `validate` 获取诊断。双链目标检查退出码 1 表示错链或歧义，2 表示检查请求失败。

## 清单 v1

顶层字段均必填，拒绝未知字段及重复 JSON 键：

| 字段 | 内容 |
| --- | --- |
| `version` | 整数 `1` |
| `scene` | 场景标识、时点、目标路径、预算、适用审校 |
| `branch` | 当前分支和父分支基础记录 |
| `sources` | 可定位、可验证的证据来源列表 |
| `actors` | 每人的策划 persona、开场状态、信念与言谈分寸 |
| `facts` | 已核实的开场事实，以 atom 表示 |
| `public_history` | 开场已经发生的消息或观察，以 atom 表示，仍逐人授权 |
| `unknowns` | 人物未知的导演信息，禁止授权给演员 |
| `events` | 候选变化或有审校依据的采纳事件 |

场景、人物、事件及分支 ID 使用 ASCII 字母、数字、下划线和连字符，1–80 字符；来源 ID 使用 16–64 位小写十六进制，避免语义名称暴露隐藏线索。时间轴名称只要求为非空字符串。来源 ID 全局唯一，人物 ID 与事件 ID 在各自列表唯一。

### 场景与时间

`scene` 必含：`id`、`title`、`time`、`target_paths`、`budget_chars`、`required_reviews`。

- `time` 为 `{ "timeline": "teahouse-episodes", "order": 1, "label": "第一回开场" }`，`label` 可省略。`order` 是策划者定义的整数顺序，不是公历日期或程序推断的纪年。
- `target_paths` 是正式目标 Markdown 路径列表，新条目可以尚未存在。每个路径沿途的现存 `AGENTS.md` 和根规范全文自动进入导演、写手包。
- `budget_chars` 是正整数，统计最终序列化 JSON 的 Python 字符数，包含元数据与规范；不是字节数或模型 token 数。首版全部保留已选必需材料，超限失败，不排序裁剪。
- `required_reviews` 至少包含 `tone`、`crosslink`；有演员须加 `character`，目标路径至少三个须加 `worldbuilding`。实际任务若涉及更广一致性问题，主架构师仍须主动追加。

所有来源时间轴必须与场景相同，且覆盖场景顺序。首版不换算纪元，不从语义判断制度何时形成。技术回放的时间范围是对所选摘录的人工确认，不代表来源整篇及其所有经历都适用于该时点。

### 来源

每项必含 `id`、`path`、`start_line`、`end_line`、`sha256`、`valid_from`、`disclose_to`；可选 `valid_until`。

- `path` 必须精确匹配项目相对 POSIX 路径，保留中文、空格、大小写及标点；不得使用绝对路径、反斜线、`..` 或跳出项目的目录链接。
- 行号从 1 开始、首尾均包含；内容按 UTF-8 读取，允许 BOM。
- `sha256` 固定**整个文件原始字节**。任何修改，包括换行变化，都会使旧清单失效；须重新阅读并确认摘录后更新，不能为消除报错盲目重算。
- 时间边界采用 `{ "timeline": "teahouse-episodes", "order": 1 }`；起止均包含，不填截止即表示尚未限定。
- 来源 `disclose_to` 只能含 `director`、`writer`；导演始终可见全部。演员不接收原始来源，只接收策划者审核过的 atom 文本。

哈希计算可用 `Get-FileHash -Algorithm SHA256 -LiteralPath <文件路径>`，写入小写摘要。源文件变化后，应重新审核正文和全部引用该文件的清单。

### 策划文本 atom

```json
{
  "text": "经核对的材料或策划要求",
  "source_ids": ["0123456789abcdef"],
  "disclose_to": ["director", "writer", "actor:laoshu"]
}
```

三个键均必填；文本非空，来源至少一个且必须存在，授权对象不得重复。`actor:<id>` 必须指向本场人物。示例中的来源标识只是格式展示，不是有效依据。

**来源可见性与文本可见性分别控制。** 作者/写手掌握真相、人物知道/相信/能说什么、读者在本段视点获知什么是三个判断。为伏笔、潜台词或反讽所需的真相，可继续用现有 `disclose_to` 显式授权 `writer`，并在策划或文本中说明呈现方式；本次不增读者字段。导演可从私密原文提炼获准材料，原文不因材料获准就自动进入包。人物未知秘密始终不得授权演员，人物知情也不等于可以当众说出。

人物未知的导演信息（`unknowns`）不允许 `actor:*`。`public_history` 中的“公开”只表示可用于记录公共观察，不表示所有人物自动知晓，仍须逐人授权。工具不判断文本真假或核查摘录是否支持断言，这由研究和审校完成。

### 人物

每人必含 `id`、`name`、`persona`、`beliefs`、`state`、`speech_limits`，后四项都是 atom 列表，允许空列表。

- `persona`：从人物稳定底谱与审定正文策划出的本场人格、语态材料，不是整个 JSON 副本。
- `beliefs`：本人相信、怀疑或误会的内容与来路，不自动升级为 `facts`。
- `state`：开场位置、在场理由、伤势、目标等经过核对的信息。
- `speech_limits`：本人已知但需要遮掩的言谈分寸，不把作者真相写成“你不知道的秘密是……”再送给人物。

个人卡只能授权本人演员及导演/写手，不能授权另一名演员。其他人可以观察的动作另记公共材料或事件。角色包不输出导演时点标签、场景标题或分支标识；需要的时令与环境应通过授权材料提供。

## 输入包与实际调度

| 对象 | 包内范围 |
| --- | --- |
| director | 全部策划材料、来源摘录、披露标记、分支与规则全文 |
| writer | 显式获准的来源/材料/人物卡/事件，以及目标规范全文；隐藏来源的引用 ID 不输出 |
| actor | 本人获准卡片、事实、观察和事件；文本不附来源 ID、路径、哈希、他人卡或 `unknowns` |

共享材料必须先确认对每名接收者成立。将包交给模型前，仍要检查选材、时代和措辞；自动加载规范不等于自动完成阅读与审校。

仅在用户要求，或主架构师已决定针对具体创作难题启用预演时调度人物。场控保留导演包，独立人物调用使用当前环境实际提供的无继承方式，如 `fork_turns="none"`，仅交付本人包与当前可见要求，不再次传入导演历史。不设默认轮数、每轮反应数或人人接话要求；若难题解决或无新增价值即停止，结果交写手自由剪裁。

本工具不调用 `spawn_agent`，不分配角色发言顺序，不禁止模型读取其他项目文件，不构成文件权限沙箱。首版组包是一次性快照；新一轮听闻与状态变化须由场控明确审核并形成下一轮输入。

## 事件、分支与回填

`events` 每项必含 `id`、`order`、`branch_id`、`status`、`text`、`source_ids`、`disclose_to`。顺序不能晚于场景，分支必须为当前分支。

`candidate` 表示待取舍材料，不能带 `final_source` 或 `reviews`。对白“甲说了 X”只能证明发生了这句话，不能证明 X 为真。开场事实、个人卡与信念不随候选原地变更，候选变化仅存事件。

`accepted` 额外要求 `final_source` 引向正式内容目录内的 Markdown 来源；`reviews` 必须同时给出四键：

```json
{
  "tone": "passed",
  "crosslink": "passed",
  "character": "passed",
  "worldbuilding": "not_applicable"
}
```

`required_reviews` 内的审校必须为 `passed`，其余为 `not_applicable`。标记必须对应真实审校报告，工具不能核实它是否属实。采纳记录不会自动更新正文或底谱。

`branch` 为 `{ "id": "main", "parent": null }`，或包含父分支 `{ "branch_id": "original", "base_event_ids": [] }`。父分支不能为自身，基础 ID 必须唯一并引用本清单保留的采纳事件。

`fork` 复制同一开场快照、保留采纳基础事件并改为新分支归属，记录父分支与基础 ID，删除候选及其独占来源。它不执行事件变化，不自动恢复任意历史时刻，也不能从单清单验证整张外部分支图是否成环。

正式回填仍由主架构师在成文和适用审校通过后执行：时间线记录正式变化；长期人物变化同步更新 MD 与 JSON；临时场景和分支不进入 `.memory/`。

## 回放与检查范围

[回放样例](../../场景/茶馆闲聊/第一回开场/scene.json)仅选取第一回《谁可称英雄》的开场环境及两名人物的稳定语态，止于席间闲谈开始之前。原文文件名中的序号后有一个空格，清单按真实路径保存。

样例不使用人物当前境界和后来行历、不续写对白、不新增事件或宣称完成真实人物演出。老舒的恐惧明确标为心理材料，仅在本人 persona 中供导演查看；它不是已发生事实，`unknowns` 留空。全部正式原文保持不变。

双链 `--check-links` 模式只读检查指定范围内严格的 `[[filename]]` 目标，包括单字名和同名歧义；不自动改名或支持别名/锚点语法。旧文若检出历史错名应另列修复范围，不能为让示例通过擅改整库。

运行目录与技术目录不属于正式双链索引。现有裸词模式仍是启发式辅助，不能替代专业交叉引用审校；本工具不解析自然语言因果、境界或消息传播。
