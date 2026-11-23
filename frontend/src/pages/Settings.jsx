import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Settings() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.营业日().then(setData).catch((e) => setErr(e.message))
  }, [])

  const s = data?.设置 || {}
  const g = data?.日闸 || {}

  return (
    <div>
      <div className="hero">
        <h2>营业日</h2>
        <p>网点营业日与封口状态只读展示（底座首刀）。</p>
      </div>
      {err && <p className="err">{err}</p>}
      <div className="panel">
        <div className="grid">
          <div className="stat"><div className="k">网点名</div><div className="v" style={{ fontSize: '1.2rem' }}>{s.网点名 || '—'}</div></div>
          <div className="stat"><div className="k">营业日</div><div className="v" style={{ fontSize: '1.2rem' }}>{s.营业日 || '—'}</div></div>
          <div className="stat"><div className="k">封口</div><div className="v" style={{ fontSize: '1.2rem' }}>{g.sealed ? '已封口' : '未封口'}</div></div>
        </div>
      </div>
    </div>
  )
}
