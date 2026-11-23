async function req(path, opts = {}) {
  const r = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  const text = await r.text()
  let data
  try { data = text ? JSON.parse(text) : null } catch { data = { raw: text } }
  if (!r.ok) {
    const detail = data?.detail || data?.raw || r.statusText
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

export const api = {
  health: () => req('/健康'),
  overview: () => req('/总览'),
  kinds: () => req('/业务种类'),
  kindEvents: () => req('/业务种类/流水'),
  setKindActive: (id, 启用) => req(`/业务种类/${id}/启停`, { method: 'POST', body: JSON.stringify({ 启用 }) }),
  windows: () => req('/窗口'),
  setWindowOpen: (id, 开放) => req(`/窗口/${id}/开闭`, { method: 'POST', body: JSON.stringify({ 开放 }) }),
  tickets: (状态) => req(状态 ? `/号牌?状态=${encodeURIComponent(状态)}` : '/号牌'),
  wall: () => req('/等候墙'),
  events: () => req('/叫号流水'),
  take: (种类编号) => req('/取号', { method: 'POST', body: JSON.stringify({ 种类编号 }) }),
  call: (窗口编号, 种类编号) => req('/叫号', { method: 'POST', body: JSON.stringify({ 窗口编号, 种类编号 }) }),
  skip: (id) => req(`/号牌/${id}/过号`, { method: 'POST', body: '{}' }),
  recall: (id, 窗口编号) => req(`/号牌/${id}/重叫`, { method: 'POST', body: JSON.stringify({ 窗口编号 }) }),
  finish: (id) => req(`/号牌/${id}/办结`, { method: 'POST', body: '{}' }),
  voidTicket: (id) => req(`/号牌/${id}/作废`, { method: 'POST', body: '{}' }),
  sealInfo: () => req('/日切'),
  seal: (强制 = false) => req('/日切/封口', { method: 'POST', body: JSON.stringify({ 强制 }) }),
  unseal: () => req('/日切/解封', { method: 'POST', body: '{}' }),
  roll: (营业日) => req('/日切/切日', { method: 'POST', body: JSON.stringify({ 营业日 }) }),
}
