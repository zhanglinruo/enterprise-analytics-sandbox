# 经营分析沙盒快速开始

## 1. 生成公开考试包

```bash
python -m ainative.cli sandbox-generate \
  --seed 61 \
  --output ./data/benchmarks/revenue-profit
```

命令会在输出目录生成：

- `enterprise.db`：经过一致性校验的工作数据库；
- `bench_*.zip`：可交给待评测 Agent 的公开考试包；
- `private-state.json`：隐藏答案和可复现信息，不得交给待评测 Agent。

公开 ZIP 包含 SQLite、15 张 CSV、数据字典、关系说明、指标定义和分析任务书，不包含场景原因、原因权重或禁判项。

## 2. 提交结构化答案

待评测 Agent 的答案保存为 JSON：

```json
{
  "anomalies": [
    {"metric": "revenue", "direction": "up", "magnitude": 1000000},
    {"metric": "gross_profit", "direction": "down", "magnitude": 100000}
  ],
  "causes": [
    {
      "cause": "原因标识",
      "confidence": 0.85,
      "evidence": [
        {"table": "表名", "field": "字段名", "value": 123}
      ]
    }
  ],
  "unknowns": ["仅凭数据无法确认的业务信息"],
  "recommendations": ["下一步行动建议"]
}
```

## 3. 自动评分

```bash
python -m ainative.cli sandbox-score \
  --benchmark ./data/benchmarks/revenue-profit \
  --answer ./answer.json
```

评分结果同时输出到终端和基准目录的 `score-report.json`，包括异常识别、数字准确性、根因、证据、判断边界和建议六个维度。

相同有效种子会生成相同的基准 ID 和数据库校验值。若某个种子的经营效果未达到预设区间，生成器最多进行两次确定性重试，并在结果中返回最终有效种子。

第一阶段只接受结构化 JSON，不包含自然语言答案抽取、Web 页面、真实企业数据合成或直接连接外部 Agent。
