import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Issue() {
  const [services, setServices] = useState([])
  const [sid, setSid] = useState('')
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')
  const [ticket, setTicket] = useState(null)

  useEffect(() => {
    api.业务种类().then((rows) => {
      setServices(rows)
      if (rows[0]) setSid(String(rows[0].id))
    }).catch((e) => setErr(e.message))
  }, [])

  async function onIssue() {
    try {
      setErr(''); setMsg('')
      const t = await api.取号(Number(sid))
      setTicket(t)
      setMsg(`已取号 ${t.ticket_no}`)
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div>
      <div className="hero">
        <h2>取号</h2>
        <p>按业务种类发放号牌并写入当日等候队列。</p>
      </div>
      <div className="panel">
        <h3>选择业务</h3>
        <div className="actions">
          <select className="select" value={sid} onChange={(e) => setSid(e.target.value)}>
            {services.map((s) => (
              <option key={s.id} value={s.id}>{s.name}（{s.prefix}）</option>
            ))}
          </select>
          <button type="button" onClick={onIssue}>取号</button>
        </div>
        {msg && <p className="okmsg">{msg}</p>}
        {err && <p className="err">{err}</p>}
        {ticket && (
          <div className="ticket-row" style={{ marginTop: 14 }}>
            <div className="ticket-no">{ticket.ticket_no}</div>
            <div className="ticket-meta">{ticket.service_name} · 位次 {ticket.queue_pos}</div>
            <span className="badge">{ticket.status}</span>
          </div>
        )}
      </div>
    </div>
  )
}
