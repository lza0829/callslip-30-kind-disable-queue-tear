import { useEffect, useState } from 'react'
import { api } from '../api'

export default function DayClose() {
  const [ov, setOv] = useState(null)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  async function load() {
    setOv(await api.总览())
  }

  useEffect(() => { load().catch((e) => setErr(e.message)) }, [])

  async function seal(on) {
    try {
      setErr(''); setMsg('')
      const r = on ? await api.封口() : await api.解封()
      setMsg(on ? `已封口 ${r.营业日}` : `已解封 ${r.营业日}`)
      await load()
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div>
      <div className="hero">
        <h2>日切封口</h2>
        <p>封口后禁止取号与叫号写路径。营业日 {ov?.营业日 || '—'}。</p>
      </div>
      <div className="panel">
        <h3>当前：{ov?.已封口 ? '已封口' : '未封口'}</h3>
        <div className="actions">
          <button type="button" onClick={() => seal(true)} disabled={ov?.已封口}>封口</button>
          <button type="button" className="ghost" onClick={() => seal(false)} disabled={!ov?.已封口}>解封</button>
        </div>
        {msg && <p className="okmsg">{msg}</p>}
        {err && <p className="err">{err}</p>}
      </div>
    </div>
  )
}
