---
name: Git Commit After Every Revision
description: 每一轮设定或正文修改完成后必须立即 git commit 落库，不能只停在 git add 暂存
type: feedback
---

每一轮修改（新建设定、扩写、重构、回填旧文）完成后，必须立即执行 `git add <改动文件>` 并 `git commit`，把修改真正落进提交历史，然后向用户汇报提交哈希与改动文件数。

**原因：** 用户多次确认后发现此前只执行了 `git add` 暂存而未 commit，误以为内容已"缓存"，实际未落库，造成重复确认与不信任。用户明确要求"以后每一次修改都需要缓存在Git里"。

**应用场景：** 本仓库所有创作任务的收尾步骤——文件写入完成后，统一 `git add` + `git commit`（中文提交信息，概括本轮设定改动），并在汇报中给出 commit hash。不要再把"已暂存"说成"已缓存"。
