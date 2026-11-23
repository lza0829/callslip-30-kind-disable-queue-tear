import { useEffect, useState } from 'react'
import { api } from '../api'

export default function DaySeal() {
  const [info, setInfo] = useState(null)
  const [day, setDay] = useState('')
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')
  const load = () => api.sealInfo().then(d => {
    setInfo(d)
    setDay(d.营业日 || '')
  }).catch(e => setErr(e.message))
  useEffect(() => { load() }, [])
  const run = async (fn, ok) => {
    setErr(''); setMsg('')
    try { await fn(); setMsg(ok); load() } catch (e) { setErr(e.message) }
  }
  if (!info && !err) return <p className="muted">加载日切…</p>
  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">当日写闸</p>
        <h1>日切封口</h1>
        <p className="lede">封口后禁止取号与叫号；须封口后再切营业日。</p>
      </header>
      {info && (
        <section className="panel">
          <div className="stat-grid">
            <div className="stat"><span>营业日</span><strong style={{ fontSize: '1.2rem' }}>{info.营业日}</strong></div>
            <div className="stat"><span>封口</span><strong>{info.已封口 ? '是' : '否'}</strong></div>
            <div className="stat"><span>未结号</span><strong>{info.未结号数}</strong></div>
          </div>
          <p className="muted">{info.备注}{info.封口时刻 ? ` · ${info.封口时刻}` : ''}</p>
          <div className="actions">
            <button type="button" onClick={() => run(() => api.seal(false), '已封口')} disabled={info.已封口}>封口</button>
            <button type="button" className="ghost" onClick={() => run(() => api.seal(true), '已强制封口')} disabled={info.已封口}>强制封口</button>
            <button type="button" className="ghost" onClick={() => run(() => api.unseal(), '已解封')} disabled={!info.已封口}>解封</button>
          </div>
        </section>
      )}
      <section className="panel">
        <h2>切日</h2>
        <div className="form row">
          <label>新营业日
            <input value={day} onChange={e => setDay(e.target.value)} placeholder="年-月-日" />
          </label>
          <button type="button" onClick={() => run(() => api.roll(day || null), '已切日')}>切到新营业日</button>
        </div>
        {err && <p className="err">{err}</p>}
        {msg && <p className="muted">{msg}</p>}
      </section>
    </div>
  )
}
