# SMOKE_TEST.md 怎么用

它是验收说明和交给 Codex 的测试任务，不是 shell/Python 程序。不要执行 `python SMOKE_TEST.md` 或把 Markdown 全文当终端命令。
首次部署、升级 Codex、切换后端模型/网关或修改角色配置后执行一次；不是每个辩题都要做。
本包创建环境没有 Codex CLI，下面的原生测试必须在实际用户环境运行；不能把本包静态单测当作原生已通过。

## A. 在操作系统终端检查环境

进入独立的辩论项目目录：

```bash
cd /你的路径/debate-workspace
python --version
codex --version
codex login status
python -m unittest discover -s tests -v
codex
```

Python 需要3.11或以上；系统命令名是 python3 时用 python3 替换。Windows PowerShell 同样逐行运行，目录换成本机路径。
登录状态只说明保存的认证，不保证后端调用、额度或子 agent 能用。没有可用认证时完成自己的正常登录，不向模型或仓库提交密钥。
首次提示信任时，只信任当前辩论目录，不信任整个 HOME 或父级项目集合；项目未信任时配置可能被跳过。
在 Codex 里检查当前工作目录、模型和权限；可使用客户端提供的 `/status`、`/permissions` 等入口。

## B. 在 Codex 输入框执行原生创建/续接测试

把下面文字作为聊天消息发送，不是在 shell 执行：

```text
请执行本项目 SMOKE_TEST.md 的 B 测试，不启动正式辩论。
实际创建两个原生子 agent，分别采用 debate_affirmative 和 debate_negative。
任务均标记 smoke test：不读取项目文件、不联网、不创建更多 agent。
A 支持“先写验收标准，再实现方案”；B 提出适用边界与反例，各最多200中文字。
在接收任一方结果之前完成双方分派；记录工具实际返回的线程标识。
收到双方正式结果后，把 B 的观点发回原 A 线程，让 A 再回答一次并说明是否修正。
不要关闭这两个线程，直到我查看完。
最后报告真实事件中的角色/线程映射、A 的两次任务是否同线程、失败信息。
缺少创建或续接能力就报告阻断，不要用角色标题模拟成功。
```

检查原生子 agent 活动/工具事件：确有两个不同子线程；能看到不同任务；A 的第二次回复发生在原线程。
客户端支持 `/agent` 时可用它查看；若没有该命令，展开客户端的子 agent 活动或实际工具事件。没有 `/agent` 本身不能断言后端不支持。
只有主 agent 的文字声明、手写 ID 或两个角色标题不算通过。模型自己整理的日志也不能单独证明真实性。
B 验证编排和续接，不验证观点质量、严格盲评、成本降低或跨目录权限。

## C. 四角色集成验收（2轮，仅测试）

另开一个新 Codex 会话，发送：

```text
执行 SMOKE_TEST.md 的 C 集成测试。
先运行 python scripts/debate.py prepare --smoke，使用它返回的 run_dir。
按该 run_prompt.md 使用四个真实子 agent 完成两轮测试：支持方、反对方、核查员、评委。
不联网、不读其他辩题。事实只来自测试给定条件或明确标记的逻辑推演。
保存双方正式发言、核查、裁决、账本与最终输出，再运行 validate。
两轮是 smoke 专用设置，不修改 PROMPT.md 和正式 debate.config.toml。
不能原生执行就保存 blocked，不伪造成功。
```

这个测试自动写入 `.smoke/<run-id>/`，不会混入正式主题目录，不覆盖正式主题。检查四种角色都有真实记录；先核查后裁决；文件位于该 run_dir。
输出至少有 manifest.json、run.json、rounds/、checks/final_check.md、checks/verdict.md、final.md、full_transcript.md。
`validate` 检查文件和账本一致；仍要由实际工具事件确认原生运行。

## D. 主题不串线和恢复验收

选择两个不同公开测试题，分别在新会话启动。确认它们进入不同主题目录；再重复同一题，确认主题目录相同但 run_id 不同且旧文件未改变。
正式题运行时不得加载其他题的证据/报告；检查可见工具读取记录。关闭 IDE 自动附加旧文件，勿从旧题 fork。
中断集成测试后，按精确 run_dir 恢复，不能把 `resume --last` 当作跨主题安全恢复。继续的是旧运行；重做则新建运行。
同目录程序性约束不能证明操作系统级读取隔离。需要严格隔离时另建受限工作区/容器。

## 通过记录

记录日期、Codex版本、模型/服务、项目目录、认证模式（不记录密钥）、创建/续接事件定位、四角色集成结果、验证器输出和未测事项。
任何缺失项写 NOT TESTED/BLOCKED，而不是全部 PASS。C 的两轮绝不代表正式辩论只需两轮。
