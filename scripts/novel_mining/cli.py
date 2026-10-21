"""Offline novel evidence workflow. No automatic model calls or formal writes."""

import argparse
import json
from pathlib import Path

from .db import MiningDatabase, DEFAULT_DB_PATH
from .slicer import NovelSlicer
from .extractor import ChapterExtractor
from .evaluator import CandidateEvaluator, EVALUATION_SPECS


def build_report(db, source_id):
    source = db.get_source(source_id)
    if not source:
        raise ValueError("Unknown source")
    extractor = ChapterExtractor(db)
    issues = extractor.audit(source_id)
    claims = db.get_claims(source_id)
    chapters = db.get_chapters(source_id)
    counts = {}
    for claim in claims:
        counts[claim["status"]] = counts.get(claim["status"], 0) + 1
    lines = [f"# {source['title']}素材证据审计", "",
             f"来源版本：`{source_id}`；作者：{source['author']}；编码：{source['encoding']}", "",
             f"登记章节：{len(chapters)}；有导入记录章节：{sum(c['status'] == 'imported' for c in chapters)}。",
             "导入记录只表示提交过检查结果，不证明章节无遗漏或已经完成语义复核。", "",
             f"陈述：{len(claims)}；状态：{json.dumps(counts, ensure_ascii=False)}；位置／哈希不合格：{len(issues)}。", "",
             "## 待处理证据", ""]
    for issue in issues:
        lines.append(f"- `{issue['claim_id']}` {issue['target_name']}：{issue['issue']}")
    if not issues:
        lines.append("位置检查未发现问题；此结果不代表归纳得到原文支持。")
    lines += ["", "## 陈述与复核状态", ""]
    for claim in claims:
        lines.append(f"- `{claim['claim_id']}` {claim['target_name']}／{claim['attribute']}："
                     f"{claim['status']}；{claim['value']}")
    lines += ["", "## 转化候选", "",
              "预设映射仅为建议，不代表仓库检索、原创性、影响评估或创作审校已经通过。",
              "优先回填已有条目；新建须证明独立展开价值。每批最多选择五项，不足不凑数。", ""]
    invalid = {i['claim_id'] for i in issues}
    entities = {e['entity_id']: e for e in db.get_all_entities(source_id)}
    for cand in db.get_all_candidates(source_id):
        entity = entities.get(cand['entity_id'])
        if not entity or not entity['claims'] or any(c['claim_id'] in invalid for c in entity['claims']):
            continue
        lines.append(f"- {cand['canonical_name']} → {cand['proposed_adaptation'].get('proposed_name', '待拟定')}"
                     f"；{cand['destination']}（待创作准入）")
    mapped = {s['name'] for s in EVALUATION_SPECS}
    unmapped = [e['canonical_name'] for e in entities.values() if e['canonical_name'] not in mapped]
    if unmapped:
        lines += ["", "无预设映射，需人工选择去向：" + "、".join(unmapped)]
    lines += ["", "历史转化稿尚需逐条回溯；本工具不会修改或自动确认正式设定。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subs = parser.add_subparsers(dest="command", required=True)
    reg = subs.add_parser("register")
    reg.add_argument("file", type=Path)
    reg.add_argument("--source-id", required=True)
    reg.add_argument("--title", required=True)
    reg.add_argument("--author", default="")
    reg.add_argument("--version", default="v1")
    reg.add_argument("--encoding", default="utf-8-sig")
    for name in ("preview", "export", "extract", "review", "evaluate", "audit", "report"):
        sub = subs.add_parser(name)
        sub.add_argument("--source-id", default="mushenji_v1")
        if name == "preview":
            sub.add_argument("--limit", type=int, default=10)
        if name == "export":
            sub.add_argument("--chapter", required=True)
            sub.add_argument("--output", type=Path, required=True)
        if name == "extract":
            sub.add_argument("--input", type=Path, required=True,
                             help="Evidence-backed chapter JSON; hardcoded extraction is disabled")
        if name == "review":
            sub.add_argument("--claim-id", required=True)
            sub.add_argument("--reviewer", required=True)
            sub.add_argument("--note", required=True)
            sub.add_argument("--decision", choices=("approve", "reject"), required=True)
        if name in ("audit", "report"):
            sub.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    db = MiningDatabase(args.db)
    ext = ChapterExtractor(db)
    try:
        if args.command == "register":
            source, chapters = NovelSlicer(db).register_and_slice(
                args.file, args.source_id, args.title, args.author, args.version, args.encoding)
            print(f"Registered {source.source_id}: {len(chapters)} chapters (not extracted)")
        elif not db.get_source(args.source_id):
            raise ValueError("Unknown source")
        elif args.command == "preview":
            print(json.dumps(db.get_chapters(args.source_id, args.limit), ensure_ascii=False, indent=2))
        elif args.command == "export":
            chapter, body = ext.chapter_text(args.source_id, args.chapter)
            payload = {"source_id": args.source_id, "chapter_id": args.chapter,
                       "chapter_sha256": chapter['sha256'], "text": body,
                       "instructions": "逐字段提供原文证据，章内 Unicode 码点 [start,end)；未知留空，勿补造。",
                       "checked_categories": [], "claims": []}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Exported {args.chapter}")
        elif args.command == "extract":
            response = json.loads(args.input.read_text(encoding="utf-8"))
            count = ext.import_response(args.source_id, response)
            print(f"Imported {count} claims: evidence positions checked; semantic review required")
        elif args.command == "review":
            ext.review_claim(args.source_id, args.claim_id, args.reviewer, args.note,
                             args.decision == "approve")
            print("Review recorded; this is source-claim review, not formal setting approval")
        elif args.command == "evaluate":
            candidates = CandidateEvaluator(db).evaluate_candidates(args.source_id)
            print(f"Saved {len(candidates)} template proposals; repository research and admission still required")
        else:
            result = (json.dumps(ext.audit(args.source_id), ensure_ascii=False, indent=2)
                      if args.command == "audit" else build_report(db, args.source_id))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(result, encoding="utf-8")
                print(f"Written: {args.output}")
            else:
                print(result)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
