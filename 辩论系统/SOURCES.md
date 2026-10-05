# 审查依据与官方资料

核对日期：2026-10-05。下列链接是官方入口，部分已重定向到OpenAI的ChatGPT Learn站点。这里只据实际文档声明支持能力，不据文档示例推断用户账户一定可用。

## 用户材料

原始《优化版v2.8_5Agent辩论系统Prompt.txt》，SHA-256：`ba6dbc2eaf5ea601ce79696005b048810cc29892f48c00a44d8e581a7847001b`。
上轮《辩论系统_v3.0_Codex完整升级包.zip》，SHA-256：`19ba200cbcff285245b0133aa0776741512c3ed263d18f870091c47b577af5a2`。
上轮复审文档与总提示词也在本次会话中可用；本次纠正v3.0默认短轮次取向，保留证据/原生执行修复。
原附件未在本次提交中重新发布全文，避免让归档旧模板与现行版本混用。原稿行号定位列于复审结论。

## Codex官方资料

- Subagents / 自定义角色与权限继承：https://developers.openai.com/codex/multi-agent/
- 项目配置、信任和优先级：https://developers.openai.com/codex/config-basic/
- 配置参考（agents、memories、sandbox、web_search）：https://developers.openai.com/codex/config-reference/
- CLI命令、--cd、认证和新会话：https://developers.openai.com/codex/cli/reference/
- 聊天命令与/new：https://developers.openai.com/codex/cli/slash-commands/
- skills的项目与全局加载位置：https://developers.openai.com/codex/skills/
- AGENTS.md加载和继承：https://developers.openai.com/codex/guides/agents-md/

## 事实、设计、测试的边界

文档支持“项目级配置”“原生子agent”“自定义角色TOML”“记忆控制”“新会话”等能力说明，不证明任何具体安装环境已经启用，也不证明多agent更准确或更便宜。
30/60轮、10/20/30/30/10阶段权重、R12起评估和4轮稳定窗口是本次设计参数，不是引用官方文档得出的推荐值。
真实运行、权限实际值、事件真实性、用量和模型质量需本地验收；静态测试不能替代。
