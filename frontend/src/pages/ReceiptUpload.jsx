import { useState, useRef } from 'react'
import { parseReceipt } from '../api'
import { useNavigate } from 'react-router-dom'

export default function ReceiptUpload() {
  const [stage, setStage] = useState('upload') // upload | processing | review
  const [items, setItems] = useState([])
  const [receipt, setReceipt] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()
  const navigate = useNavigate()

  const handleImage = async (file) => {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setStage('processing')
    setLoading(true)
    setError('')

    try {
      const res = await parseReceipt(file)
      const data = res.data
      setReceipt(data)
      setItems(data.items || [])
      setStage('review')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to parse receipt')
      setStage('upload')
    } finally {
      setLoading(false)
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
      <h1 className="page-title">🧾 Scan Receipt</h1>
      <p className="page-subtitle">
        Upload a receipt photo to auto-add ingredients
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
              <p>Parsing receipt with AI...</p>
            </div>
          ) : (
            <>
              <div className="upload-zone-icon">🧾</div>
              <p>Tap or drag a receipt photo here</p>
              <p style={{ fontSize: '0.85rem', marginTop: 4 }}>
                JPG, PNG accepted
              </p>
              <button
                className="btn btn-primary"
                onClick={(e) => { e.stopPropagation(); fileRef.current?.click() }}
              >
                Choose Photo
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
        <div style={{ marginTop: 16 }}>
          <img
            src={preview}
            alt="Receipt"
            style={{
              width: '100%',
              maxHeight: 300,
              objectFit: 'cover',
              borderRadius: 'var(--radius)',
            }}
          />
        </div>
      )}

      {stage === 'review' && receipt && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 8 }}>🧾 {receipt.vendor || 'Receipt'}</h3>
          {receipt.date && (
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: 12 }}>
              {receipt.date}
            </p>
          )}

          <div className="ingredient-list">
            {items.map((item, i) => (
              <div key={i} className="ingredient-item">
                <span className="manual-item-name">{item.name}</span>
                <span className="mass">
                  {item.qty} {item.unit}
                  {item.price ? ` — $${item.price.toFixed(2)}` : ''}
                </span>
              </div>
            ))}
          </div>

          <div className="ingredient-actions" style={{ marginTop: 16 }}>
            <button className="btn btn-primary" onClick={handleDone} style={{ width: '100%' }}>
              ✅ Done — View Inventory
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
