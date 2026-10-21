# 经典小说素材：证据先行的离线工作流

当前工具负责登记、切章、导出原文、导入带证据的陈述、校验位置、登记语义复核及生成审计报告。不自动调用模型，不自动写正式设定，不承诺完整章节召回。

## 本次修复

- 移除《牧神记》前十章的硬编码“提取”，不再生成虚构证据与偏移。
- 严格解码，失败即停止；同一来源 ID 不可覆盖注册，换版本必须换 ID。
- 每项陈述绑定章节哈希、章内 Unicode 码点范围和真实原文片段。位置相符仅记 `evidence_checked`，不等于内容归纳正确。
- 原文语义由人或当前会话回读复核，留下复核者和具体理由后才记 `verified`。复核登记是声明记录，程序不能证明复核真正发生，不能当作质量认证。
- 修改陈述产生新 ID，不继承原审核；完全相同的重复导入保留已有复核结果。导入为追加式，错误陈述用拒绝登记处理，不会被新一版响应静默删除。
- 实体按来源版本、名称与类别隔离。只有该实体全部陈述通过复核且证据仍匹配，才能套用转化建议模板。
- 旧库迁移保留陈述与候选，但无证据定位的记录保持待复核，不继承旧 `verified`。旧实体不会自动归入新来源或参与转化。
- 报告按数据库实际状态生成，取消固定“10/10完成”和“已通过世界观审查”等断言。

## 使用

在仓库根目录运行，所有原文和包含原文的导出文件留在 `.workbench/novel_mining/`。可在子命令前传 `--db <路径>` 使用隔离的数据库，规范化原文与数据库同目录；勿覆盖正式设定或原始 TXT。

```powershell
python scripts/novel_mining.py register <TXT路径> --source-id sample_v1 --title 示例书 --author 作者 --encoding utf-8
python scripts/novel_mining.py preview --source-id sample_v1 --limit 10
python scripts/novel_mining.py export --source-id sample_v1 --chapter sample_v1_c0001 --output .workbench/novel_mining/chapter.json
```

回读导出的 `text`，填写 `checked_categories` 和 `claims`。空结果允许 `claims: []`，但必须说明实际检查过的类别。每项陈述一个证据范围；同一属性有多个证据时分别记录。格式示例（原创测试文本）：

```json
{
  "source_id": "sample_v1",
  "chapter_id": "sample_v1_c0001",
  "chapter_sha256": "从导出包复制完整章节哈希",
  "checked_categories": ["器物"],
  "claims": [{
    "target_name": "石灯",
    "category": "器物",
    "attribute": "用途",
    "value": "入夜发光",
    "claim_type": "情节展示",
    "conditions": "入夜",
    "speaker": null,
    "evidence_start": 0,
    "evidence_end": 6,
    "evidence_snippet": "石灯入夜发光"
  }]
}
```

示例偏移只适用于片段恰在章节开头的测试文本，实际填写必须包含章节标题在内计算。原文专名不要求与归纳名相同，但二者对应关系需要语义复核。未知代价、条件、配方不得补造；人物说法与传闻必须记录说话者，不能升格为世界事实。

```powershell
python scripts/novel_mining.py extract --source-id sample_v1 --input .workbench/novel_mining/chapter.json
python scripts/novel_mining.py audit --source-id sample_v1
python scripts/novel_mining.py review --source-id sample_v1 --claim-id <陈述ID> --decision approve --reviewer 主代理 --note "回读原文后说明证据支持范围与不支持之处"
python scripts/novel_mining.py evaluate --source-id sample_v1
python scripts/novel_mining.py report --source-id sample_v1 --output .workbench/novel_mining/current-report.md
```

`audit` 输出位置或哈希不合格项；返回空列表只表示这项检查没有发现错误，不是语义通过。陈述 ID 可从本地数据库读取；`report` 会列出各条陈述的 ID 和审核状态。`review --decision reject` 可拒绝有误归纳；无真实证据的旧记录必须重新导入才能复核，不允许直接批准。

旧 `extract --chapters 1-10` 用法已停用，避免继续把预写答案当作提取。`evaluate` 暂时仍只提供有限的历史模板；无映射对象须人工判定，不代表无价值或已淘汰。模板中的拟定名称、等级、机制与去向都是未审定建议，不能作为外书事实或本书既有设定。

## 从素材到正式内容

按以下顺序处理候选，每批最多选五项：

1. 复核原作证据，分开保存原作事实、通用功能模型与本次原创补完；证据不足先补证，不凑字段。
2. 检索本书同名、同功能和上下游，优先补现有条目。仅有普通功能的器物可留作场景细节，不必逐件独立建档。
3. 评估境界、代价、量产、价格、侦测／身份制度及地理时代影响。低阶针具若能无条件破高阶护罡，也应退回专项评估。
4. 保留读者熟悉的直观命名和有价值的功能差异，删除为凑古韵堆出的修饰，避免所有条目都扩成同一套传奇历史。
5. 实际创作时进入根规则管线，完成依据、成文、适用审校与旧文回填，再登记正式路径和提交。程序校验不替代这些环节。

目前第 2—5 步仍由主代理判断与创作管线执行，尚无自动准入、自动精选或提交恢复能力。多进程协调、完整任务租约、长期备份、采用记录及审核历史事件表仍属后续工程；暂限单协调者手动运行。

## 验证

```powershell
python -m unittest discover -s scripts -p test_novel_mining.py -v
```

测试使用临时原创文本，不接触用户原作。现有数据的问题与修复范围见 `EVIDENCE_AUDIT.md`。
