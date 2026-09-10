---
name: Selective Staging Under Concurrent Edits
description: 仓库可能被并行会话同时改动，提交时只精确暂存本次任务的文件，禁止 git add -A 或 git add .
type: feedback
---

提交本任务的改动时，只逐个 `git add -- <本次任务实际改动的文件>`，不要用 `git add -A` / `git add .` / `git commit -a`。若开工时工作区快照是 clean、收尾时却出现大量陌生改动，说明有并行会话在改同一工作区——此时只提交自己动的文件，把别人的改动留在工作区，并在汇报中说明。

另：同一文件可能被自己与并行会话混合修改（如本次 起源总纲.md 既有我的 `[[洞喻]]` 回填，也有对方的形意论述新增）。这种情况下不能整文件提交，应先看 `git diff` 分清改动归属；若自己的改动与对方改动无法在文件内分离，宁可暂不提交该文件或先与用户确认，也不能把他人未完成的工作一并落库。

**原因：** 本仓库实际存在多会话并行编辑（本次收尾时工作区多出神裔.md、业.md、世界背景.md、帝网.md、.memory/project-xingyi-ye-architecture.md 等绝非本任务产出的改动）。若用 git add -A，会把对方半成品一并提交，污染提交历史、抢走对方落库权，并可能提交未完成的设定。

**应用场景：** 所有本仓库任务的阶段四 git 落库环节。收尾先 `git status --short` 与 `git diff --stat` 核对改动范围，逐个文件显式 add；对出现非预期改动的文件，先 `git diff -- <file>` 确认归属再决定。
