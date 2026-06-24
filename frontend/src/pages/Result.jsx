import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getPhotoStatus, generateStory, generateVideo, storyTemplates } from '../services/api'

const VIDEO_STEPS = [
  { icon: '🎵', label: '分析故事情感...' },
  { icon: '🎹', label: '生成背景音乐...' },
  { icon: '🎥', label: 'Ken Burns 动态效果...' },
  { icon: '🎨', label: '色彩调色处理...' },
  { icon: '📝', label: '烧录字幕...' },
  { icon: '🎬', label: '合成最终短片...' },
]

export default function Result() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [photo, setPhoto] = useState(null)
  const [loading, setLoading] = useState(true)
  const [story, setStory] = useState('')
  const [generatingStory, setGeneratingStory] = useState(false)
  const [audioUrl, setAudioUrl] = useState(null)
  const [generatingVideo, setGeneratingVideo] = useState(false)
  const [videoStep, setVideoStep] = useState(0)
  const [videoUrl, setVideoUrl] = useState(null)
  const [error, setError] = useState(null)
  const [step, setStep] = useState('story') // story | video | done
  const audioRef = useRef(null)
  const videoStepTimer = useRef(null)

  useEffect(() => {
    loadPhoto()
    return () => { if (videoStepTimer.current) clearInterval(videoStepTimer.current) }
  }, [id])

  const loadPhoto = async () => {
    try {
      const data = await getPhotoStatus(id)
      setPhoto(data)
    } catch (e) {
      setError('加载照片信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateStory = async () => {
    if (!story.trim()) return
    setGeneratingStory(true)
    setError(null)
    try {
      const result = await generateStory(id, story)
      setAudioUrl(result.audio_url)
      setStep('video')
    } catch (e) {
      setError(e.message || '配音生成失败，请重试')
    } finally {
      setGeneratingStory(false)
    }
  }

  const handleGenerateVideo = async () => {
    setGeneratingVideo(true)
    setError(null)
    setVideoStep(0)

    // Simulate step progression while backend processes
    let stepIdx = 0
    videoStepTimer.current = setInterval(() => {
      stepIdx = Math.min(stepIdx + 1, VIDEO_STEPS.length - 1)
      setVideoStep(stepIdx)
    }, 2000)

    try {
      const result = await generateVideo(id)
      // Stop timer and show all steps complete
      if (videoStepTimer.current) clearInterval(videoStepTimer.current)
      setVideoStep(VIDEO_STEPS.length)
      setTimeout(() => {
        setVideoUrl(result.video_url)
        setStep('done')
        setGeneratingVideo(false)
      }, 600)
    } catch (e) {
      if (videoStepTimer.current) clearInterval(videoStepTimer.current)
      setError(e.message || '视频生成失败，请重试')
      setGeneratingVideo(false)
    }
  }

  const applyTemplate = (text) => {
    setStory(text)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="spinner" />
      </div>
    )
  }

  if (!photo) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <p className="text-5xl mb-4">😕</p>
        <h2 className="text-xl font-bold mb-2">照片未找到</h2>
        <p className="text-muted mb-6">该照片可能已被删除或链接无效</p>
        <button onClick={() => navigate('/upload')} className="btn-primary">重新上传</button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      {/* Step indicator */}
      <div className="flex items-center justify-center gap-3 mb-12">
        {['讲述故事', '生成短片', '完成'].map((label, i) => {
          const stepNum = i + 1
          const currentStep = step === 'story' ? 1 : step === 'video' ? 2 : 3
          const isActive = stepNum === currentStep
          const isDone = stepNum < currentStep
          return (
            <div key={i} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all
                ${isDone ? 'bg-green text-white' : isActive ? 'bg-accent text-white pulse-glow' : 'bg-card border border-border text-muted'}`}>
                {isDone ? '✓' : stepNum}
              </div>
              <span className={`text-sm ${isActive ? 'text-text font-medium' : 'text-muted'}`}>{label}</span>
              {i < 2 && <div className={`w-8 h-0.5 ${stepNum > i + 1 ? 'bg-green' : 'bg-border'}`} />}
            </div>
          )
        })}
      </div>

      {error && (
        <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between gap-4">
          <span>⚠️ {error}</span>
          <button
            onClick={() => { setError(null); step === 'story' ? handleGenerateStory() : handleGenerateVideo() }}
            className="text-red-400 underline hover:text-red-300 whitespace-nowrap"
          >
            重试
          </button>
        </div>
      )}

      {/* Restored photo preview */}
      <div className="mb-10">
        <h2 className="text-xl font-bold text-center mb-4">修复后的照片</h2>
        <img
          src={photo.restored_url}
          alt="修复后"
          className="max-h-80 mx-auto rounded-2xl shadow-lg"
        />
      </div>

      {/* Step 1: Story */}
      {step === 'story' && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-center mb-2">这张照片有什么故事？</h2>
          <p className="text-muted text-center mb-8">
            告诉我们照片背后的故事，AI 会把它变成一段深情的配音旁白
          </p>

          {/* Story templates */}
          <div className="mb-4">
            <p className="text-sm text-muted mb-2">💡 没有灵感？试试这些模板：</p>
            <div className="flex gap-2 flex-wrap">
              {storyTemplates.map((tpl, i) => (
                <button
                  key={i}
                  onClick={() => applyTemplate(tpl.text)}
                  className="px-3 py-1.5 rounded-lg bg-card border border-border text-sm text-muted hover:border-accent/40 hover:text-accent transition-all"
                >
                  {tpl.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="relative">
              <textarea
                value={story}
                onChange={(e) => setStory(e.target.value)}
                placeholder="比如：这是我奶奶18岁时的照片，那年她刚考上师范学校。她总说那是她人生中最快乐的一年，每天天不亮就起床读书，晚上在煤油灯下备课..."
                rows={5}
              />
              <span className="absolute bottom-3 right-3 text-xs text-muted/60">
                {story.length} 字
              </span>
            </div>
            <div className="flex gap-4 justify-end">
              <button onClick={() => navigate('/upload')} className="btn-secondary">返回</button>
              <button
                onClick={handleGenerateStory}
                disabled={!story.trim() || generatingStory}
                className="btn-primary"
              >
                {generatingStory ? (
                  <span className="flex items-center gap-2">
                    <span className="spinner w-4 h-4 border-2" /> 生成配音中...
                  </span>
                ) : '生成配音 🎙️'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Preview audio + generate video */}
      {step === 'video' && audioUrl && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-center mb-2">配音已生成</h2>
          <p className="text-muted text-center mb-8">听听 AI 为你讲述的故事，然后生成动态回忆短片</p>

          <div className="card mb-8">
            <h4 className="font-semibold mb-4">🎙️ AI 配音预览</h4>
            <audio ref={audioRef} controls className="w-full" src={audioUrl}>
              您的浏览器不支持音频播放
            </audio>
            <p className="text-sm text-muted mt-4 italic">"{story}"</p>
          </div>

          {/* Video generation progress */}
          {generatingVideo && (
            <div className="card mb-8 animate-fade-in">
              <h4 className="font-semibold mb-6 text-center">🎬 正在生成回忆短片...</h4>
              {/* Progress bar */}
              <div className="w-full h-2 rounded-full bg-border overflow-hidden mb-6">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-accent2 transition-all duration-500"
                  style={{ width: `${((videoStep + 1) / VIDEO_STEPS.length) * 100}%` }}
                />
              </div>
              {/* Steps */}
              <div className="space-y-3">
                {VIDEO_STEPS.map((s, i) => {
                  const isDone = i < videoStep
                  const isActive = i === videoStep
                  const isPending = i > videoStep
                  return (
                    <div key={i} className={`flex items-center gap-3 transition-all ${isPending ? 'opacity-40' : ''}`}>
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
                        ${isDone ? 'bg-green text-white' : isActive ? 'bg-accent text-white pulse-glow' : 'bg-card border border-border'}`}>
                        {isDone ? '✓' : isActive ? <span className="spinner w-3 h-3 border-2" /> : i + 1}
                      </div>
                      <span className={`text-sm ${isActive ? 'text-text font-medium' : isDone ? 'text-green' : 'text-muted'}`}>
                        {s.icon} {s.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {!generatingVideo && (
            <div className="flex gap-4 justify-center">
              <button onClick={() => { setStep('story'); setAudioUrl(null) }} className="btn-secondary">
                重新编辑故事
              </button>
              <button
                onClick={handleGenerateVideo}
                className="btn-primary"
              >
                生成回忆短片 🎬
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 3: Done - Video */}
      {step === 'done' && videoUrl && (
        <div className="animate-fade-in text-center">
          <h2 className="text-2xl font-bold mb-2">🎉 回忆短片已生成！</h2>
          <p className="text-muted mb-8">你的老照片现在有了声音和生命</p>

          <div className="card mb-8">
            <video
              controls
              className="w-full rounded-xl"
              src={videoUrl}
              poster={photo.restored_url}
            >
              您的浏览器不支持视频播放
            </video>
          </div>

          <div className="flex gap-4 justify-center flex-wrap">
            <a
              href={videoUrl}
              download="回忆短片.mp4"
              className="btn-secondary no-underline inline-block"
            >
              下载短片 💾
            </a>
            <button
              onClick={() => {
                if (navigator.share) {
                  navigator.share({ title: 'AI 老照片时光机', text: '看看我用 AI 修复的老照片！', url: window.location.href })
                } else {
                  navigator.clipboard?.writeText(window.location.href)
                }
              }}
              className="btn-primary"
            >
              分享给朋友 📤
            </button>
          </div>

          <div className="mt-12 pt-8 border-t border-border/50">
            <button onClick={() => navigate('/upload')} className="btn-secondary">
              修复另一张照片 📷
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
