import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Services() {
  const [rows, setRows] = useState([])
  const [err, setErr] = useState('')

  useEffect(() => {
    api.业务种类().then(setRows).catch((e) => setErr(e.message))
  }, [])

  return (
    <div>
      <div className="hero">
        <h2>业务种类</h2>
        <p>号段前缀与种类名册，供取号与窗口绑定。</p>
      </div>
      {err && <p className="err">{err}</p>}
      <div className="panel">
        {rows.map((s) => (
          <div className="ticket-row" key={s.id}>
            <div className="ticket-no">{s.prefix}</div>
            <div className="ticket-meta">{s.name} · 排序 {s.sort_no}</div>
            <span className="badge ok">{s.active ? '启用' : '停用'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
