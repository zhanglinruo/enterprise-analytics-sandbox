# Linxi Sandbox Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为公开经营分析 ZIP 增加一个使用 OpenAI Responses API、仅能调用受控只读工具、能冻结结构化答案的最小独立“林析”Agent。

**Architecture:** CLI 把公开 ZIP 交给 `PackageGuard` 解压到独立临时目录，`SandboxReadOnlyToolkit` 只暴露公共文档读取、Schema 检查、只读 SQL 和答案提交五种能力。`OpenAIResponsesRuntime` 执行有预算的函数调用循环，`LinxiSandboxAnalyst` 负责生命周期、审计、原子写入和错误归类；评分器不进入运行时依赖图。

**Tech Stack:** Python 3.11+、标准库 `sqlite3`/`zipfile`/`tempfile`/`unittest`、`openai>=2,<3`、`python-dotenv>=1,<2`、OpenAI Responses API、SQLite URI 只读连接。

## Global Constraints

- 默认模型固定为 `gpt-5.6-terra`，默认 `reasoning.effort` 固定为 `medium`。
- 仅允许通过项目根目录 `.env` 或进程环境读取 `OPENAI_API_KEY`；环境变量优先，任何日志、异常和运行产物不得包含密钥值。
- `.env`、`.env.*`、数据库、ZIP、private state、score report 和 Agent 运行目录不得提交；仅 `.env.example` 可提交。
- 公开包最多 100 个成员、总解压体积 256 MiB、单文件 128 MiB，且必须恰好包含一个 `data/enterprise.db`。
- 工具总调用上限 30，SQL 调用上限 20，单次 SQL 最多返回 200 行、序列化结果最多 64 KiB。
- SQLite 同时使用 `mode=ro&immutable=1`、`PRAGMA query_only=ON`、authorizer、禁用扩展加载和 progress handler。
- Agent 只能访问包内公开文档和数据库；不得获得 Shell、Python 执行、任意路径、网络搜索、evaluator、private state、Ground Truth 或评分能力。
- 第一次通过 `AgentAnswer.from_dict` 的 `submit_answer` 必须立即冻结；评分前不得再调用模型。
- 默认测试套件绝不调用真实 OpenAI API；真实验收仅在 `LINXI_LIVE_TEST=1` 时运行。
- 保留现有 `DeterministicRuntime`、`AINativeEngine`、生成与评分命令的行为。
- 所有行为变更严格遵循 failing test → minimal implementation → passing test → commit。

---

## File Structure

| Path | Responsibility |
|---|---|
| `ainative/sandbox/agent_config.py` | 加载 `.env`，验证模型、推理强度和预算，生成不泄密配置。 |
| `ainative/sandbox/agent_package.py` | 验证公开 ZIP、逐成员安全解压、定位允许读取的公共资产、清理临时目录。 |
| `ainative/sandbox/agent_tools.py` | 只读 SQLite 会话、五个工具实现、预算、结果截断与 JSONL 审计。 |
| `ainative/runtime/openai_responses.py` | Responses API 函数调用循环、重试、最终答案冻结、usage 汇总。 |
| `ainative/sandbox/agent.py` | 林析责任提示、单次运行编排、产物原子写入、错误码和运行元数据。 |
| `ainative/cli.py` | 新增 `sandbox-agent-run` 参数和退出码映射。 |
| `tests/sandbox/agent_fixtures.py` | 最小公开 ZIP/SQLite 与假 Responses 客户端，禁止复用私有答案 helper。 |
| `tests/sandbox/test_agent_config.py` | 配置与密钥脱敏测试。 |
| `tests/sandbox/test_agent_package.py` | ZIP 安全边界和临时目录清理测试。 |
| `tests/sandbox/test_agent_tools.py` | 只读 SQL、预算、截断和审计测试。 |
| `tests/sandbox/test_openai_responses.py` | 假客户端驱动的 Runtime 契约测试。 |
| `tests/sandbox/test_agent_service.py` | 成功/失败生命周期与冻结产物测试。 |
| `tests/sandbox/test_agent_cli.py` | CLI 参数、退出码与隔离边界测试。 |
| `tests/sandbox/test_agent_live.py` | 显式开启的 seed 61 真实 API 验收。 |
| `.env.example` | 无密钥的环境变量模板。 |
| `.gitignore` | 排除真实环境文件和本地运行产物。 |
| `pyproject.toml` | 声明两项必要运行依赖。 |
| `docs/sandbox/quickstart.md` | 林析命令、ZIP 用途、安全边界与验收说明。 |
| `docs/experiments/external-agent-validation-001.md` | 仅在真实运行完成后登记冻结答案的事实信息。 |

---

### Task 1: Configuration and Secret Boundary

**Files:**
- Create: `.env.example`
- Create: `ainative/sandbox/agent_config.py`
- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Create: `tests/sandbox/test_agent_config.py`

**Interfaces:**
- Produces: `LinxiConfig`, `ConfigurationError`, `load_linxi_config(project_root: Path, environ: Mapping[str, str] | None = None) -> LinxiConfig`
- `LinxiConfig` fields: `api_key`, `model`, `reasoning_effort`, `max_tool_calls`, `max_sql_queries`, `query_row_limit`, `query_byte_limit`, `api_timeout_seconds`, `api_retry_limit`
- Secret contract: `api_key` uses `repr=False`; `public_metadata()` excludes it.

- [ ] **Step 1: Write failing configuration tests**

```python
class LinxiConfigTest(unittest.TestCase):
    def test_loads_root_dotenv_without_overriding_process_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "OPENAI_API_KEY=file-secret\n"
                "OPENAI_MODEL=gpt-5.6-terra\n"
                "OPENAI_REASONING_EFFORT=medium\n",
                encoding="utf-8",
            )
            config = load_linxi_config(
                root,
                {"OPENAI_API_KEY": "process-secret"},
            )
            self.assertEqual(config.api_key, "process-secret")
            self.assertEqual(config.model, "gpt-5.6-terra")
            self.assertNotIn("process-secret", repr(config))
            self.assertNotIn("api_key", config.public_metadata())

    def test_missing_key_and_invalid_effort_fail_without_echoing_values(self):
        with self.assertRaisesRegex(ConfigurationError, "OPENAI_API_KEY"):
            load_linxi_config(Path.cwd(), {})
        secret = "sk-test-never-log"
        with self.assertRaises(ConfigurationError) as caught:
            load_linxi_config(
                Path.cwd(),
                {
                    "OPENAI_API_KEY": secret,
                    "OPENAI_REASONING_EFFORT": "maximum",
                },
            )
        self.assertNotIn(secret, str(caught.exception))
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `python -m unittest tests.sandbox.test_agent_config -v`

Expected: FAIL because `ainative.sandbox.agent_config` does not exist.

- [ ] **Step 3: Add dependencies, ignore rules, environment template, and minimal loader**

Set `pyproject.toml` project dependencies exactly to:

```toml
dependencies = [
  "openai>=2,<3",
  "python-dotenv>=1,<2",
]
```

Append to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
data/agent-runs/
```

Create `.env.example`:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-terra
OPENAI_REASONING_EFFORT=medium
```

Implement:

```python
@dataclass(frozen=True)
class LinxiConfig:
    api_key: str = field(repr=False)
    model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    max_tool_calls: int = 30
    max_sql_queries: int = 20
    query_row_limit: int = 200
    query_byte_limit: int = 65_536
    api_timeout_seconds: float = 120.0
    api_retry_limit: int = 2

    def public_metadata(self) -> dict[str, object]:
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_tool_calls": self.max_tool_calls,
            "max_sql_queries": self.max_sql_queries,
            "query_row_limit": self.query_row_limit,
            "query_byte_limit": self.query_byte_limit,
            "api_timeout_seconds": self.api_timeout_seconds,
            "api_retry_limit": self.api_retry_limit,
        }
```

`load_linxi_config` must call `dotenv_values(project_root / ".env")`, merge only `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_REASONING_EFFORT` beneath the supplied/process environment, strip values, require a key, require a non-empty model, and accept only `minimal|low|medium|high|xhigh`.

- [ ] **Step 4: Run focused tests and the existing suite**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_config -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: configuration tests pass and the existing 25 tests remain green.

- [ ] **Step 5: Commit the configuration boundary**

```powershell
git add .env.example .gitignore pyproject.toml ainative/sandbox/agent_config.py tests/sandbox/test_agent_config.py
git commit -m "feat: add Linxi agent configuration boundary"
```

---

### Task 2: Safe Public Package Preparation

**Files:**
- Create: `ainative/sandbox/agent_package.py`
- Create: `tests/sandbox/agent_fixtures.py`
- Create: `tests/sandbox/test_agent_package.py`

**Interfaces:**
- Consumes: standard library only.
- Produces: `PackageValidationError`, `PreparedPackage`, `prepare_public_package(archive_path: Path) -> PreparedPackage`
- `PreparedPackage` fields: `archive_path`, `archive_sha256`, `root`, `database_path`, `public_documents`, `_temporary_directory`
- `PreparedPackage.close() -> None`, `__enter__`, and `__exit__`; `public_documents` maps POSIX relative names to resolved package-local paths.

- [ ] **Step 1: Add a deterministic public-package fixture**

`write_public_package(destination: Path, members: Mapping[str, bytes] | None = None) -> Path` must create a minimal database with table `public_metric(period TEXT, value INTEGER)`, include:

```text
data/enterprise.db
task/analysis_question.md
schema/data_dictionary.md
schema/relationships.md
semantic/metrics.json
manifest.json
```

The fixture must contain no private state, Cause IDs, scorer imports, or known-correct answer.

- [ ] **Step 2: Write failing acceptance and malicious ZIP tests**

Cover these exact cases:

```python
def test_prepares_expected_public_assets_and_cleans_up(self):
    archive = write_public_package(self.root / "public.zip")
    with prepare_public_package(archive) as package:
        extracted = package.root
        self.assertTrue(package.database_path.is_file())
        self.assertIn("task/analysis_question.md", package.public_documents)
    self.assertFalse(extracted.exists())

def test_rejects_path_traversal_drive_path_and_absolute_path(self):
    for member in ("../outside.txt", "C:/outside.txt", "/outside.txt"):
        archive = write_zip_with_member(self.root / "bad.zip", member, b"x")
        with self.assertRaises(PackageValidationError):
            prepare_public_package(archive)

def test_rejects_symlink_private_names_oversized_and_excess_members(self):
    symlink = ZipInfo("schema/link.md")
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    cases = [
        write_zip_infos(self.root / "symlink.zip", [(symlink, b"target")]),
        write_zip_with_member(self.root / "private.zip", "private-state.json", b"{}"),
        write_zip_infos(
            self.root / "many.zip",
            [(ZipInfo(f"schema/{index}.md"), b"x") for index in range(101)],
        ),
    ]
    for archive in cases:
        with self.subTest(archive=archive.name):
            with self.assertRaises(PackageValidationError):
                prepare_public_package(archive)
```

Create a symlink entry by setting `ZipInfo.external_attr = (stat.S_IFLNK | 0o777) << 16`. Test the private-name tokens case-insensitively: `private`, `ground_truth`, `score-report`, `answer`. Test 101 members, one declared member over 128 MiB, and total declared size over 256 MiB without allocating those payloads.

- [ ] **Step 3: Run tests and verify the missing implementation failure**

Run: `python -m unittest tests.sandbox.test_agent_package -v`

Expected: FAIL because package preparation types are absent.

- [ ] **Step 4: Implement validation before any extraction**

For every `ZipInfo`:

```python
pure = PurePosixPath(info.filename.replace("\\", "/"))
if (
    not info.filename
    or pure.is_absolute()
    or ".." in pure.parts
    or re.match(r"^[A-Za-z]:", info.filename)
):
    raise PackageValidationError("Unsafe archive member path")
mode = (info.external_attr >> 16) & 0xFFFF
if stat.S_ISLNK(mode) or (mode and not stat.S_ISREG(mode) and not stat.S_ISDIR(mode)):
    raise PackageValidationError("Unsupported archive member type")
```

Validate counts, declared sizes, duplicate normalized names, banned name tokens, exactly one `data/enterprise.db`, required public documents, and the manifest before creating `TemporaryDirectory(prefix="linxi-public-")`. Then copy each validated file with `archive.open(info)` and `shutil.copyfileobj`; resolve the target and prove `target.is_relative_to(root.resolve())`.

Compute SHA-256 by streaming the original archive. On every validation/extraction error, clean up before re-raising.

- [ ] **Step 5: Run focused tests and compile**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_package -v
python -m compileall -q ainative tests
```

Expected: all package tests pass; compilation exits zero.

- [ ] **Step 6: Commit the package guard**

```powershell
git add ainative/sandbox/agent_package.py tests/sandbox/agent_fixtures.py tests/sandbox/test_agent_package.py
git commit -m "feat: validate and isolate public agent packages"
```

---

### Task 3: Read-Only SQLite Toolkit and Audit

**Files:**
- Create: `ainative/sandbox/agent_tools.py`
- Create: `tests/sandbox/test_agent_tools.py`
- Modify: `tests/sandbox/agent_fixtures.py`

**Interfaces:**
- Consumes: `LinxiConfig`, `PreparedPackage`, `AgentAnswer.from_dict`.
- Produces: `ToolBudgetExceeded`, `ToolInputError`, `ToolResult`, `SubmittedAnswer`, `SandboxReadOnlyToolkit`.
- `ToolResult` fields: `ok: bool`, `content: dict[str, object]`, `truncated: bool = False`.
- `SubmittedAnswer` fields: `payload: dict[str, object]`, `answer: AgentAnswer`.
- `SandboxReadOnlyToolkit.dispatch(name: str, arguments: Mapping[str, object]) -> ToolResult | SubmittedAnswer`.
- Public methods: `read_public_document(name)`, `list_tables()`, `describe_table(table)`, `execute_select(sql)`, `submit_answer(payload)`.
- Read-only counters: `tool_call_count`, `sql_query_count`.

- [ ] **Step 1: Write failing tests for the five allowed tools**

Verify:

- public documents are selected by exact relative name, never an arbitrary path;
- `list_tables` excludes `sqlite_%`;
- `describe_table` accepts only a name returned by `list_tables`;
- `execute_select` returns ordered `columns` and JSON-safe `rows`;
- `submit_answer` returns an `AgentAnswer` for valid payload;
- unknown tools and unknown arguments return controlled `ToolInputError`.

Use `self.addCleanup(toolkit.close)` so Windows proves every SQLite handle closes.

- [ ] **Step 2: Write failing SQLite security and budget tests**

Reject these strings:

```sql
INSERT INTO public_metric VALUES ('x', 1)
DROP TABLE public_metric
ATTACH DATABASE 'other.db' AS other
SELECT 1; SELECT 2
PRAGMA writable_schema=ON
VACUUM
```

Also verify:

- a `WITH` query containing only a `SELECT` is accepted;
- authorizer denial still protects the connection if lexical checks miss an operation;
- extension loading is disabled;
- the 201st row is truncated to 200 with `truncated=true`;
- serialization over 65,536 bytes is truncated without emitting invalid JSON;
- the 21st SQL and 31st total tool call raise `ToolBudgetExceeded`;
- a recursive query is interrupted by the progress/deadline handler;
- the audit file contains tool name, ordinal, sanitized arguments, status, truncation, duration and result SHA-256;
- the audit file contains neither a fake API key nor package/output absolute paths nor full document/query results.

- [ ] **Step 3: Run tests and verify failure**

Run: `python -m unittest tests.sandbox.test_agent_tools -v`

Expected: FAIL because `SandboxReadOnlyToolkit` is not implemented.

- [ ] **Step 4: Implement the read-only connection and authorizer**

Open with:

```python
uri = f"{package.database_path.resolve().as_uri()}?mode=ro&immutable=1"
connection = sqlite3.connect(uri, uri=True)
connection.execute("PRAGMA query_only = ON")
connection.enable_load_extension(False)
```

Install an authorizer that returns `SQLITE_DENY` for `SQLITE_INSERT`, `SQLITE_UPDATE`, `SQLITE_DELETE`, `SQLITE_CREATE_*`, `SQLITE_DROP_*`, `SQLITE_ALTER_TABLE`, `SQLITE_ATTACH`, `SQLITE_DETACH`, `SQLITE_TRANSACTION`, `SQLITE_SAVEPOINT`, `SQLITE_REINDEX`, `SQLITE_ANALYZE`, and `SQLITE_PRAGMA` except internally issued read-only schema inspection. Keep schema inspection on dedicated local helpers so model SQL cannot invoke PRAGMA.

Install a progress handler that checks both an operation counter and `time.monotonic()` deadline. Convert `sqlite3.DatabaseError` to sanitized `ToolInputError` without file paths.

- [ ] **Step 5: Implement dispatch, result limits, and audit**

Dispatch must require exact argument keys:

```python
{
    "read_public_document": {"name"},
    "list_tables": set(),
    "describe_table": {"table"},
    "execute_select": {"sql"},
    "submit_answer": {"payload"},
}
```

Before each dispatch increment and enforce the total budget; increment SQL budget before executing SQL. Normalize SQL by stripping comments only for start-token and semicolon validation; rely on the authorizer for semantic enforcement.

Serialize rows incrementally, stopping before either the row or byte limit. Audit JSONL with one `json.dumps(record, ensure_ascii=False)` object per line; include SQL text for reproducibility, but for document/result content include only byte count and SHA-256.

- [ ] **Step 6: Run focused tests and the full suite**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_tools -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: toolkit/security tests and all pre-existing tests pass.

- [ ] **Step 7: Commit the controlled toolkit**

```powershell
git add ainative/sandbox/agent_tools.py tests/sandbox/agent_fixtures.py tests/sandbox/test_agent_tools.py
git commit -m "feat: add audited read-only analysis tools"
```

---

### Task 4: OpenAI Responses Runtime

**Files:**
- Create: `ainative/runtime/openai_responses.py`
- Create: `tests/sandbox/test_openai_responses.py`
- Modify: `tests/sandbox/agent_fixtures.py`

**Interfaces:**
- Consumes: `AgentRuntime`, `LinxiConfig`, `SandboxReadOnlyToolkit`.
- Produces: `RuntimeFailure`, `RuntimeBudgetExceeded`, `RuntimeResult`, `OpenAIResponsesRuntime`.
- `RuntimeResult` fields: `answer_payload`, `tool_call_count`, `sql_query_count`, `api_retry_count`, `usage`.
- Constructor: `OpenAIResponsesRuntime(client: object, config: LinxiConfig, toolkit: SandboxReadOnlyToolkit)`.
- Method: `execute_task(task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]`, preserving the existing abstract base signature.

- [ ] **Step 1: Add a scripted fake Responses client**

Create test-only objects with the exact fields consumed by production:

```python
@dataclass
class FakeFunctionCall:
    type: str
    name: str
    arguments: str
    call_id: str

@dataclass
class FakeResponse:
    output: list[FakeFunctionCall]
    usage: object | None = None

class ScriptedResponses:
    def __init__(self, steps):
        self.steps = deque(steps)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        step = self.steps.popleft()
        if isinstance(step, Exception):
            raise step
        return step
```

The outer fake client exposes `.responses`.

- [ ] **Step 2: Write a failing happy-path contract test**

Script:

```text
list_tables
→ describe_table(table="public_metric")
→ execute_select(sql="SELECT period, value FROM public_metric ORDER BY period")
→ submit_answer(payload=<valid AgentAnswer mapping>)
```

Assert every request uses:

```python
{
    "model": "gpt-5.6-terra",
    "reasoning": {"effort": "medium"},
    "parallel_tool_calls": False,
    "store": False,
}
```

Assert tool definitions contain exactly the five names with `strict=True` and `additionalProperties=False`. Assert each next `input` contains the prior response output plus matching `function_call_output` with the original `call_id`. Assert execution stops immediately after the first valid `submit_answer`.

- [ ] **Step 3: Write failing error, retry, and correction tests**

Cover:

- invalid JSON function arguments produce a controlled tool output, not a crash;
- an invalid final payload gets exactly one schema-correction message and may submit once more;
- a second invalid payload raises `RuntimeFailure`;
- `APITimeoutError`, `APIConnectionError`, and `RateLimitError` retry at most two times;
- authentication, permission, bad request, and model-not-found errors do not retry;
- tool/SQL budget exhaustion raises `RuntimeBudgetExceeded` and does not synthesize an answer;
- a response with no function call and no submitted answer fails explicitly;
- usage totals are collected without storing reasoning text.

Patch the retry sleeper in tests so no wall-clock delay occurs.

- [ ] **Step 4: Run tests and verify the missing runtime failure**

Run: `python -m unittest tests.sandbox.test_openai_responses -v`

Expected: FAIL because `OpenAIResponsesRuntime` does not exist.

- [ ] **Step 5: Define strict tool schemas and implement the stateless loop**

Define the five function tools as immutable module data. `submit_answer` must spell out the full `AgentAnswer` JSON Schema, require every top-level key, restrict anomaly direction to `up|down|stable`, bound confidence to `[0,1]`, require evidence arrays, and disallow unknown properties at every object level.

For privacy and deterministic testability, each call uses `store=False`; continue by replaying `response.output` and appending:

```python
{
    "type": "function_call_output",
    "call_id": item.call_id,
    "output": json.dumps(tool_result, ensure_ascii=False),
}
```

Do not use `previous_response_id`. Do not inspect or persist reasoning content. Instantiate the real SDK later with `max_retries=0`; this class owns the exact two-retry policy using bounded backoff.

- [ ] **Step 6: Run runtime tests and compile**

Run:

```powershell
python -m unittest tests.sandbox.test_openai_responses -v
python -m compileall -q ainative tests
```

Expected: fake-client contract tests pass without network traffic.

- [ ] **Step 7: Commit the Responses runtime**

```powershell
git add ainative/runtime/openai_responses.py tests/sandbox/test_openai_responses.py tests/sandbox/agent_fixtures.py
git commit -m "feat: add bounded OpenAI Responses runtime"
```

---

### Task 5: Linxi Run Lifecycle and Frozen Artifacts

**Files:**
- Create: `ainative/sandbox/agent.py`
- Create: `tests/sandbox/test_agent_service.py`

**Interfaces:**
- Consumes: `load_linxi_config`, `prepare_public_package`, `SandboxReadOnlyToolkit`, `OpenAIResponsesRuntime`.
- Produces: `AgentRunError`, `AgentRunResult`, `run_linxi_agent`.
- Exact signature: `run_linxi_agent(package_path: Path, output_dir: Path, *, project_root: Path, environ: Mapping[str, str] | None = None, client_factory: Callable[[LinxiConfig], object] = create_openai_client) -> AgentRunResult`.

- `AgentRunResult` fields: `run_id`, `status`, `answer_path`, `metadata_path`, `audit_path`.
- Error categories: `configuration`, `package_security`, `api_failure`, `budget_exhausted`, `invalid_answer`, `incomplete`.

- [ ] **Step 1: Write failing success lifecycle test**

Use a fake client factory and a minimal public package. Assert:

- output directory must not pre-exist or must be empty;
- success creates exactly `raw-answer.json`, `run-metadata.json`, and `tool-audit.jsonl`;
- `raw-answer.json` equals the first valid submitted mapping;
- metadata status is `completed`;
- metadata includes run ID, `business_analyst`, responsibility version, model, effort, start/end/duration, package SHA-256, tool/SQL counts, retry count and usage;
- metadata and audit do not include the fake key, `.env` content, absolute paths, private state, scores, or reasoning;
- the extracted temporary directory and SQLite connection are gone on Windows after return.

- [ ] **Step 2: Write failing failure lifecycle and atomicity tests**

For configuration, package, permanent API, budget, and invalid-answer errors assert:

- `run-metadata.json` exists with a stable category and `failed` status whenever output initialization succeeded;
- `raw-answer.json` does not exist;
- no `.tmp` file remains;
- exception text does not expose the key or absolute package path;
- a second model answer after a valid submit is never requested.

Patch `Path.replace` to fail once and prove a partially written answer is never mistaken for a completed answer.

- [ ] **Step 3: Run tests and verify missing service failure**

Run: `python -m unittest tests.sandbox.test_agent_service -v`

Expected: FAIL because `run_linxi_agent` is absent.

- [ ] **Step 4: Implement responsibility prompt and real client factory**

The system instruction identifies 林析 as `business_analyst`, asks it to identify material anomalies, quantify impact, support causes with public evidence, state unknowns, and submit the required schema. It must state the read-only/tool budgets and forbidden access boundary, but must not contain scenario ID, Cause ID, target range, scorer weights, expected SQL, forbidden claims, or private filenames beyond the generic boundary.

Create the SDK client exactly as:

```python
OpenAI(
    api_key=config.api_key,
    timeout=config.api_timeout_seconds,
    max_retries=0,
)
```

- [ ] **Step 5: Implement atomic run artifacts and cleanup**

Create a stable run ID from UTC start time plus eight random hex characters; randomness is for run identity, never sandbox data. Write JSON through a sibling `.<name>.tmp`, flush and `os.fsync`, then `Path.replace`.

Initialize metadata as `running`, transition once to `completed` or `failed`, and sanitize errors to category plus a bounded message. Use nested context managers so toolkit closes before package cleanup.

Never import `DeterministicScorer`, `load_generation_result`, `GroundTruth`, or private-state helpers in this module.

- [ ] **Step 6: Run service tests and the full suite**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_service -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: lifecycle tests pass and no regression occurs.

- [ ] **Step 7: Commit the Linxi service**

```powershell
git add ainative/sandbox/agent.py tests/sandbox/test_agent_service.py
git commit -m "feat: orchestrate auditable Linxi agent runs"
```

---

### Task 6: CLI Command and Exit Codes

**Files:**
- Modify: `ainative/cli.py`
- Create: `tests/sandbox/test_agent_cli.py`

**Interfaces:**
- Consumes: `run_linxi_agent`, `AgentRunError`.
- Produces: `sandbox-agent-run --package PATH --output PATH`.
- Refactor: `main(argv: Sequence[str] | None = None) -> int`; existing module entry remains `raise SystemExit(main())`.
- Exit map: success `0`; argument/config/answer schema `2`; package/SQLite security `5`; permanent API `6`; budget/incomplete `7`.

- [ ] **Step 1: Write failing in-process CLI tests**

Patch `ainative.cli.run_linxi_agent` and call:

```python
exit_code = main([
    "sandbox-agent-run",
    "--package", str(archive),
    "--output", str(output),
])
```

Assert success prints one JSON object with run ID, status and relative artifact names. For each `AgentRunError.category`, assert the documented exit code and a sanitized one-line stderr message.

Also run the parser against missing `--package`/`--output`, an existing non-empty output directory, a directory instead of ZIP, and a path named `private-state.json`.

- [ ] **Step 2: Write a subprocess isolation test without real API**

Run `python -m ainative.cli sandbox-agent-run --help` and assert both flags appear and exit zero. Keep full successful orchestration in the in-process fake-client test so CI cannot contact the network.

- [ ] **Step 3: Run tests and verify command absence**

Run: `python -m unittest tests.sandbox.test_agent_cli -v`

Expected: FAIL because the parser does not recognize `sandbox-agent-run`.

- [ ] **Step 4: Add the parser and dispatch**

Add:

```python
agent_parser = sub.add_parser(
    "sandbox-agent-run",
    help="Run Linxi against one isolated public benchmark ZIP",
)
agent_parser.add_argument("--package", required=True, type=Path)
agent_parser.add_argument("--output", required=True, type=Path)
```

Call `run_linxi_agent(args.package, args.output, project_root=ROOT)`, print JSON only on success, and use a single category-to-code mapping for errors. Do not accept benchmark directories, evaluator paths, private state, scores, model prompt overrides, arbitrary working directories, or extra tools.

- [ ] **Step 5: Run CLI tests, existing CLI vertical slice, and compile**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_cli tests.sandbox.test_cli -v
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q ainative tests
```

Expected: old generate/score flow and new command tests all pass.

- [ ] **Step 6: Commit the CLI**

```powershell
git add ainative/cli.py tests/sandbox/test_agent_cli.py
git commit -m "feat: expose Linxi sandbox agent CLI"
```

---

### Task 7: Documentation, Opt-In Live Acceptance, and EAV001 Freeze

**Files:**
- Modify: `README.md`
- Modify: `docs/sandbox/quickstart.md`
- Create: `tests/sandbox/test_agent_live.py`
- Modify after a successful live run only: `docs/experiments/external-agent-validation-001.md`

**Interfaces:**
- Consumes: checked-in seed 61 handoff location under ignored `data/benchmarks/external-agent-validation-001/participant-handoff/`.
- Produces: explicit operator workflow and an opt-in real API test.

- [ ] **Step 1: Write the skipped-by-default live acceptance test**

Use:

```python
@unittest.skipUnless(
    os.environ.get("LINXI_LIVE_TEST") == "1",
    "set LINXI_LIVE_TEST=1 to run the real OpenAI acceptance test",
)
class LinxiLiveAcceptanceTest(unittest.TestCase):
    def test_seed_61_public_handoff_freezes_first_answer(self):
        result = run_linxi_agent(
            PACKAGE,
            RUN_OUTPUT,
            project_root=ROOT,
        )
        payload = json.loads(result.answer_path.read_text(encoding="utf-8"))
        AgentAnswer.from_dict(payload)
        self.assertEqual(result.status, "completed")
```

The test must fail with a clear message if the exact seed 61 ZIP is absent, and must refuse to overwrite a prior run directory. It must not call the scorer.

- [ ] **Step 2: Document why ZIP exists and how to run Linxi**

Update the README and quickstart to state:

- ZIP is the immutable, hashable public handoff that simulates what an external participant receives;
- it prevents accidental access to the generator directory, database siblings, private state and score report;
- normal app/demo commands still work without an API key, while the Agent command requires `pip install -e .` and root `.env`;
- the command:

```powershell
python -m ainative.cli sandbox-agent-run `
  --package .\data\benchmarks\external-agent-validation-001\participant-handoff\bench_2a6511aeb612.zip `
  --output .\data\agent-runs\EAV001-INTERNAL-01
```

- live acceptance command:

```powershell
$env:LINXI_LIVE_TEST="1"
python -m unittest tests.sandbox.test_agent_live -v
```

- score only after the three run artifacts are frozen and copied to an evidence location outside the model-visible package.

- [ ] **Step 3: Verify default tests skip network access**

Run:

```powershell
python -m unittest tests.sandbox.test_agent_live -v
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q ainative tests
git status --short
```

Expected: live test reports skipped; all other tests pass; only intended source/docs changes appear.

- [ ] **Step 4: Commit documentation and opt-in acceptance**

```powershell
git add README.md docs/sandbox/quickstart.md tests/sandbox/test_agent_live.py
git commit -m "docs: add Linxi agent acceptance workflow"
```

- [ ] **Step 5: Run the real seed 61 attempt exactly once**

Preconditions:

```powershell
Test-Path .\.env
Get-FileHash .\data\benchmarks\external-agent-validation-001\participant-handoff\bench_2a6511aeb612.zip -Algorithm SHA256
git status --short
```

Expected ZIP SHA-256: `cef9e8c59003a12b54afbdc884b85c3de0af23d94518db3808e54ecec9d6c2cf`.

Then run:

```powershell
$env:LINXI_LIVE_TEST="1"
python -m unittest tests.sandbox.test_agent_live -v
```

Do not rerun because of a low score. A rerun is allowed only for a recorded infrastructure failure that produced no `raw-answer.json`.

- [ ] **Step 6: Freeze, hash, and inspect before scoring**

Run:

```powershell
Get-FileHash .\data\agent-runs\EAV001-INTERNAL-01\raw-answer.json -Algorithm SHA256
Get-Content .\data\agent-runs\EAV001-INTERNAL-01\run-metadata.json
Select-String -Path .\data\agent-runs\EAV001-INTERNAL-01\* -Pattern 'sk-' -SimpleMatch
```

Expected: answer hash is recorded, metadata status is `completed`, secret scan returns no matches. Copy the three immutable run artifacts to the experiment evidence directory before any score command.

- [ ] **Step 7: Score only the frozen raw answer and update the registry**

Use the existing private benchmark directory only from the scorer process:

```powershell
python -m ainative.cli sandbox-score `
  --benchmark .\data\benchmarks\external-agent-validation-001 `
  --answer .\data\agent-runs\EAV001-INTERNAL-01\raw-answer.json
```

Update `docs/experiments/external-agent-validation-001.md` with model, reasoning effort, UTC timing, intervention status, answer hash/path, schema result, deterministic dimensions, observed errors and evidence. Do not add Ground Truth, hidden Cause IDs, private SQL, API key, reasoning traces, or prompt changes.

- [ ] **Step 8: Run final verification and commit the factual run record**

Run:

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q ainative tests
git diff --check
git status --short
```

Expected: all non-live tests pass, live test is skipped without the flag, compilation and whitespace checks pass, generated artifacts remain ignored.

Commit only the experiment register:

```powershell
git add docs/experiments/external-agent-validation-001.md
git commit -m "docs: record first Linxi external validation run"
```

---

## Final Review Gate

- [ ] Every design requirement maps to Tasks 1–7: configuration, ZIP isolation, five tools, SQLite hardening, Responses loop, retry/budget policy, answer schema/freeze, artifacts, CLI, default-off live test, and EAV001 registration.
- [ ] Search the plan and implementation for `private-state`, `GroundTruth`, `DeterministicScorer`, scorer imports, Cause IDs and secret values in the runtime dependency graph; only documentation describing the forbidden boundary may mention them.
- [ ] Confirm every type and signature used by later tasks exactly matches the producing task’s Interfaces block.
- [ ] Confirm `OpenAIResponsesRuntime` remains substitutable for `AgentRuntime.execute_task(task, context)`.
- [ ] Confirm Windows cleanup tests prove both ZIP temporary directories and SQLite handles close.
- [ ] Confirm no successful path can write `run-metadata.json: completed` before `raw-answer.json` is atomically frozen.
- [ ] Confirm no test outside `test_agent_live.py` can instantiate a real OpenAI client or access the network.
- [ ] Confirm generated databases, ZIPs, `.env`, raw answers, audit logs and score reports are ignored and absent from staged changes.
