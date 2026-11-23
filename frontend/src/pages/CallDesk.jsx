import { useEffect, useState } from 'react'
import { api } from '../api'

export default function CallDesk() {
  const [windows, setWindows] = useState([])
  const [wid, setWid] = useState('')
  const [busy, setBusy] = useState([])
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  async function load() {
    const [w, all] = await Promise.all([api.窗口(), api.号牌()])
    setWindows(w.filter((x) => x.open))
    if (!wid && w.find((x) => x.open)) setWid(String(w.find((x) => x.open).id))
    setBusy(all.filter((t) => ['叫号中', '办理中'].includes(t.status)))
  }

  useEffect(() => { load().catch((e) => setErr(e.message)) }, [])

  async function onCall() {
    try {
      setErr(''); setMsg('')
      const t = await api.叫号(Number(wid))
      setMsg(`已叫 ${t.ticket_no}`)
      await load()
    } catch (e) {
      setErr(e.message)
    }
  }

  async function act(id, fn, ok) {
    try {
      setErr(''); setMsg('')
      await fn(id)
      setMsg(ok)
      await load()
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div>
      <div className="hero">
        <h2>叫号</h2>
        <p>窗口独占叫下一等候号；可开始办理或办结。</p>
      </div>
      <div className="panel">
        <h3>叫下一号</h3>
        <div className="actions">
          <select className="select" value={wid} onChange={(e) => setWid(e.target.value)}>
            {windows.map((w) => (
              <option key={w.id} value={w.id}>{w.code} · {w.title}</option>
            ))}
          </select>
          <button type="button" onClick={onCall}>叫号</button>
        </div>
        {msg && <p className="okmsg">{msg}</p>}
        {err && <p className="err">{err}</p>}
      </div>
      <div className="panel">
        <h3>在办号</h3>
        {busy.map((t) => (
          <div className="ticket-row" key={t.id}>
            <div className="ticket-no">{t.ticket_no}</div>
            <div className="ticket-meta">{t.window_code || '未分窗'} · {t.service_name} · {t.status}</div>
            <div className="actions">
              {t.status === '叫号中' && (
                <button type="button" onClick={() => act(t.id, api.开始办理, '已开始办理')}>开始办理</button>
              )}
              <button type="button" onClick={() => act(t.id, api.办结, '已办结')}>办结</button>
              <button type="button" className="ghost" onClick={() => act(t.id, api.过号, '已过号')}>过号</button>
            </div>
          </div>
        ))}
        {!busy.length && <p style={{ color: 'var(--muted)', margin: 0 }}>暂无在办号</p>}
      </div>
    </div>
  )
}
