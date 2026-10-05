---
name: evidence-debate
description: 在本独立项目中，用户明确要求读取辩题 PROMPT.md、run_prompt.md 或执行多 agent 辩论时使用；不用于普通问答、维护和 smoke test。
---

读取项目 AGENTS.md、PROTOCOL.md。项目级参数唯一来源是 debate.config.toml。
没有 run_dir 时执行 python scripts/debate.py prepare --prompt PROMPT.md。
已有 run_dir 时读取该目录的 run_prompt.md、manifest.json、inputs/system/PROTOCOL.md 和最新 run.json。
必须实际分派支持方、反对方、核查员和评委，不在主线程冒充子 agent。
在当前运行快照内执行；不要再次读取已修改的 PROMPT.md 或扫描其他辩题。
