# 项目级配置：放在哪里、如何生效、边界是什么

核对日期：2026-10-05。官方资料在上层 SOURCES.md；文档形式与客户端能力仍需实际 smoke test。

## 1. 只在一个独立项目安装

```text
debate-workspace/
  .debate-project
  .codex/
    config.toml
    agents/
      debate_affirmative.toml
      debate_negative.toml
      debate_checker.toml
      debate_judge.toml
  .agents/skills/evidence-debate/SKILL.md
  AGENTS.md
  PROTOCOL.md
  SCHEMA.md
  PROMPT.md
  debate.config.toml
  scripts/debate.py
  tests/test_debate.py
```

不要放进 `~/.codex/config.toml`、`~/.codex/agents/`、`~/.agents/skills/` 或 `~/.codex/AGENTS.md`。不要修改 gptug 根目录配置。
本包在仓库中放 `辩论系统/codex-project/`，是供整体复制的独立运行项目；上层文档只是阅读材料。
在新目录 `git init`，将它作为单独 Codex 项目打开，避免被父级其他仓库规则包围。
项目配置需要该目录被信任；首次由你在客户端确认，不把整个 HOME 加为信任目录。

## 2. 完整 Codex 配置

实际文件 `.codex/config.toml`：

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"
web_search = "live"

[agents]
enabled = true
max_concurrent_threads_per_session = 4

[features]
memories = false

[memories]
use_memories = false
generate_memories = false

[sandbox_workspace_write]
network_access = false
```

`agents` 开启原生工具并限制同时开放的子线程数（不含主线程）；这个4不是辩论轮数或费用上限。
主 agent 需要工作区写权限来保存报告。四个角色文件默认只读；父会话实时权限覆盖、组织策略仍可能影响最终权限，要查看实际值，不使用 `--yolo`。
关闭 memories 的读写用于减少跨题自动记忆输入，不删除正常会话日志，也不阻止模型已有常识。认证、历史和信任记录仍可能由 Codex 正常存于用户目录；“配置只影响该项目”不是“软件完全不写用户目录”。
`web_search=live` 让公共主题可检索实时资料；`network_access=false` 限制沙箱 shell 的网络，不是关闭内置搜索。两个字段控制不同入口。
public_only 是本协议对内容的限制，不是网络层数据防泄漏产品。内部资料项目首次配置时应把 web_search 改为 disabled，同时将 debate.config.toml 的 search_policy 改成 offline，并检查 MCP、连接器、模型服务及其他工具的授权。
禁止把企业私有路径、代码、报告、设计代号发送到公共搜索。目录里没有 MCP 配置，不等于不存在继承的 MCP；本包不会静默替你删除全局 MCP。

## 3. 完整辩论参数配置

以下是本程序读的 `debate.config.toml`，不是 Codex 内置参数：

```toml
system_version = "3.1"
purpose = "decision"
planned_rounds = 30
max_rounds = 60
extension_rounds = 10
phase_weights = [10, 20, 30, 30, 10]
convergence_start_ratio = 0.4
stable_window = 4
checkpoint_interval = 5
search_policy = "public_only"
output_language = "zh-CN"
```

固定默认足以让日常只编辑主题。要把整个系统改成50轮规划，可在部署/维护时设 planned_rounds=50，并确保 max_rounds不低于50；阶段由程序按权重计算，不能再逐个修改四份角色规则。
计划30不表示30轮自动停。有效工作未完成时以10轮为块扩展，最多60；停止应满足协议中的证据、覆盖和稳定性闸门。常规收敛起点为初始计划的40%，默认R12；紧急阻断/可复现证明允许例外。
要研究100轮任务可以明确增大配置，但更长并不自动更好，也不能保证平台一次调用不中断；长期运行应特别检查摘要失真与中断恢复。

## 4. 四份角色配置

`.codex/agents/debate_*.toml` 已提供完整内容，不需要用户再生成。每份都有 `name`、`description`、`developer_instructions`，并设置 `sandbox_mode="read-only"`。
`name` 是 Codex 选择角色的标识；文件名跟它保持一致。角色约束短而专一，共享规则只维护在 PROTOCOL.md；每个新辩题不再复制编辑整套角色模板。
不要把 AGENTS.md 当成创建 agent 的 API：是否真实启动必须由子 agent 工具事件验证。
当前包不写死 model、model_reasoning_effort 或 model_provider，沿用你实际可用的会话模型。后端网关、认证、模型兼容不是这个模板可以凭空提供的。
要固定模型，可在部署时使用账户实际支持的模型标识；不同模型推理档位可能不同，先验收。不要照抄文档示例中你账户没有的模型名称。

## 5. 不影响其他项目，不等于不受其他配置影响

官方配置规则中，CLI覆盖优先于项目配置，项目配置可覆盖较低优先级默认值；组织策略仍有约束。AGENTS.md、skills、MCP 也有各自继承/发现机制。
本项目的 `.codex`、角色和skill不安装到全局，不应成为其他独立项目的默认规则；但本项目仍可能继承已有全局指令、全局skill、MCP和登录状态。
遇到冲突检查当前目录、是否被信任、CLI参数、上层AGENTS/skills和组织策略；不要简单关闭安全限制。
确需连登录状态和全局配置都隔离，可另设专用运行环境或进程级 CODEX_HOME，并重新配置认证/供应商；本包默认不这样做，避免改变你的既有Codex环境，也不宣称这相当于操作系统级文件隔离。

## 6. 主题隔离的四层

文件：topic_key + run_id，独立账本和完整快照，不共享latest指针。
会话：每次启动新主会话，子agent只属于当前run；同题重做不自动复用旧证据。
记忆：本项目关闭自动记忆读写；IDE不要自动附加别的题目文件，开新会话而不是fork旧会话。
权限：当前实现是合作式路径约束，不是OS读访问隔离。严格不允许看到其他题目时，应每题独立受限工作区/容器，只挂载当前题目和只读协议。

## 7. 维护与恢复

每次启动冻结系统文件和原prompt；旧run不受后续修改主题影响。协议或角色文件更新后先用新会话执行 smoke test，再开始新题。
修改全局供应商、登录、安装MCP不是本包正常启动动作。常规辩论没有自动Git提交/上传权限，避免将内部结果发布到公共仓库。
