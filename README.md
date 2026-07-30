# AI Native Starter

面向“责任型 AI 应用”的最小可运行脚手架。它不是聊天机器人模板，也不是低代码
工作流平台，而是把 AI 同事进入真实工作所需的责任、任务、动作、审批、产物和评价
做成可复用内核。

当前版本同时提供一个“AI 经营分析同事”参考应用，完整演示：

```text
数据更新 → 异常感知 → 主动建任务 → 归因分析 → 生成证据
       → 发布审批 → 人工确认 → 评价沉淀
```

## 快速开始

本版本只依赖 Python 3.11+，无需安装第三方包。

```bash
cd ai-native-starter
python -m ainative.cli init
python -m ainative.cli serve
```

浏览器打开 <http://127.0.0.1:8000>，点击“运行本月监测”。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 经营分析沙盒

沙盒可以生成一个具备销售、采购、库存和复式记账逻辑的虚构制造企业，并用隐藏
Ground Truth 评测经营分析 Agent：

```bash
python -m ainative.cli sandbox-generate \
  --seed 61 \
  --output ./data/benchmarks/revenue-profit

python -m ainative.cli sandbox-score \
  --benchmark ./data/benchmarks/revenue-profit \
  --answer ./answer.json
```

详细格式和公开/私有数据边界参见
[`docs/sandbox/quickstart.md`](docs/sandbox/quickstart.md)。

本地 Codex 接手开发时，请先阅读 [`AGENTS.md`](AGENTS.md) 和
[`docs/handoff/PROJECT_HANDOFF.md`](docs/handoff/PROJECT_HANDOFF.md)。测试记录与后续
路线分别位于 [`TEST_REPORT.md`](docs/handoff/TEST_REPORT.md) 和
[`ROADMAP.md`](docs/handoff/ROADMAP.md)。

## V0.1 的核心约束

- 每个 AI 同事必须拥有责任契约；
- 每个任务必须有唯一主责 AI 和成功标准；
- 每个动作都要经过治理判断；
- 关键结论必须携带证据和置信度；
- 每次执行必须生成结构化产物；
- 正式发布等高影响动作必须先审批；
- 对话不是任务和产物的唯一载体。

## 目录

```text
ainative/
  core/          通用对象、治理策略、存储与任务引擎
  runtime/       可替换的 Agent Runtime 接口及确定性演示实现
  domain/        领域包；当前包含经营分析
  api/           零依赖 HTTP API
config/          AI 同事责任契约
sample_data/     可重复验证的经营数据
web/             行动中心、责任空间、任务与 AI 同事视图
tests/           核心闭环测试
```

## 从演示版走向企业版

通用内核的边界已经固定，企业落地时替换适配器即可：

- `JsonStore` → PostgreSQL；
- `DeterministicRuntime` → LangGraph / AgentScope；
- 本地数据工具 → 集团数据通道 CLI；
- 规则模型 → 集团 Model Gateway；
- 本地策略 → 统一权限与审批平台；
- 文件产物 → 内网对象存储。

建议先用第二个明显不同的场景验证核心模型，再把 V0.1 升级为 SDK 或平台。
