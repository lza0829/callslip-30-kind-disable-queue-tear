import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Take from './pages/Take'
import Wall from './pages/Wall'
import Call from './pages/Call'
import Skip from './pages/Skip'
import Windows from './pages/Windows'
import Kinds from './pages/Kinds'
import DaySeal from './pages/DaySeal'

const links = [
  ['/', '总览'],
  ['/取号', '取号'],
  ['/等候墙', '等候墙'],
  ['/叫号', '叫号'],
  ['/过号', '过号重叫'],
  ['/窗口', '窗口'],
  ['/业务种类', '业务种类'],
  ['/日切', '日切封口'],
]

export default function App() {
  return (
    <div className="shell">
      <aside className="side">
        <div>
          <p className="brand-sub">银行柜面</p>
          <h1 className="brand">叫号条</h1>
        </div>
        <nav className="nav">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'on' : '')}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/取号" element={<Take />} />
          <Route path="/等候墙" element={<Wall />} />
          <Route path="/叫号" element={<Call />} />
          <Route path="/过号" element={<Skip />} />
          <Route path="/窗口" element={<Windows />} />
          <Route path="/业务种类" element={<Kinds />} />
          <Route path="/日切" element={<DaySeal />} />
        </Routes>
      </main>
    </div>
  )
}
