import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { Camera, Play, Pause, Stop, ArrowRight, ArrowLeft, Question } from '@phosphor-icons/react'
import api from '../api'

const WS_BASE = `ws://${window.location.hostname}:8000`

export default function CookSession() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [session, setSession] = useState(null)
  const [steps, setSteps] = useState([])
  const [currentStep, setCurrentStep] = useState(1)
  const [totalSteps, setTotalSteps] = useState(1)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [stepTimer, setStepTimer] = useState(0)
  const [ocrResult, setOcrResult] = useState(null)
  const [ocrLoading, setOcrLoading] = useState(false)
  const [freeformMode, setFreeformMode] = useState(false)
  const [cameraActive, setCameraActive] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [sessionComplete, setSessionComplete] = useState(false)
  const [motionHint, setMotionHint] = useState('')

  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const autoCaptureRef = useRef(null)
  const lastFrameRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('active_cook_session', sessionId)
    api.get(`/cook/session/${sessionId}`)
      .then((res) => {
        const s = res.data.session
        setSession(s)
        setCurrentStep(s.current_step || 1)
        setTotalSteps(s.total_steps || 1)
        setStatus(s.status)
      })
      .catch(() => {
        navigate('/chef')
      })
    return () => {
      const current = localStorage.getItem('active_cook_session')
      if (current === sessionId) localStorage.removeItem('active_cook_session')
    }
  }, [sessionId, navigate])

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/cook/${sessionId}`)
    ws.onopen = () => setWsConnected(true)
    ws.onclose = () => setWsConnected(false)
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data)
        if (msg.type === 'step_update') {
          setCurrentStep(msg.current_step)
          setStepTimer(0)
          if (msg.session_complete) {
            setSessionComplete(true)
            setStatus('completed')
          }
        } else if (msg.type === 'ocr_result') {
          setOcrResult(msg.ocr)
          setOcrLoading(false)
        } else if (msg.type === 'status') {
          setStatus(msg.status)
        }
      } catch {}
    }
    wsRef.current = ws
    return () => {
      ws.close()
    }
  }, [sessionId])

  useEffect(() => {
    if (status === 'in_progress' && !sessionComplete) {
      timerRef.current = setInterval(() => {
        setStepTimer((t) => t + 1)
      }, 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [status, sessionComplete])

  useEffect(() => {
    if (!cameraActive || !videoRef.current) return

    const detectMotion = () => {
      const video = videoRef.current
      if (!video || video.readyState < 2) return

      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data

      if (!lastFrameRef.current) {
        lastFrameRef.current = pixels
        return
      }

      let diff = 0
      for (let i = 0; i < pixels.length; i += 16) {
        diff += Math.abs(pixels[i] - lastFrameRef.current[i])
      }
      lastFrameRef.current = pixels
      const avgDiff = diff / (pixels.length / 16)

      if (avgDiff > 15) {
        setMotionHint(t('cook.motion_detected'))
        captureAndSend()
      } else {
        setMotionHint('')
      }
    }

    autoCaptureRef.current = setInterval(detectMotion, 15000)
    return () => clearInterval(autoCaptureRef.current)
  }, [cameraActive, t])

  const startCamera = useCallback(async () => {
    try {
      setCameraActive(true)
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      const video = videoRef.current
      if (video) {
        video.srcObject = stream
        await video.play()
      }
    } catch {
      setCameraActive(false)
      setError(t('cook.camera_error'))
    }
  }, [t])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setCameraActive(false)
    if (autoCaptureRef.current) {
      clearInterval(autoCaptureRef.current)
    }
  }, [])

  const captureAndSend = useCallback((freeform = false) => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    const b64 = canvas.toDataURL('image/jpeg', 0.8).split(',')[1]

    setOcrLoading(true)
    setOcrResult(null)

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'ocr_snapshot',
        image: b64,
        freeform,
      }))
    } else {
      const endpoint = freeform ? 'ocr-freeform' : 'ocr'
      api.post(`/cook/session/${sessionId}/${endpoint}`, { image: b64 })
        .then((res) => {
          setOcrResult(res.data.ocr)
          setOcrLoading(false)
        })
        .catch(() => setOcrLoading(false))
    }
  }, [sessionId])

  const handleNextStep = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'next_step' }))
    } else {
      api.post(`/cook/session/${sessionId}/step`)
        .then((res) => {
          setCurrentStep(res.data.current_step)
          setStepTimer(0)
          if (res.data.session_complete) {
            setSessionComplete(true)
            setStatus('completed')
          }
        })
    }
  }

  const handlePause = () => {
    const action = status === 'paused' ? 'resume' : 'pause'
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action }))
    } else {
      api.post(`/cook/session/${sessionId}/${action}`)
        .then(() => setStatus(action === 'pause' ? 'paused' : 'in_progress'))
    }
  }

  const handleAbandon = async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'abandon' }))
    } else {
      await api.post(`/cook/session/${sessionId}/abandon`)
    }
    stopCamera()
    localStorage.removeItem('active_cook_session')
    navigate('/chef')
  }

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const currentInstruction = steps.find((s) => s.step_number === currentStep)?.instruction || ''

  if (status === 'loading') {
    return (
      <div className="page">
        <div className="loading-state"><div className="spinner" /><p>{t('cook.loading')}</p></div>
      </div>
    )
  }

  if (sessionComplete) {
    return (
      <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>&#127858;</div>
        <h1>{t('cook.complete_title')}</h1>
        <p style={{ marginBottom: 24 }}>{t('cook.complete_subtitle')}</p>
        <button className="btn btn-primary" onClick={() => navigate('/chef')}>
          {t('cook.back_to_chef')}
        </button>
      </div>
    )
  }

  return (
    <div className="cook-session">
      {/* Camera view */}
      <div className="cook-camera">
        {cameraActive ? (
          <video ref={videoRef} autoPlay playsInline muted className="cook-video" />
        ) : (
          <div className="cook-camera-placeholder">
            <Camera size={48} />
            <p>{t('cook.start_camera_hint')}</p>
            <button className="btn btn-primary" onClick={startCamera}>
              {t('cook.start_camera')}
            </button>
          </div>
        )}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Step overlay */}
        {cameraActive && (
          <div className="cook-overlay">
            <div className="cook-step-badge">
              {t('cook.step')} {currentStep}/{totalSteps}
            </div>
            <div className="cook-instruction">{currentInstruction}</div>
            <div className="cook-timer">{formatTime(stepTimer)}</div>
          </div>
        )}
      </div>

      {/* Controls */}
      {cameraActive && (
        <div className="cook-controls">
          <button className="btn btn-cook" onClick={() => captureAndSend(false)} disabled={ocrLoading}>
            <Camera size={18} /> {ocrLoading ? t('cook.scanning') : t('cook.scan_step')}
          </button>
          <button
            className="btn btn-cook btn-outline"
            onClick={() => { setFreeformMode(true); captureAndSend(true); }}
            disabled={ocrLoading}
            title={t('cook.what_is_this')}
          >
            <Question size={18} />
          </button>
        </div>
      )}

      {/* OCR result */}
      {ocrResult && (
        <motion.div
          className={`cook-ocr-result ${ocrResult.is_correct === false ? 'cook-ocr-warning' : ''}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="cook-ocr-detected">{t('cook.detected')}: {ocrResult.detected}</div>
          {ocrResult.suggestion && <div className="cook-ocr-suggestion">{ocrResult.suggestion}</div>}
          {ocrResult.mode === 'freeform' && <div className="cook-ocr-mode">{t('cook.freeform_mode')}</div>}
        </motion.div>
      )}

      {motionHint && <div className="cook-motion-hint">{motionHint}</div>}

      {error && <div className="error-state">{error}</div>}

      {/* Step progress + actions */}
      <div className="cook-actions">
        <div className="cook-progress-bar">
          <div className="cook-progress-fill" style={{ width: `${(currentStep / totalSteps) * 100}%` }} />
        </div>

        <div className="cook-button-row">
          <button className="btn btn-outline" onClick={handlePause}>
            {status === 'paused' ? <Play size={16} /> : <Pause size={16} />}
            {status === 'paused' ? t('cook.resume') : t('cook.pause')}
          </button>

          <button className="btn btn-primary" onClick={handleNextStep} disabled={status === 'paused'}>
            {t('cook.complete_step')} <ArrowRight size={16} />
          </button>

          <button className="btn btn-outline-danger" onClick={handleAbandon}>
            <Stop size={16} /> {t('cook.stop')}
          </button>
        </div>
      </div>
    </div>
  )
}
