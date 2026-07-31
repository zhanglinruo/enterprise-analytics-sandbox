# 林析经营分析盲测 Agent 设计规格

**日期：** 2026-07-31

**状态：** Proposed

**阶段：** P1 — External Agent Validation

## 1. 背景

项目已有 AI 经营分析同事“林析”的责任契约、任务、动作、审批、产物和评价模型，
并预留了 `AgentRuntime` 接口。但当前 `DeterministicRuntime` 只读取
`sample_data/monthly_metrics.json` 并按固定公式生成演示结论；它不具备读取公开考试
ZIP、探索 SQLite、调用真实模型或生成盲测答案的能力。

本规格补全一个最小可执行林析，用于
`EAV001-INTERNAL-01`。它不是通用 Agent 平台，也不替换现有确定性演示。

## 2. 目标

林析必须能够：

1. 只使用一个公开考试 ZIP 完成经营分析；
2. 自主阅读公共说明、探索 SQLite 表并迭代执行只读 SQL；
3. 识别主要经营异常、量化影响、提出受证据支持的原因；
4. 明确仅凭公开数据无法确认的事项；
5. 输出符合现有 `AgentAnswer` 契约的原始 JSON；
6. 保存不含密钥的运行元数据和工具审计；
7. 在评分前冻结首次最终答案，保护盲测完整性。

## 3. 非目标

第一版不包含：

- LangGraph、AgentScope 或多 Agent 编排；
- Web 页面、后台任务或审批界面；
- 自然语言答案抽取；
- 任意 Shell、Python 执行或网络搜索工具；
- 对 Ground Truth、评分器或 evaluator 目录的访问；
- 自动评分、Prompt 调优或基于私有分数的重试；
- 第二个场景或通用企业数据 Agent；
- 对现有 `demo`、`DeterministicRuntime` 或 `AINativeEngine` 行为的替换。

## 4. 已确认技术决策

| 决策 | 选择 |
|---|---|
| 模型提供方 | OpenAI API |
| API | Responses API |
| 默认模型 | `gpt-5.6-terra` |
| 默认推理强度 | `medium` |
| 模型覆盖变量 | `OPENAI_MODEL` |
| 推理强度覆盖变量 | `OPENAI_REASONING_EFFORT` |
| 密钥来源 | 项目根目录 `.env` 中的 `OPENAI_API_KEY` |
| SDK | 官方 `openai` Python SDK |
| `.env` 加载 | `python-dotenv` |
| Agent 模式 | 本地受控工具循环 |
| 数据位置 | SQLite 和 ZIP 始终保留在本机 |

OpenAI 当前模型指南建议使用 Responses API 构建推理和工具调用工作流，并将
`gpt-5.6-terra` 定位为能力与成本的平衡选择：

- <https://developers.openai.com/api/docs/guides/latest-model>
- <https://developers.openai.com/api/docs/models>

## 5. 架构

```text
public bench ZIP
        |
        v
PackageGuard ──> temporary public workspace
                         |
                         v
              SandboxReadOnlyToolkit
                         |
                         v
              OpenAIResponsesRuntime
                         |
                         v
               LinxiSandboxAnalyst
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
       raw-answer   run-metadata   tool-audit
```

### 5.1 `OpenAIResponsesRuntime`

实现现有 `AgentRuntime` 边界，负责：

- 创建 Responses API 请求；
- 设置模型、推理强度和结构化工具；
- 处理模型函数调用；
- 把受控工具结果返回模型；
- 执行调用预算和临时 API 重试；
- 接收最终 `submit_answer` 调用。

Runtime 不包含经营场景、Cause ID、评分规则或 SQL 业务逻辑。

### 5.2 `SandboxReadOnlyToolkit`

向模型暴露且仅暴露五个工具：

1. `read_public_document`
2. `list_tables`
3. `describe_table`
4. `execute_select`
5. `submit_answer`

Toolkit 不提供 Shell、任意路径、文件写入、数据库写入、评分或网络能力。

### 5.3 `LinxiSandboxAnalyst`

复用“林析”的责任型 Agent 概念，负责：

- 创建单次分析任务和成功标准；
- 记录读数据动作与治理判断；
- 提供精简、无答案暗示的系统责任说明；
- 调用 Runtime 和 Toolkit；
- 原子保存答案、运行元数据和审计日志；
- 在成功或失败时留下明确运行状态。

林析的只读分析动作允许自主执行；源数据修改永远禁止。

### 5.4 CLI

新增命令：

```powershell
python -m ainative.cli sandbox-agent-run `
  --package path\to\bench_*.zip `
  --output path\to\run-directory
```

CLI 只接受单个公开 ZIP 和新的运行输出目录。它不接受 benchmark evaluator 目录、
`private-state.json`、评分答案或 Ground Truth。

## 6. 责任契约

### 6.1 身份

- ID：`business_analyst`
- 名称：林析
- 角色：AI 经营分析同事
- 目标：识别经营异常，形成可信分析，并明确判断边界

### 6.2 能力

- 读取公开经营资料；
- 检查关系型数据结构；
- 执行只读经营分析 SQL；
- 进行指标、趋势和归因分析；
- 生成结构化证据和建议。

### 6.3 自治与治理

| 动作 | 决策 |
|---|---|
| 读取公开包 | allow |
| 描述公开表结构 | allow |
| 执行受限只读 SQL | allow |
| 提交原始分析产物 | allow |
| 修改源数据 | deny |
| 读取公开包之外的文件 | deny |
| 调用评分或私有状态 | deny |
| 外部发布正式报告 | 不在第一版范围 |

## 7. 数据流

1. CLI 加载 `.env` 并验证非敏感配置。
2. `PackageGuard` 验证 ZIP 的名称、大小、成员和路径安全。
3. ZIP 解压到运行专属临时目录。
4. Toolkit 定位公共文档和 `data/enterprise.db`。
5. SQLite 以只读、immutable、query-only 模式打开。
6. Runtime 向模型提供责任说明、公共任务书和五个工具定义。
7. 模型迭代阅读公共资料、查看表结构并执行受限查询。
8. 每次工具调用与受控结果写入 JSONL 审计。
9. 模型调用 `submit_answer`。
10. 本地使用现有 `AgentAnswer.from_dict` 进行二次 Schema 验证。
11. 成功时原子写入 `raw-answer.json`，随后写入完成状态。
12. 无论成功失败都关闭 SQLite 并清理临时解压目录。

## 8. 包安全

`PackageGuard` 必须：

- 拒绝绝对路径、`..` 路径穿越和驱动器路径；
- 拒绝符号链接和非普通文件；
- 限制 ZIP 成员不超过 100 个；
- 限制总解压体积不超过 256 MiB；
- 限制单个文件不超过 128 MiB；
- 要求恰好一个 `data/enterprise.db`；
- 要求公共任务、Schema 或数据字典资产存在；
- 拒绝名称包含 `private`、`ground_truth`、`score-report` 或 `answer` 的成员；
- 不允许调用者指定解压目标内的任意文件路径。

解压使用逐成员验证后的受控目标路径，不调用无校验的批量解压。

## 9. SQLite 只读安全

数据库连接必须同时使用：

- URI `mode=ro&immutable=1`；
- `PRAGMA query_only = ON`；
- SQLite authorizer 拒绝写入、DDL、`ATTACH`、`DETACH`、扩展加载和危险操作；
- 禁用扩展加载；
- progress handler 提供查询步数或时间上限。

`execute_select` 只接受一条以 `SELECT` 或 `WITH` 开始的语句。它拒绝：

- 多语句；
- 空 SQL；
- 写入或 DDL；
- `ATTACH` / `DETACH`；
- 非白名单 PRAGMA；
- 返回超过 200 行或序列化后超过 64 KiB 的结果。

查询失败以受控错误返回模型，同时完整记录错误类型，但不暴露本地绝对路径。

## 10. OpenAI 工具循环

默认限制：

| 限制 | 值 |
|---|---:|
| 工具调用总数 | 30 |
| SQL 查询数 | 20 |
| 最终 Schema 修正机会 | 1 |
| 临时 API 重试 | 2 |
| 单次查询行数 | 200 |
| 单次查询序列化结果 | 64 KiB |

每次工具结果都可能影响模型的下一步分析，因此第一版使用直接函数调用，而不使用
Programmatic Tool Calling。

模型系统说明只包含：

- 林析的责任和成功标准；
- 只读与盲测边界；
- 工具用途和证据要求；
- 最终答案 Schema；
- 查询和停止预算。

系统说明不得包含场景 ID、Cause ID、目标区间、评分权重、禁止原因或预期 SQL。

## 11. 最终答案

`submit_answer` 参数必须与现有 `AgentAnswer` 契约一致：

```json
{
  "anomalies": [
    {"metric": "metric_name", "direction": "up", "magnitude": 0}
  ],
  "causes": [
    {
      "cause": "stable_cause_identifier",
      "confidence": 0.8,
      "evidence": [
        {"table": "public_table", "field": "public_field", "value": 0}
      ]
    }
  ],
  "unknowns": ["material unknown"],
  "recommendations": ["specific next action"]
}
```

本地验证拒绝未知顶层字段、非法方向、非有限数值、缺失 evidence 数组和超出
`[0, 1]` 的置信度。

第一次成功提交的答案立即冻结。Runtime 不得读取评分结果后再次请求模型。

## 12. 运行产物

成功运行目录包含：

```text
raw-answer.json
run-metadata.json
tool-audit.jsonl
```

`run-metadata.json` 包含：

- run ID；
- Agent 身份和责任版本；
- 模型和推理强度；
- 开始、结束和耗时；
- 包 SHA-256；
- 工具和 SQL 调用计数；
- API 重试次数；
- 最终状态和受控错误码；
- Token 使用量（API 提供时）。

它不得包含：

- API Key 或请求头；
- `.env` 内容；
- evaluator 路径；
- private state；
- 模型隐藏推理内容；
- 私有评分结果。

`tool-audit.jsonl` 每行记录工具名、调用序号、非敏感参数、状态、截断标记和耗时。
SQL 可以记录以支持证据复核；文档内容和查询结果只记录摘要与哈希，避免日志膨胀。

## 13. `.env` 与依赖

新增运行依赖：

- `openai`
- `python-dotenv`

项目根 `.env` 至少包含：

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=medium
```

仓库提交 `.env.example`，不提交 `.env`。`.gitignore` 必须忽略：

```gitignore
.env
.env.*
!.env.example
```

启动日志只报告变量是否配置，不回显变量值。

## 14. 错误处理

| 场景 | 行为 |
|---|---|
| `.env` 或 API Key 缺失 | API 调用前失败 |
| 模型或推理配置非法 | API 调用前失败 |
| ZIP 安全校验失败 | 停止并记录包错误 |
| SQLite 安全校验失败 | 停止并记录数据库错误 |
| 非法 SQL | 拒绝并允许模型修正 |
| 临时 API 限流或超时 | 最多重试两次 |
| API 鉴权或模型不可用 | 不重试，立即失败 |
| 工具或 SQL 预算耗尽 | 失败，不生成兜底答案 |
| 最终 JSON 非法 | 允许一次修正，仍非法则失败 |

建议 CLI 退出码：

| 退出码 | 含义 |
|---:|---|
| 0 | 成功并写入原始答案 |
| 2 | 参数、配置或最终答案 Schema 无效 |
| 5 | 公开包或 SQLite 安全校验失败 |
| 6 | OpenAI API 永久失败 |
| 7 | 工具预算耗尽或运行未完成 |

失败运行仍写入不含密钥的 `run-metadata.json`，但不得伪造 `raw-answer.json`。

## 15. 测试策略

### 15.1 单元测试

- ZIP 路径穿越、符号链接、异常体积和私有名称被拒绝；
- 正常公开包被接受；
- SQLite 写入、DDL、`ATTACH`、多语句和危险 PRAGMA 被拒绝；
- 查询行数、序列化体积和执行预算生效；
- `.env` 缺失和非法配置在 API 调用前失败；
- 异常和日志不包含模拟 API Key。

### 15.2 Runtime 契约测试

使用假的 Responses 客户端模拟：

```text
list_tables
→ describe_table
→ execute_select
→ submit_answer
```

验证工具结果传回、调用计数、一次 Schema 修正、API 重试和最终冻结。CI 不调用真实
OpenAI API。

### 15.3 CLI 集成测试

使用最小公开 ZIP、SQLite fixture 和假 Runtime 验证：

- 成功产物；
- 失败元数据；
- 审计日志；
- 退出码；
- 临时目录清理；
- evaluator 路径和私有文件被拒绝。

### 15.4 Live acceptance

只有显式设置 `LINXI_LIVE_TEST=1` 才调用真实 API。正式接受测试使用 seed 61 公共包：

- 模型只能看到参与者 handoff；
- 工具全部为只读；
- 最终答案通过 `AgentAnswer` 验证；
- 答案和审计先冻结，再进行任何评分。

开发阶段不根据私有分数调 Prompt，不把 Ground Truth 写入 fixture。首次 live 结果直接
作为 `EAV001-INTERNAL-01` 的原始答案。

## 16. 替代方案

### 一次性预计算

由 Python 先计算完整指标再让模型解释。实现更小，但分析路径由开发者预设，可能暗示
答案，不适合验证 Agent 的自主分析能力。

### 托管 Code Interpreter

把整个 ZIP 上传到托管执行环境。隔离直观，但数据完整上传，工具限制、查询审计和本地
复现控制更弱。

### LangGraph / AgentScope

可提供更丰富的状态机和编排，但第一版只有单 Agent、五个工具和一个最终产物，引入
框架会扩大依赖和测试面。

## 17. 验收标准

实现完成需同时满足：

1. 所有现有 25 项测试继续通过；
2. 新增安全、Runtime 和 CLI 测试全部通过；
3. CI 默认不访问真实 OpenAI API；
4. `.env`、API Key 和生成运行目录均不进入 Git；
5. 写入、任意文件读取和评分访问在工具边界不可达；
6. seed 61 live acceptance 生成 Schema 合法的首次原始答案；
7. 运行日志可复核 SQL 和工具序列且不含密钥；
8. 首次答案在评分前冻结，并登记为 `EAV001-INTERNAL-01`。

## 18. 后续边界

只有 EAV001 完成并证明该 Agent 工作流有价值后，才考虑：

- 多模型比较；
- Agent Runtime 框架；
- 人工审批或 UI；
- 直接评分集成；
- 更多场景和通用企业数据连接器。
