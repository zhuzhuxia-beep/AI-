import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { uploadPhoto, restorePhoto } from '../services/api'

// AI 修复步骤（依次高亮，用 setTimeout 模拟进度）
const RESTORE_STEPS = [
  '🔍 分析照片特征...',
  '降噪处理中...',
  '划痕修复中...',
  '对比度增强...',
  '智能上色中...',
  '最终优化...',
]

// 将后端 / 网络错误转换为友好的中文提示
function getErrorMessage(error, context) {
  if (!error) return '操作失败，请重试'

  // 无响应：网络中断或请求超时
  if (!error.response) {
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
      return context === 'restore'
        ? 'AI 修复超时，处理可能需要更长时间，请稍后重试'
        : '上传超时，请检查网络后重试'
    }
    return '网络连接失败，请检查网络连接后重试'
  }

  const { status, data } = error.response

  // 服务器内部错误
  if (status >= 500) return '服务器暂时不可用，请稍后重试'

  if (context === 'upload') {
    if (status === 400) return data?.detail || '文件格式不支持或文件已损坏，请选择有效的图片'
    if (status === 413) return '文件过大，请选择小于 20MB 的图片'
    if (status === 415) return '文件格式不支持，请选择 JPG、PNG、WebP 或 BMP 格式'
  }

  if (context === 'restore') {
    if (status === 404) return '照片数据未找到，请重新上传照片'
    if (status === 422) return data?.detail || '照片处理参数异常，请重试'
  }

  return data?.detail || error.message || '操作失败，请重试'
}

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [uploadedId, setUploadedId] = useState(null)
  const [restoredUrl, setRestoredUrl] = useState(null)
  const [error, setError] = useState(null)
  const [errorContext, setErrorContext] = useState(null) // 'upload' | 'restore' | null
  const [step, setStep] = useState('upload') // upload | restoring | done
  const [restoreStep, setRestoreStep] = useState(0) // 0..RESTORE_STEPS.length
  const restoreFinishedRef = useRef(false)

  // AI 修复进度模拟：restoring 开始后逐步推进，后端完成后收尾
  useEffect(() => {
    if (!restoring) return
    restoreFinishedRef.current = false
    let current = 0
    const timer = setInterval(() => {
      // 后端已完成则停止模拟
      if (restoreFinishedRef.current) {
        clearInterval(timer)
        return
      }
      current += 1
      // 停在最后一个步骤，等待后端真正完成
      if (current >= RESTORE_STEPS.length - 1) {
        current = RESTORE_STEPS.length - 1
        clearInterval(timer)
      }
      setRestoreStep(current)
    }, 1500)
    return () => clearInterval(timer)
  }, [restoring])

  const onDrop = useCallback((acceptedFiles) => {
    const f = acceptedFiles[0]
    if (f) {
      setFile(f)
      setPreview(URL.createObjectURL(f))
      setError(null)
      setErrorContext(null)
    }
  }, [])

  // 文件被拒绝（格式 / 大小不符）时给出友好提示
  const onDropRejected = useCallback((rejections) => {
    const r = rejections[0]
    if (!r) return
    if (r.errors.some((e) => e.code === 'file-too-large')) {
      setError('文件过大，请选择小于 20MB 的图片')
    } else if (r.errors.some((e) => e.code === 'file-invalid-type')) {
      setError('文件格式不支持，请选择 JPG、PNG、WebP 或 BMP 格式的图片')
    } else {
      setError('文件无法处理，请重新选择')
    }
    setErrorContext(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.bmp'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
  })

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setErrorContext(null)
    try {
      const result = await uploadPhoto(file)
      setUploadedId(result.id)
      setStep('restoring')
      await handleRestore(result.id)
    } catch (e) {
      setError(getErrorMessage(e, 'upload'))
      setErrorContext('upload')
    } finally {
      setUploading(false)
    }
  }

  const handleRestore = async (id) => {
    setRestoring(true)
    setRestoreStep(0)
    setError(null)
    setErrorContext(null)
    try {
      const result = await restorePhoto(id)
      setRestoredUrl(result.restored_url)
      // 后端完成：停止模拟，标记全部步骤完成
      restoreFinishedRef.current = true
      setRestoreStep(RESTORE_STEPS.length)
      // 短暂停留，让用户看到全部完成的绿色状态
      await new Promise((r) => setTimeout(r, 600))
      setStep('done')
    } catch (e) {
      restoreFinishedRef.current = true
      setError(getErrorMessage(e, 'restore'))
      setErrorContext('restore')
    } finally {
      setRestoring(false)
    }
  }

  // 重试：根据出错环节调用对应流程
  const handleRetry = () => {
    const ctx = errorContext
    setError(null)
    setErrorContext(null)
    if (ctx === 'upload' && file) {
      handleUpload()
    } else if (ctx === 'restore' && uploadedId) {
      handleRestore(uploadedId)
    }
  }

  const handleNext = () => {
    if (uploadedId) {
      navigate(`/result/${uploadedId}`)
    }
  }

  const handleReset = () => {
    setFile(null)
    setPreview(null)
    setUploadedId(null)
    setRestoredUrl(null)
    setError(null)
    setErrorContext(null)
    setRestoreStep(0)
    setStep('upload')
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      {/* Step indicator */}
      <div className="flex items-center justify-center gap-3 mb-12">
        {['上传照片', 'AI 修复', '查看结果'].map((label, i) => {
          const stepNum = i + 1
          const currentStep = step === 'upload' ? 1 : step === 'restoring' ? 2 : 3
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

      {/* Error */}
      {error && (
        <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 animate-fade-in">
          <div className="flex items-start gap-3">
            <span className="text-xl flex-shrink-0">⚠️</span>
            <p className="text-red-400 text-sm flex-1 pt-0.5">{error}</p>
          </div>
          {(errorContext || step === 'restoring') && (
            <div className="flex gap-3 mt-3 ml-8 flex-wrap">
              {errorContext && (
                <button
                  onClick={handleRetry}
                  className="btn-primary"
                  style={{ padding: '8px 20px', fontSize: '14px' }}
                >
                  重试
                </button>
              )}
              {step === 'restoring' && (
                <button
                  onClick={handleReset}
                  className="btn-secondary"
                  style={{ padding: '8px 20px', fontSize: '14px' }}
                >
                  重新选择照片
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-center mb-2">上传你的老照片</h2>
          <p className="text-muted text-center mb-8">支持 JPG、PNG、WebP 格式，最大 20MB</p>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
              ${isDragActive ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50 hover:bg-card/50'}
              ${preview ? 'p-4' : ''}`}
          >
            <input {...getInputProps()} />
            {preview ? (
              <img src={preview} alt="预览" className="max-h-80 mx-auto rounded-xl object-contain" />
            ) : (
              <div>
                <p className="text-5xl mb-4">📷</p>
                <p className="text-lg font-medium mb-2">
                  {isDragActive ? '松开以添加照片' : '拖拽照片到此处，或点击选择'}
                </p>
                <p className="text-sm text-muted">JPG · PNG · WebP · 最大 20MB</p>
              </div>
            )}
          </div>

          {preview && (
            <div className="flex gap-4 justify-center mt-8">
              <button onClick={handleReset} className="btn-secondary">重新选择</button>
              <button onClick={handleUpload} disabled={uploading} className="btn-primary">
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <span className="spinner w-4 h-4 border-2" /> 上传中...
                  </span>
                ) : '开始修复 ✨'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Restoring - 多步骤进度反馈 */}
      {step === 'restoring' && !error && (
        <div className="animate-fade-in py-6">
          <h2 className="text-2xl font-bold text-center mb-2">AI 正在修复你的照片</h2>
          <p className="text-muted text-center mb-10">智能修复与上色进行中，请稍候</p>

          <div className="grid md:grid-cols-2 gap-8 items-center">
            {/* 原图半透明预览 + 加载动画 */}
            <div className="relative rounded-2xl overflow-hidden border border-border">
              {preview ? (
                <img src={preview} alt="原图" className="w-full opacity-50" />
              ) : (
                <div className="aspect-[4/3] flex items-center justify-center bg-card">
                  <p className="text-muted text-sm">无预览</p>
                </div>
              )}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="spinner" />
              </div>
              <div className="absolute bottom-3 left-3 bg-black/60 text-white text-xs px-3 py-1 rounded-full pointer-events-none">
                原图
              </div>
            </div>

            {/* 多步骤进度指示器 */}
            <div>
              {/* 总进度条 */}
              <div className="w-full h-1.5 bg-border rounded-full overflow-hidden mb-5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-accent2 transition-all duration-500"
                  style={{ width: `${Math.min(100, (restoreStep / RESTORE_STEPS.length) * 100)}%` }}
                />
              </div>

              {/* 步骤列表 */}
              <div className="space-y-2">
                {RESTORE_STEPS.map((label, i) => {
                  const isDone = i < restoreStep
                  const isCurrent = i === restoreStep
                  return (
                    <div
                      key={i}
                      className={`flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 border
                        ${isCurrent ? 'bg-accent/10 border-accent/40' : isDone ? 'bg-green/5 border-transparent' : 'border-transparent opacity-50'}`}
                    >
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 transition-all
                          ${isDone ? 'bg-green text-white' : isCurrent ? 'bg-accent text-white pulse-glow' : 'bg-card border border-border text-muted'}`}
                      >
                        {isDone ? (
                          '✓'
                        ) : isCurrent ? (
                          <span
                            className="inline-block w-4 h-4 rounded-full animate-spin"
                            style={{ border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff' }}
                          />
                        ) : (
                          i + 1
                        )}
                      </div>
                      <span className={`text-sm transition-all ${isDone ? 'text-muted' : isCurrent ? 'text-text font-medium' : 'text-muted'}`}>
                        {label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Done - Comparison */}
      {step === 'done' && restoredUrl && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-center mb-2">✨ 修复完成！</h2>
          <p className="text-muted text-center mb-8">拖动滑块查看修复前后对比</p>

          <ComparisonSlider before={preview} after={restoredUrl} />

          <div className="flex gap-4 justify-center mt-10">
            <button onClick={handleReset} className="btn-secondary">修复另一张</button>
            <button onClick={handleNext} className="btn-primary">
              下一步：生成回忆短片 🎬
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ComparisonSlider({ before, after }) {
  const [position, setPosition] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [showHint, setShowHint] = useState(true)
  const containerRef = useRef(null)
  const userInteracted = useRef(false)

  // 自动播放：挂载时从左到右自动滑动一次
  useEffect(() => {
    let pos = 0
    const timer = setInterval(() => {
      // 用户交互后立即停止自动播放
      if (userInteracted.current) {
        clearInterval(timer)
        return
      }
      pos += 0.8
      if (pos >= 100) {
        setPosition(100)
        clearInterval(timer)
        // 滑动结束后回到中间位置，方便用户继续拖动
        setTimeout(() => {
          if (!userInteracted.current) setPosition(50)
        }, 500)
      } else {
        setPosition(pos)
      }
    }, 20)
    return () => clearInterval(timer)
  }, [])

  // 全局松手时停止拖拽（避免鼠标移出滑块后仍处于拖拽状态）
  useEffect(() => {
    const stop = () => setDragging(false)
    window.addEventListener('mouseup', stop)
    window.addEventListener('touchend', stop)
    return () => {
      window.removeEventListener('mouseup', stop)
      window.removeEventListener('touchend', stop)
    }
  }, [])

  // 一段时间后隐藏拖动提示
  useEffect(() => {
    const t = setTimeout(() => setShowHint(false), 3500)
    return () => clearTimeout(t)
  }, [])

  const updateFromClientX = useCallback((clientX) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const x = clientX - rect.left
    setPosition(Math.max(0, Math.min(100, (x / rect.width) * 100)))
  }, [])

  const handleMouseDown = (e) => {
    userInteracted.current = true
    setDragging(true)
    setShowHint(false)
    updateFromClientX(e.clientX)
  }

  const handleMouseMove = (e) => {
    if (dragging) updateFromClientX(e.clientX)
  }

  const handleTouchStart = (e) => {
    userInteracted.current = true
    setShowHint(false)
    if (e.touches[0]) updateFromClientX(e.touches[0].clientX)
  }

  const handleTouchMove = (e) => {
    userInteracted.current = true
    if (e.touches[0]) updateFromClientX(e.touches[0].clientX)
  }

  return (
    <div
      ref={containerRef}
      className="comparison-slider mx-auto touch-none"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
    >
      <img src={before} alt="修复前" />
      <img
        src={after}
        alt="修复后"
        className="after"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
      />

      {/* 分隔线 */}
      <div
        className="absolute top-0 bottom-0 pointer-events-none"
        style={{
          left: `${position}%`,
          transform: 'translateX(-50%)',
          width: '3px',
          background:
            'linear-gradient(to bottom, transparent, var(--color-accent) 15%, var(--color-accent) 85%, transparent)',
          boxShadow: '0 0 12px rgba(240,160,80,0.6)',
        }}
      />

      {/* 手柄 */}
      <div
        className="absolute top-1/2 pointer-events-none flex items-center justify-center pulse-glow"
        style={{
          left: `${position}%`,
          transform: 'translate(-50%, -50%)',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #f0a050, #e08030)',
          border: '3px solid rgba(255,255,255,0.95)',
          color: '#fff',
        }}
      >
        <span className="flex items-center" style={{ gap: '1px' }}>
          <span style={{ fontSize: '20px', lineHeight: 1 }}>‹</span>
          <span style={{ fontSize: '20px', lineHeight: 1 }}>›</span>
        </span>
      </div>

      {/* 标签 */}
      <div className="absolute bottom-3 left-3 bg-black/60 text-white text-xs px-3 py-1 rounded-full pointer-events-none">
        修复前
      </div>
      <div className="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-3 py-1 rounded-full pointer-events-none">
        修复后
      </div>

      {/* 拖动提示 */}
      {showHint && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-black/60 text-white text-xs px-3 py-1 rounded-full pointer-events-none animate-fade-in whitespace-nowrap">
          拖动中间滑块对比修复效果
        </div>
      )}
    </div>
  )
}
