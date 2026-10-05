# Codex 独立辩论项目 v3.1

日常唯一需要编辑的是 **PROMPT.md 第一行的主题**。默认规划30轮、上限60轮；根据重要争点、核查和稳定性继续、扩展或结束，不强行跑满，也不为了省消耗压成几轮。

首次配置见 [CONFIGURATION.md](CONFIGURATION.md)，首次真实能力测试见 [SMOKE_TEST.md](SMOKE_TEST.md)。完整运行协议见 [PROTOCOL.md](PROTOCOL.md)，字段契约见 [SCHEMA.md](SCHEMA.md)。

## 首次部署

把整个 `codex-project` 目录复制到新建的独立工作区，必须包含 `.codex`、`.agents` 和 `.debate-project` 隐藏文件。不要复制到用户 HOME 的全局配置目录。
示例（需已安装 Git、Python3.11+ 和可用的 Codex）：

```bash
git clone https://github.com/DiiShan/gptug.git
python -c "import shutil; shutil.copytree('gptug/辩论系统/codex-project', 'debate-workspace')"
cd debate-workspace
git init
python -m unittest discover -s tests -v
codex --version
codex login status
codex
```

目标 `debate-workspace` 必须尚不存在，复制操作不会覆盖已有工作区。Python命令名为python3时替换即可。上述示例也可在PowerShell逐行执行。
只信任新建的辩论目录，执行 SMOKE_TEST.md。不要在 gptug 顶层或整个 HOME 开启本工作流。

## 日常方式一：固定命令自动新建会话（推荐）

修改 PROMPT.md 第一行，例如：

```text
【辩题输入】在需求存在明显不确定性时，应先做原型还是先写完整规格？
```

在该项目终端运行固定命令：

```bash
python scripts/debate.py start
```

脚本读取主题、建立独立运行、保存输入快照，然后启动一个新的 Codex 主会话，指向生成的 run_prompt.md。不会调用 `resume --last`，不会继承旧题聊天记录。
这是一条启动命令，不是常驻监视器；脚本退出后不会继续做后台工作。用户依然需正常完成客户端信任、认证及必要权限确认。

## 日常方式二：在新 Codex 聊天读取模板

在本项目新建一个空白会话，输入固定句子：

```text
读取 PROMPT.md 并执行。
```

Codex 按项目规则自动 prepare，再读取生成的 run_prompt.md。不要在已经讨论另一个辩题的聊天里直接换题；可用客户端的新聊天入口或CLI的 `/new`。不要 fork 旧题。
**同一辩题内部一个主对话组织多个原生子 agent；不同辩题使用不同主对话。**

## 自动产物

```text
debates/
  t-主题名--主题哈希/
    topic.json
    runs/
      20261005T...Z--随机ID/
        manifest.json
        run_prompt.md
        inputs/PROMPT.md
        inputs/system/...
        run.json
        rounds/
        checkpoints/
        checks/final_check.md
        checks/verdict.md
        evidence/
        final.md
        full_transcript.md
```

prepare 只建立骨架和输入，不制造辩论结果。rounds/、checks/、final.md 等由实际运行完成后写入。
相同主题再次启动会新建run，不覆盖历史；改变主题进入另一主题目录。不同题不共享 agent、证据缓存、状态文件或“最新结果”指针。
启动后的旧运行使用自己的输入快照，因此后来修改公共 PROMPT.md 不会改变旧运行的辩题。
默认 `.gitignore` 忽略所有运行输出；这是防误提交，不是访问控制。是否发布某次结果，需要另行授权和内容检查。

## 常用命令

```bash
# 查看按总轮数生成的阶段划分，不调用模型
python scripts/debate.py plan
python scripts/debate.py plan --rounds 50

# 只初始化目录，不启动 Codex；通常由主 agent 调用
python scripts/debate.py prepare --prompt PROMPT.md

# 创建不影响正式主题的两轮集成测试输入
python scripts/debate.py prepare --smoke

# 最终形式检查；替换为真实 run_dir，不要直接复制尖括号占位符
python scripts/debate.py validate 'debates/<主题目录>/runs/<运行目录>'

# 中断恢复：指定准确旧运行，在新主会话中读该运行快照
python scripts/debate.py resume 'debates/<主题目录>/runs/<运行目录>'
```

`resume` 要求当前系统模板与旧运行快照匹配；改变 PROMPT.md 主题不算系统模板漂移。不能匹配时需恢复对应系统版本，而非静默用新规则接着辩。
原生线程能否跨客户端重启恢复取决于运行环境；恢复失败必须新建同角色线程并记录替换，不能假装原线程续接成功。

## 边界

脚本真正实现的是输入/目录/快照/新会话启动和事后结构检查；实际辩论由 Codex 原生子 agent 工具加本协议组织，不是独立实现的强制多 agent 调度服务器。
本包不保证一次请求一定不中断跑满60轮，不把多 agent 数量当质量保证。结构测试通过不证明来源真实、事实正确、原生工具真的执行或操作系统级隔离。
