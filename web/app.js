const state = { data: null, view: "action" };
const titles = {
  action: ["行动中心", "聚焦需要人介入的判断，其余工作交给 AI 同事持续推进。"],
  space: ["责任空间", "查看长期目标、责任边界、指标状态与持续行动。"],
  colleague: ["AI 同事", "以责任契约管理能力、授权范围与工作表现。"],
  artifacts: ["产物中心", "结构化保存可编辑、可版本化、可追溯的工作结果。"]
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) throw new Error((await response.json()).error || "请求失败");
  return response.json();
}

function badge(status) {
  const map = {
    pending: ["待审批", "pending"], waiting_approval: ["待审批", "pending"],
    completed: ["已完成", "complete"], published: ["已发布", "complete"],
    draft: ["草稿", "draft"], active: ["运行中", "complete"],
    rejected: ["已退回", "pending"], failed: ["未通过", "pending"]
  };
  const item = map[status] || [status, "draft"];
  return `<span class="badge ${item[1]}">${item[0]}</span>`;
}

function renderMetrics() {
  const s = state.data.summary;
  const rows = [
    ["活跃责任空间", s.active_spaces],
    ["进行中任务", s.open_tasks],
    ["待我审批", s.pending_approvals],
    ["已发布产物", s.published_artifacts]
  ];
  document.querySelector("#metrics").innerHTML = rows.map(
    ([label, value]) => `<article class="metric"><small>${label}</small><strong>${value}</strong></article>`
  ).join("");
}

function approvalItem(approval) {
  const task = state.data.tasks.find(x => x.id === approval.task_id);
  const artifact = state.data.artifacts.find(x => x.task_id === approval.task_id);
  return `<article class="item">
    <div class="item-top">
      <div><h3>${task.goal}</h3><p>${approval.reason}</p></div>
      ${badge(approval.status)}
    </div>
    ${artifact ? `<div class="evidence">${artifact.evidence.map(x =>
      `<div><small>${x.label} · ${x.source}</small><strong>${x.value}${x.label.includes("利润") ? " 万元" : "%"}</strong></div>`
    ).join("")}</div>
    <p style="margin-top:13px"><strong style="color:#102138">AI 初步判断：</strong>
      ${artifact.content.main_driver}，分析置信度 ${(artifact.content.confidence * 100).toFixed(0)}%。
    </p>` : ""}
    ${approval.status === "pending" ? `<div class="buttons">
      <button class="approve" onclick="decide('${approval.id}', true)">确认并发布</button>
      <button class="reject" onclick="decide('${approval.id}', false)">退回补充证据</button>
    </div>` : ""}
  </article>`;
}

function renderAction() {
  const approvals = state.data.approvals;
  const tasks = state.data.tasks;
  return `<div class="layout">
    <section class="panel">
      <div class="panel-head"><h2>需要我处理</h2><span>${approvals.filter(x => x.status === "pending").length} 项待办</span></div>
      ${approvals.length ? approvals.map(approvalItem).join("") : `
        <div class="empty"><div class="empty-icon">✓</div><strong>当前没有待处理事项</strong>
        <p>运行本月监测后，AI 同事会主动发现异常并创建任务。</p></div>`}
    </section>
    <section class="panel">
      <div class="panel-head"><h2>AI 最近行动</h2><span>自动审计</span></div>
      ${tasks.length ? tasks.map(t => `<article class="item">
        <div class="item-top"><div><h3>${t.goal}</h3><p>来源：AI 主动发现 · 唯一主责已分配</p></div>${badge(t.status)}</div>
      </article>`).join("") : `<div class="empty"><p>暂无行动记录</p></div>`}
    </section>
  </div>`;
}

function renderSpace() {
  return state.data.spaces.map(space => {
    const colleague = state.data.colleagues.find(x => x.id === space.owner_id);
    return `<section class="panel">
      <div class="panel-head"><h2>${space.name}</h2>${badge(space.status)}</div>
      <div class="detail-grid">
        <div class="detail-row"><span>长期目标</span><strong>${space.objective}</strong></div>
        <div class="detail-row"><span>主责 AI</span><strong>${colleague.name} · ${colleague.role}</strong></div>
        <div class="detail-row"><span>关注指标</span><div class="capabilities">${space.indicators.map(x => `<span class="chip">${x}</span>`).join("")}</div></div>
        <div class="detail-row"><span>本期状态</span><strong>${state.data.tasks.length ? "发现 1 项重大异常" : "等待数据更新"}</strong></div>
      </div>
    </section>`;
  }).join("");
}

function renderColleague() {
  return state.data.colleagues.map(c => `<div class="layout">
    <section class="panel">
      <div class="panel-head"><h2>${c.name} · ${c.role}</h2>${badge(c.status)}</div>
      <div class="detail-grid">
        <div class="detail-row"><span>责任目标</span><strong>${c.objective}</strong></div>
        <div class="detail-row"><span>自主等级</span><strong>L${c.autonomy_level} · 分层授权</strong></div>
        <div><span style="color:var(--muted);font-size:13px">能力</span><div class="capabilities">${c.capabilities.map(x => `<span class="chip">${x}</span>`).join("")}</div></div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head"><h2>表现评价</h2><span>${state.data.evaluations.length} 次评价</span></div>
      <div class="detail-grid">
        ${state.data.evaluations.length ? state.data.evaluations.map(e =>
          `<div class="detail-row"><span>${e.notes}</span><strong>采纳率 ${(e.metrics.human_acceptance * 100).toFixed(0)}%</strong></div>`
        ).join("") : `<p style="color:var(--muted);font-size:13px">任务闭环后自动形成评价记录。</p>`}
      </div>
    </section>
  </div>`).join("");
}

function renderArtifacts() {
  return `<section class="panel">
    <div class="panel-head"><h2>分析产物</h2><span>可追溯证据</span></div>
    ${state.data.artifacts.length ? state.data.artifacts.map(a => `<article class="item">
      <div class="item-top"><div><h3>${a.title}</h3><p>${a.content.summary} · ${a.content.main_driver}</p></div>${badge(a.status)}</div>
      <div class="capabilities">${a.content.recommendations.map(x => `<span class="chip">${x}</span>`).join("")}</div>
    </article>`).join("") : `<div class="empty"><p>监测运行后将在这里形成结构化分析产物。</p></div>`}
  </section>`;
}

function render() {
  renderMetrics();
  const [title, subtitle] = titles[state.view];
  document.querySelector("#page-title").textContent = title;
  document.querySelector("#page-subtitle").textContent = subtitle;
  const renderers = { action: renderAction, space: renderSpace, colleague: renderColleague, artifacts: renderArtifacts };
  document.querySelector("#content").innerHTML = renderers[state.view]();
}

async function refresh() {
  state.data = await api("/api/dashboard");
  render();
}

async function runDemo() {
  const button = document.querySelector("#run-button");
  button.disabled = true;
  button.textContent = "AI 正在监测…";
  try {
    await api("/api/demo/run", { method: "POST" });
    state.view = "action";
    await refresh();
    toast("发现 1 项重大利润偏差，已创建分析任务");
  } catch (e) { toast(e.message); }
  finally {
    button.disabled = false;
    button.innerHTML = "运行本月监测 <span>→</span>";
  }
}

async function decide(id, approved) {
  await api(`/api/approvals/${id}/decision`, {
    method: "POST", body: JSON.stringify({ approved, decided_by: "经营分析负责人" })
  });
  await refresh();
  toast(approved ? "结论已确认并发布，评价记录已沉淀" : "任务已退回，等待补充业务证据");
}

function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = message; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

document.querySelector("#run-button").addEventListener("click", runDemo);
document.querySelectorAll(".nav-item").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".nav-item").forEach(x => x.classList.remove("active"));
  button.classList.add("active"); state.view = button.dataset.view; render();
}));
refresh().catch(e => document.querySelector("#content").innerHTML = `<div class="loading">${e.message}</div>`);

