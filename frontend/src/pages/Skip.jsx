import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Skip() {
  const [skipped, setSkipped] = useState([])
  const [wins, setWins] = useState([])
  const [wid, setWid] = useState('')
  const [err, setErr] = useState('')
  const load = async () => {
    try {
      const [t, w] = await Promise.all([api.tickets('过号'), api.windows()])
      setSkipped(t)
      setWins(w.filter(x => x.开放))
      if (!wid && w.length) setWid(String(w.find(x => x.开放)?.id || ''))
    } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [])
  const onRecall = async (id) => {
    setErr('')
    try { await api.recall(id, Number(wid)); load() } catch (e) { setErr(e.message) }
  }
  const onVoid = async (id) => {
    setErr('')
    try { await api.voidTicket(id); load() } catch (e) { setErr(e.message) }
  }
  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">回收命运</p>
        <h1>过号重叫</h1>
        <p className="lede">过号可重叫回窗办理，或作废另取。</p>
      </header>
      <section className="panel">
        <div className="form row">
          <label>重叫窗口
            <select value={wid} onChange={e => setWid(e.target.value)}>
              {wins.map(w => <option key={w.id} value={w.id}>{w.名称}</option>)}
            </select>
          </label>
        </div>
        {err && <p className="err">{err}</p>}
        <div className="card-grid" style={{ marginTop: 12 }}>
          {skipped.length === 0 && <p className="muted">暂无过号</p>}
          {skipped.map(t => (
            <div className="slip" key={t.id}>
              <div className="no">{t.号牌}</div>
              <div className="meta">{t.业务种类} · {t.状态}</div>
              <div className="actions">
                <button type="button" onClick={() => onRecall(t.id)}>重叫</button>
                <button type="button" className="danger" onClick={() => onVoid(t.id)}>作废</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
