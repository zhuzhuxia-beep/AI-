import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Result from './pages/Result'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg">
        <header className="border-b border-border/50 backdrop-blur-sm sticky top-0 z-50 bg-bg/80">
          <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
            <a href="/" className="flex items-center gap-3 no-underline">
              <span className="text-2xl">📷</span>
              <span className="text-lg font-bold gradient-text">AI 老照片时光机</span>
            </a>
            <nav className="flex gap-6 text-sm text-muted">
              <a href="/" className="hover:text-text transition-colors no-underline">首页</a>
              <a href="/upload" className="hover:text-text transition-colors no-underline">开始修复</a>
            </nav>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/result/:id" element={<Result />} />
          </Routes>
        </main>
        <footer className="border-t border-border/50 py-8 text-center text-sm text-muted">
          <p>TRAE AI 创造力大赛 · 生活娱乐赛道 · 2026</p>
        </footer>
      </div>
    </BrowserRouter>
  )
}

export default App
