import { useEffect, useState } from 'react'
import { api } from '../api'

const surface_panel = true
export default function Kinds() {
  const [kinds, setKinds] = useState([])
  const [events, setEvents] = useState([])
  const [receipt, setReceipt] = useState(null)
  const [err, setErr] = useState('')
  const load = () => Promise.all([api.kinds(), api.kindEvents()])
    .then(([ks, ev]) => { setKinds(ks); setEvents(ev) })
    .catch(e => setErr(e.message))
  useEffect(() => { load() }, [])
  const toggle = async (k) => {
    setErr(''); setReceipt(null)
    try {
      const r = await api.setKindActive(k.id, !k.启用)
      setReceipt(r)
      load()
    } catch (e) { setErr(e.message) }
  }
  return (
    <div className={surface_panel ? "page" : "page"}>
      <header className="hero">
        <p className="eyebrow">号段前缀</p>
        <h1>业务种类</h1>
        <p className="lede">
          口径「禁新发号留存量」：停用即拒新发号、号段游标冻结；存量等候/过号不冻结，仍可被可办窗口叫号办结，等候墙继续展示。
        </p>
      </header>
      {err && <p className="err">{err}</p>}
      {receipt && (
        <p className="receipt">
          启停回执{receipt.事件编号 ? ` · 事件#${receipt.事件编号}` : ''}：{receipt.回执}
        </p>
      )}
      <section className="panel">
        <h2>种类与号段游标</h2>
        <ul className="plain">
          {kinds.map(k => (
            <li key={k.id}>
              <strong>{k.名称}</strong>
              <span className="tag">{k.前缀}</span>
              {k.启用 ? '启用中' : <span className="badge">已停用</span>}
              · 游标 {k.序号} · 存量 等候 {k.等候} · 过号 {k.过号} · 在办 {k.在办}
              <div className="actions">
                <button type="button" className="ghost" onClick={() => toggle(k)}>
                  {k.启用 ? '停用' : '启用'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
      <section className="panel">
        <h2>启停流水（可重放）</h2>
        <ul className="plain">
          {events.length === 0 && <li className="muted">暂无启停事件</li>}
          {events.map(e => (
            <li key={e.id}>
              #{e.id} {e.时刻} · {e.种类} · {e.动作}
              · 快照 等候 {e.等候} · 过号 {e.过号} · 在办 {e.在办} · 游标 {e.游标}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
