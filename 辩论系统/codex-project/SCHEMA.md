# v3.1 文件与账本契约

这是面向主 agent 的字段契约。scripts/debate.py 的 validate 只检查其中可机械检查的部分，不验证语义真实性。

## 不可覆盖输入

manifest.json：schema_version、run_id、topic_key、motion_original、created_at（含时区）、smoke、config（冻结的应用配置）、initial_plan、convergence_start_round、system_hashes。
inputs/PROMPT.md：本次原始主题文件。inputs/system/：共享协议、应用配置、Codex配置、角色文件、入口和脚本的运行快照。
run_prompt.md：自动生成，明确当前运行路径；不要求用户改名或手填目录。

## run.json

schema_version="3.1"；run_id 与 manifest 一致；execution_mode="native"；status 为 prepared/running/blocked/interrupted/adjudicated/inconclusive；rounds_completed；max_rounds；evidence_version；stop_reason。
运行中状态不必通过最终验证。工具缺失时 blocked，不生成假裁决。最终允许 adjudicated 或 inconclusive。

agents 数组：每项 role（affirmative/negative/checker/judge）、thread_id、tool_event_ref。替换线程时可另加 replaced_thread_id、reason；同角色可有多条历史，但同一个 thread_id 不得充当多个角色。

rounds 数组：number 从1连续递增；phase（实际执行阶段）；input_evidence_version；artifacts 对象中的 affirmative/negative/moderator 均为相对当前 run_dir 的非空文件路径；progress_note；changed_claim_ids；changed_evidence_ids；decision_changed；conditions_changed。保存真正发生的进展，不伪造稳定窗口。

claims 数组：id（C001…）、text、kind（empirical/logical/forecast/value）、decisive（bool）、evidence_ids、depends_on、assessment（supported/partially_supported/contradicted/unverified/disputed/not_applicable）、review_version、review_note、scope。
预测与价值主张的 supported 不能被解释成未来事实已经发生；其事实前提通过 depends_on 指向 empirical 主张。

evidence 数组：id（E001…）、locator（URL或文件/页码/行号/计算定位）、source_type、excerpt、source_date、accessed_at、scope、source_family、acquisition（observed/user_supplied/unobserved）、tool_event_ref（observed 必须有实际定位）。
用户提供的信息要保留 user_supplied，不假装独立外部验证。网页引用仅保留必要短摘录。

issues 数组：id、claim_ids、priority（decisive/important/minor）、status（open/resolved/blocked）、resolution、next_action。coverage 数组按题目记录重要维度和双方覆盖，不能只检查字数。

plan_revisions 数组：changed_after_round、reason、old_planned_rounds、new_planned_rounds、remaining_plan。保留历史，不重写已执行回合。

convergence 对象：coverage_complete、key_facts_checked、strongest_objections_addressed、reverse_case_done、no_high_value_next_step、stable_rounds，以及 note。布尔闸门需要正文/核查支持，模型填 true 不等于已经证明。

final_gate 对象：evidence_version、checker_thread_id、report_path="checks/final_check.md"；核查必须早于最终裁决完成。
verdict 对象：kind（recommendation/conditional/inconclusive/competition_only）、evidence_version、judge_thread_id、report_path="checks/verdict.md"、summary、relied_claim_ids、blocking_claim_ids、conditions、remaining_uncertainties。

override/例外：提前证明用 stop_reason="exception_proven" 并提供 exception_note、exception_evidence_ids；预算耗尽用 budget_exhausted；正常收敛用 converged；smoke结束用 smoke_completed。

## 支持链规则

最终支持链上的被证伪命题不能当作成立前提；要论证“旧命题已被推翻”，新增由反证支持的命题，不直接依赖旧错误命题。
未核实/部分支持/有争议的事实前提仅能在 conditional/inconclusive 中作为明示 blocking_claim_ids，不支持无条件 recommendation。
当前版本事实审查必须匹配 evidence_version。核查版本改变后所有最终事实前提需重新确认，不要求无意义地重搜每一个未变来源。

## 输出文件

rounds/001-affirmative.md、001-negative.md、001-moderator.md 等逐轮保存，不用一段总摘要替代原始正式发言。
checkpoints/ 保存阶段及定期锚点；checks/ 保存核查批次和裁决；evidence/ 保存获准的必要证据定位/重算输出。
final.md 是面向用户的实质结论。full_transcript.md 是正式交付记录汇集，不是私有思考链。
所有路径均相对当前 run_dir，不允许绝对路径、.. 越界或链接到其他运行。工具不能自动封锁 agent 的所有读取，须另行审查实际事件。
