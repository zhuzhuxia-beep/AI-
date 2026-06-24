import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { getGallery } from '../services/api'

// 数字滚动动画 Hook：从 0 计数到目标值
function useCountUp(target, duration = 2000, start = false) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!start || target <= 0) return
    let startTime = null
    let rafId
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      // easeOutExpo 缓动函数，让数字先快后慢
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setCount(Math.floor(eased * target))
      if (progress < 1) {
        rafId = requestAnimationFrame(animate)
      } else {
        setCount(target)
      }
    }
    rafId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafId)
  }, [target, duration, start])
  return count
}

export default function Home() {
  // 画廊数据状态
  const [gallery, setGallery] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const [galleryLoaded, setGalleryLoaded] = useState(false)

  // 统计区域滚动可见性检测
  const statsRef = useRef(null)
  const galleryRef = useRef(null)
  const [statsVisible, setStatsVisible] = useState(false)

  // 监听统计区域进入视口，触发数字滚动动画
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStatsVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.3 }
    )
    if (statsRef.current) observer.observe(statsRef.current)
    return () => observer.disconnect()
  }, [])

  // 画廊懒加载：滚动到画廊区域时才请求 API
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !galleryLoaded) {
          setGalleryLoaded(true)
          loadGallery()
          observer.disconnect()
        }
      },
      { threshold: 0.1 }
    )
    if (galleryRef.current) observer.observe(galleryRef.current)
    return () => observer.disconnect()
  }, [galleryLoaded])

  const loadGallery = async () => {
    try {
      const data = await getGallery()
      setGallery(data.photos || [])
      setTotal(data.total || 0)
    } catch (e) {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  // 三个统计数字（均基于后端 total 字段）
  const restoredCount = useCountUp(total, 2000, statsVisible)
  const storyCount = useCountUp(total, 2200, statsVisible)
  const videoCount = useCountUp(total, 2400, statsVisible)

  return (
    <div className="flex flex-col">
      {/* ====== HERO ====== */}
      <section className="relative min-h-screen flex items-center justify-center text-center px-6 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(240,160,80,0.08)_0%,transparent_70%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_50%,rgba(240,160,80,0.04)_0%,transparent_50%)]" />

        <div className="relative z-10 max-w-3xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-gradient-to-r from-accent/15 to-accent/5 border border-accent/20 text-accent text-sm font-medium mb-10 tracking-wider">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            TRAE AI 创造力大赛 · 生活娱乐赛道
          </div>

          {/* Title */}
          <h1 className="text-6xl md:text-8xl font-extrabold leading-[1.1] mb-6">
            <span className="gradient-text">AI 老照片</span>
            <br />
            <span className="gradient-text">时光机</span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-muted/90 mb-12 max-w-xl mx-auto leading-relaxed">
            上传一张老照片，AI 帮你修复、上色、生成动态回忆短片
            <br />
            <span className="text-accent/80">——让尘封的记忆重新活过来。</span>
          </p>

          {/* CTA */}
          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              to="/upload"
              className="group relative inline-flex items-center gap-2 px-8 py-4 rounded-2xl bg-gradient-to-r from-accent to-accent2 text-white font-bold text-lg no-underline overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-[0_0_40px_rgba(240,160,80,0.3)]"
            >
              <span className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
              <span className="relative flex items-center gap-2">
                ✨ 开始修复老照片
                <span className="text-xl group-hover:translate-x-1 transition-transform">→</span>
              </span>
            </Link>
            <a
              href="#how"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl border border-border text-text font-medium text-lg no-underline transition-all duration-300 hover:border-accent/50 hover:text-accent hover:bg-accent/5"
            >
              了解更多 ↓
            </a>
          </div>

          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-muted/50 text-xs animate-bounce">
            <span>向下滚动</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 3v10M4 9l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      </section>

      {/* ====== HOW IT WORKS ====== */}
      <section id="how" className="relative px-6 py-32">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-20">
            <p className="text-xs uppercase tracking-[4px] text-accent font-semibold mb-4">How It Works</p>
            <h2 className="text-4xl md:text-5xl font-bold">从老照片到回忆短片</h2>
            <p className="text-muted text-lg mt-4">只需三步，让尘封的记忆重新活过来</p>
          </div>

          {/* Step flow */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            {[
              { num: '01', icon: '📷', title: '上传老照片', desc: '支持 JPG、PNG 格式\nAI 自动识别照片年代' },
              { num: '02', icon: '✨', title: '修复 + 上色', desc: 'AI 自动修复划痕、增强清晰度\n智能上色，让照片焕然一新' },
              { num: '03', icon: '🎬', title: '生成回忆短片', desc: '讲述照片背后的故事\nAI 配音 + 动态短片一键生成' },
            ].map((step, i) => (
              <div key={i} className="relative group">
                {/* Number */}
                <div className="text-7xl font-black text-border/40 absolute -top-6 -right-2 select-none leading-none">
                  {step.num}
                </div>
                {/* Card */}
                <div
                  className="relative z-10 h-full p-8 rounded-2xl border border-border/60 bg-gradient-to-b from-card to-card/80
                            transition-all duration-300 group-hover:border-accent/30 group-hover:-translate-y-1"
                >
                  <div className="text-5xl mb-6">{step.icon}</div>
                  <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                  <p className="text-muted text-sm leading-relaxed whitespace-pre-line">{step.desc}</p>
                </div>
                {/* Connector arrow on desktop */}
                {i < 2 && (
                  <div className="hidden md:flex absolute -right-[1.75rem] top-1/2 -translate-y-1/2 text-2xl text-accent/40 z-20">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M5 12h14M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== FEATURES ====== */}
      <section className="relative px-6 py-32 border-t border-border/40">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-20">
            <p className="text-xs uppercase tracking-[4px] text-accent font-semibold mb-4">Features</p>
            <h2 className="text-4xl md:text-5xl font-bold">四大核心引擎</h2>
            <p className="text-muted text-lg mt-4">从修复到叙事，AI 全程驱动</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: '🔧', title: '修复引擎', desc: '划痕修复 · 噪点去除', desc2: '清晰度增强 · 人脸还原' },
              { icon: '🎨', title: '上色引擎', desc: '智能上色 · 风格迁移', desc2: '年代配色 · 手动微调' },
              { icon: '🎥', title: '动态引擎', desc: 'Ken Burns 效果 · 微动效', desc2: '粒子特效 · 转场动画' },
              { icon: '🎙️', title: '叙事引擎', desc: '用户讲故事 → AI 配音', desc2: '年代音乐 → 短片合成', featured: true },
            ].map((f, i) => (
              <div
                key={i}
                className={`rounded-2xl p-8 border transition-all duration-300 hover:-translate-y-1
                  ${f.featured
                    ? 'border-accent/40 bg-gradient-to-b from-accent/10 to-card/80 hover:border-accent/60 hover:shadow-[0_0_40px_rgba(240,160,80,0.1)]'
                    : 'border-border/60 bg-card hover:border-accent/30'
                  }`}
              >
                <div className="flex items-center gap-3 mb-5">
                  <span className="text-4xl">{f.icon}</span>
                  {f.featured && (
                    <span className="px-2.5 py-0.5 rounded-full bg-accent/15 text-accent text-xs font-semibold border border-accent/20">
                      核心亮点
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-bold mb-3">{f.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{f.desc}</p>
                <p className="text-muted text-sm leading-relaxed">{f.desc2}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== STATS ====== */}
      <section ref={statsRef} className="relative px-6 py-24 border-t border-border/40 overflow-hidden">
        {/* 背景装饰光晕 */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(240,160,80,0.05)_0%,transparent_70%)]" />
        <div className="relative z-10 max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs uppercase tracking-[4px] text-accent font-semibold mb-4">Statistics</p>
            <h2 className="text-3xl md:text-4xl font-bold">数据见证奇迹</h2>
            <p className="text-muted text-lg mt-4">每一组数字背后，都是一段被唤醒的记忆</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 md:gap-12">
            {[
              { value: restoredCount, label: '修复照片数', icon: '🔧', suffix: ' 张' },
              { value: storyCount, label: '生成故事数', icon: '🎙️', suffix: ' 段' },
              { value: videoCount, label: '合成短片数', icon: '🎬', suffix: ' 部' },
            ].map((stat, i) => (
              <div key={i} className="text-center group">
                <div className="text-4xl mb-3 inline-block transition-transform duration-300 group-hover:scale-110">
                  {stat.icon}
                </div>
                <div className="text-5xl md:text-6xl font-extrabold gradient-text mb-3 tabular-nums">
                  {stat.value.toLocaleString()}
                  <span className="text-2xl md:text-3xl text-muted font-medium">{stat.suffix}</span>
                </div>
                <p className="text-muted text-sm tracking-wide">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== GALLERY ====== */}
      <section ref={galleryRef} className="relative px-6 py-24 border-t border-border/40">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs uppercase tracking-[4px] text-accent font-semibold mb-4">Gallery</p>
            <h2 className="text-4xl md:text-5xl font-bold">时光机作品集</h2>
            <p className="text-muted text-lg mt-4">看看 AI 让多少老照片重新活了过来</p>
          </div>

          {/* 未加载状态（用户滚动到此处前不显示 spinner） */}
          {!galleryLoaded && (
            <div className="text-center py-20 px-6">
              <div className="text-5xl mb-6 opacity-40">🖼️</div>
              <p className="text-muted/60 text-sm">向下滚动查看作品集</p>
            </div>
          )}

          {/* 加载中状态 */}
          {galleryLoaded && loading && (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="spinner mb-4" />
              <p className="text-muted text-sm">正在加载作品集...</p>
            </div>
          )}

          {/* 空状态提示 */}
          {galleryLoaded && !loading && !error && gallery.length === 0 && (
            <div className="text-center py-20 px-6">
              <div className="text-6xl mb-6 opacity-50">🖼️</div>
              <h3 className="text-xl font-bold mb-3 text-muted">作品集还在酝酿中</h3>
              <p className="text-muted/70 text-sm mb-8 max-w-md mx-auto leading-relaxed">
                这里将展示 AI 修复的老照片作品。成为第一个让记忆重新活过来的人吧！
              </p>
              <Link
                to="/upload"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-accent to-accent2 text-white font-semibold text-sm no-underline transition-all duration-300 hover:scale-105 hover:shadow-[0_0_30px_rgba(240,160,80,0.3)]"
              >
                ✨ 上传第一张老照片
              </Link>
            </div>
          )}

          {/* 加载失败状态 */}
          {galleryLoaded && !loading && error && gallery.length === 0 && (
            <div className="text-center py-20 px-6">
              <div className="text-5xl mb-4 opacity-50">📡</div>
              <p className="text-muted text-sm mb-6">作品集暂时无法加载，请稍后再试</p>
              <button
                onClick={loadGallery}
                className="btn-secondary"
              >
                重新加载
              </button>
            </div>
          )}

          {/* 画廊网格 */}
          {galleryLoaded && !loading && gallery.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {gallery.map((photo) => (
                <div
                  key={photo.id}
                  className="group relative rounded-2xl overflow-hidden border border-border/60 bg-card cursor-pointer transition-all duration-300 hover:border-accent/40 hover:-translate-y-1 hover:shadow-[0_0_40px_rgba(240,160,80,0.12)]"
                  onClick={() => setSelectedPhoto(photo)}
                >
                  {/* 图片容器：hover 切换修复前后 */}
                  <div className="relative aspect-[4/3] overflow-hidden">
                    {/* 默认显示修复后的照片 */}
                    <img
                      src={photo.restored_url}
                      alt="修复后"
                      loading="lazy"
                      className="absolute inset-0 w-full h-full object-cover transition-opacity duration-500 group-hover:opacity-0"
                    />
                    {/* 悬停显示修复前的照片 */}
                    <img
                      src={photo.original_url}
                      alt="修复前"
                      loading="lazy"
                      className="absolute inset-0 w-full h-full object-cover opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                    />
                    {/* 悬停遮罩提示 */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                      <div className="flex items-center gap-2 text-white text-xs">
                        <span className="px-2 py-1 rounded bg-white/20 backdrop-blur-sm">修复前</span>
                        <span className="text-accent">→</span>
                        <span className="px-2 py-1 rounded bg-accent/30 backdrop-blur-sm">修复后</span>
                      </div>
                    </div>
                    {/* 视频播放标识 */}
                    {photo.video_url && (
                      <div className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center text-white text-sm border border-white/20 transition-all duration-300 group-hover:bg-accent group-hover:scale-110">
                        ▶
                      </div>
                    )}
                  </div>

                  {/* 故事文案 */}
                  {photo.story && (
                    <div className="p-4">
                      <p className="text-muted text-xs leading-relaxed line-clamp-2">
                        {photo.story}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ====== CTA ====== */}
      <section className="relative px-6 py-32 border-t border-border/40 text-center overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(240,160,80,0.06)_0%,transparent_70%)]" />
        <div className="relative z-10 max-w-2xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            准备好让记忆<br />
            <span className="gradient-text">活过来了吗？</span>
          </h2>
          <p className="text-muted text-lg mb-10">
            找一张家里的老照片，试试 AI 时光机的魔力。
          </p>
          <Link
            to="/upload"
            className="group relative inline-flex items-center gap-3 px-10 py-5 rounded-2xl bg-gradient-to-r from-accent to-accent2 text-white font-bold text-xl no-underline overflow-hidden transition-all duration-300 hover:scale-105 hover:shadow-[0_0_50px_rgba(240,160,80,0.3)]"
          >
            <span className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
            <span className="relative flex items-center gap-2">
              ✨ 开始修复
              <span className="text-2xl group-hover:translate-x-1 transition-transform">→</span>
            </span>
          </Link>
        </div>
      </section>

      {/* ====== 视频播放模态框 ====== */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
          onClick={() => setSelectedPhoto(null)}
        >
          <div
            className="relative w-full max-w-3xl rounded-2xl overflow-hidden border border-border/60 bg-card shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 关闭按钮 */}
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center text-white text-lg border border-white/20 transition-all duration-200 hover:bg-accent hover:scale-110"
              aria-label="关闭"
            >
              ✕
            </button>

            {/* 视频播放器 */}
            {selectedPhoto.video_url ? (
              <video
                controls
                autoPlay
                className="w-full max-h-[70vh] bg-black"
                src={selectedPhoto.video_url}
                poster={selectedPhoto.restored_url}
              >
                您的浏览器不支持视频播放
              </video>
            ) : (
              <img
                src={selectedPhoto.restored_url}
                alt="修复后的照片"
                className="w-full max-h-[70vh] object-contain bg-black"
              />
            )}

            {/* 故事文案 */}
            {selectedPhoto.story && (
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-accent text-sm">🎙️</span>
                  <span className="text-xs uppercase tracking-wider text-muted font-semibold">照片背后的故事</span>
                </div>
                <p className="text-text/90 text-sm leading-relaxed">
                  {selectedPhoto.story}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
