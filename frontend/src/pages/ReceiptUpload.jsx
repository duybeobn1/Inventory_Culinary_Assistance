import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { parseReceipt } from '../api'
import { useNavigate } from 'react-router-dom'

export default function ReceiptUpload() {
  const [stage, setStage] = useState('upload')
  const [items, setItems] = useState([])
  const [receipt, setReceipt] = useState(null)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()
  const { t } = useTranslation()
  const navigate = useNavigate()

  const handleImage = async (file) => {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setStage('processing')
    setError('')

    try {
      const res = await parseReceipt(file)
      const data = res.data
      setReceipt(data)
      setItems(data.items || [])
      setStage('review')
    } catch (err) {
      setError(err.response?.data?.detail || t('receipt.failed_parse'))
      setStage('upload')
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    handleImage(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    handleImage(file)
  }

  const handleDragOver = (e) => e.preventDefault()

  const handleDone = () => {
    navigate('/inventory')
  }

  return (
    <div className="page">
      <h1 className="page-title">{t('receipt.title')}</h1>
      <p className="page-subtitle">
        {t('receipt.subtitle')}
      </p>

      {error && <div className="error-state">{error}</div>}

      {(stage === 'upload' || stage === 'processing') && (
        <div
          className="upload-zone"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileRef.current?.click()}
        >
          {stage === 'processing' ? (
            <div className="loading-state">
              <div className="spinner" />
              <p>{t('receipt.parsing')}</p>
            </div>
          ) : (
            <>
              <p className="upload-zone-hint">{t('receipt.drop_hint')}</p>
              <p className="upload-zone-formats">
                {t('receipt.accepted_formats')}
              </p>
              <button
                className="btn btn-primary"
                onClick={(e) => { e.stopPropagation(); fileRef.current?.click() }}
              >
                {t('receipt.choose_photo')}
              </button>
            </>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={handleFileChange}
          />
        </div>
      )}

      {preview && stage !== 'upload' && (
        <div className="preview-wrap">
          <img
            src={preview}
            alt="Receipt"
            className="preview-img"
          />
        </div>
      )}

      {stage === 'review' && receipt && (
        <motion.div
          className="card review-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <h3>{receipt.vendor || 'Receipt'}</h3>
          {receipt.date && (
            <p className="receipt-date">{receipt.date}</p>
          )}

          <div className="ingredient-list">
            {items.map((item, i) => (
              <div key={i} className="ingredient-item">
                <span className="manual-item-name">{item.name}</span>
                <span className="mass">
                  {item.qty} {item.unit}
                  {item.price ? ` \u2014 $${item.price.toFixed(2)}` : ''}
                </span>
              </div>
            ))}
          </div>

          <div className="ingredient-actions receipt-actions">
            <button className="btn btn-primary btn-full" onClick={handleDone}>
              {t('receipt.done')}
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
