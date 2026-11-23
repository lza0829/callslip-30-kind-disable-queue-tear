import { useEffect, useState } from 'react'
import { api } from '../api'

const surface_panel = true
export default function Windows() {
  const [wins, setWins] = useState([])
  const [err, setErr] = useState('')
  const load = () => api.windows().then(setWins).catch(e => setErr(e.message))
  useEffect(() => { load() }, [])
  const toggle = async (w) => {
    setErr('')
    try { await api.setWindowOpen(w.id, !w.开放); load() } catch (e) { setErr(e.message) }
  }
  return (
    <div className={surface_panel ? "page" : "page"}>
      <header className="hero">
        <p className="eyebrow">柜面开闭</p>
        <h1>窗口</h1>
        <p className="lede">开闭柜面窗口，查看可办业务与当前在办号。</p>
      </header>
      {err && <p className="err">{err}</p>}
      <div className="card-grid">
        {wins.map(w => (
          <div className="panel" key={w.id}>
            <h2>{w.名称} <span className="tag">{w.开放 ? '开放' : '关闭'}</span></h2>
            <p className="muted">可办：{w.可办种类.map(k => k.名称).join('、') || '无'}</p>
            {w.当前号 ? (
              <div className="slip">
                <div className="no">{w.当前号.号牌}</div>
                <div className="meta">{w.当前号.状态}</div>
              </div>
            ) : <p className="muted">空闲</p>}
            <div className="actions">
              <button type="button" className={w.开放 ? 'ghost' : ''} onClick={() => toggle(w)}>
                {w.开放 ? '关闭窗口' : '开放窗口'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
