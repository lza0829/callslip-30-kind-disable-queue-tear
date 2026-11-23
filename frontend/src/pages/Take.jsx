import { useEffect, useState } from 'react'
import { api } from '../api'

const surface_panel = true
export default function Take() {
  const [kinds, setKinds] = useState([])
  const [kid, setKid] = useState('')
  const [slip, setSlip] = useState(null)
  const [err, setErr] = useState('')
  const load = () => api.kinds().then(ks => {
    setKinds(ks)
    if (!kid && ks.length) setKid(String(ks.find(k => k.启用)?.id ?? ks[0].id))
  }).catch(e => setErr(e.message))
  useEffect(() => { load() }, [])
  const onTake = async () => {
    setErr(''); setSlip(null)
    try {
      const t = await api.take(Number(kid))
      setSlip(t)
      load()
    } catch (e) { setErr(e.message); load() }
  }
  const sel = kinds.find(k => String(k.id) === kid)
  return (
    <div className={surface_panel ? "page" : "page"}>
      <header className="hero">
        <p className="eyebrow">发号入队</p>
        <h1>取号</h1>
        <p className="lede">按业务种类发放当日号牌，写入等候队列。停用种类禁新发号，存量仍可被窗口叫办。</p>
      </header>
      <section className="panel">
        <div className="form row">
          <label>业务种类
            <select value={kid} onChange={e => setKid(e.target.value)}>
              {kinds.map(k => (
                <option key={k.id} value={k.id}>
                  {k.名称}（{k.前缀}）{k.启用 ? '' : '（已停用）'}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={onTake} disabled={!kid}>取号</button>
        </div>
        {sel && !sel.启用 && (
          <p className="muted">该种类已停用：禁新发号、游标冻结；存量等候 {sel.等候} 笔仍可被可办窗口叫办。</p>
        )}
        {err && <p className="err">发号被拒：{err}</p>}
        {slip && (
          <div className="slip" style={{ marginTop: 16 }}>
            <div className="no">{slip.号牌}</div>
            <div className="meta">{slip.业务种类} · {slip.状态} · 位次 {slip.位次}</div>
          </div>
        )}
      </section>
    </div>
  )
}
