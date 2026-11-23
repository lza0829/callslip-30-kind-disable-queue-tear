import { useEffect, useState } from 'react'
import { api } from '../api'

const surface_panel = true
export default function Queue() {
  const [rows, setRows] = useState([])
  const [err, setErr] = useState('')

  async function load() {
    try {
      setErr('')
      setRows(await api.号牌('等候'))
    } catch (e) {
      setErr(e.message)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="hero">
        <h2>等候墙</h2>
        <p>当日仍处等候的号牌，按位次排列。</p>
      </div>
      {err && <p className="err">{err}</p>}
      <div className="panel">
        {rows.map((t) => (
          <div className="ticket-row" key={t.id}>
            <div className="ticket-no">{t.ticket_no}</div>
            <div className="ticket-meta">{t.service_name} · 位次 {t.queue_pos} · {t.created_at}</div>
            <span className="badge">{t.status}</span>
          </div>
        ))}
        {!rows.length && <p style={{ color: 'var(--muted)', margin: 0 }}>暂无等候号</p>}
      </div>
      <button type="button" className="ghost" onClick={load}>刷新</button>
    </div>
  )
}
