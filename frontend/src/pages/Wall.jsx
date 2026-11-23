import { useEffect, useState } from 'react'
import { api } from '../api'

const surface_panel = true
export default function Wall() {
  const [wall, setWall] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.wall().then(setWall).catch(e => setErr(e.message)) }, [])
  if (err) return <p className="err">{err}</p>
  if (!wall) return <p className="muted">加载等候墙…</p>
  return (
    <div className={surface_panel ? "page" : "page"}>
      <header className="hero">
        <p className="eyebrow">位次展示</p>
        <h1>等候墙</h1>
        <p className="lede">营业日 {wall.营业日}。按种类展示等候与过号位次。</p>
      </header>
      {wall.在办?.length > 0 && (
        <section className="panel">
          <h2>在办</h2>
          <div className="card-grid">
            {wall.在办.map(t => (
              <div className="slip" key={t.id}>
                <div className="no">{t.号牌}</div>
                <div className="meta">{t.窗口} · {t.业务种类} · {t.状态}</div>
              </div>
            ))}
          </div>
        </section>
      )}
      {wall.墙面.map(block => (
        <section className={block.启用 ? 'panel' : 'panel off'} key={block.业务种类}>
          <h2>
            {block.业务种类}
            {!block.启用 && <span className="badge">已停用 · 禁新发号 · 存量可叫办</span>}
            {' '}· 等候 {block.等候数} · 过号 {block.过号数}
          </h2>
          <div className="card-grid">
            {block.队列.length === 0 && <p className="muted">暂无号牌</p>}
            {block.队列.map(t => (
              <div className="slip" key={t.id}>
                <div className="no">{t.号牌}</div>
                <div className="meta">{t.状态} · 位次 {t.位次}</div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
