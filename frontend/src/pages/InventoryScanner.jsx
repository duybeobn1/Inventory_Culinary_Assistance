import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { scanFridge, confirmScan } from '../api'

export default function InventoryScanner() {
  const [stage, setStage] = useState('upload') // upload | processing | review
  const [items, setItems] = useState([])
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
      const res = await scanFridge(file)
      const data = res.data

      if (data.status === 'verification_required') {
        setItems(
          data.data.map((item) => ({
            name: item.name,
            mass: item.estimated_mass,
            unit: item.unit,
          }))
        )
        setStage('review')
      } else {
        setError('Unexpected response from scan')
        setStage('upload')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed. Try again.')
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

  const updateItem = (index, field, value) => {
    setItems((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  const removeItem = (index) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const addItem = () => {
    setItems((prev) => [...prev, { name: '', mass: 0, unit: 'g' }])
  }

  const handleConfirm = async () => {
    setLoading(true)
    setError('')
    try {
      const payload = items
        .filter((i) => i.name.trim())
        .map((i) => ({ name: i.name, estimated_mass: i.mass, unit: i.unit }))
      await confirmScan(payload)
      navigate('/chef')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save inventory')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">📸 Scan Your Fridge</h1>
      <p className="page-subtitle">
        Take a photo or upload an image of your fridge contents
      </p>

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
              <p>AI is analyzing your fridge...</p>
            </div>
          ) : (
            <>
              <div className="upload-zone-icon">📷</div>
              <p>Tap or drag an image here</p>
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
            alt="Fridge"
            style={{
              width: '100%',
              maxHeight: 300,
              objectFit: 'cover',
              borderRadius: 'var(--radius)',
            }}
          />
        </div>
      )}

      {error && <div className="error-state" style={{ marginTop: 16 }}>{error}</div>}

      {stage === 'review' && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 12 }}>
            Verify Ingredients ({items.length} detected)
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: 12 }}>
            Edit names, adjust quantities, or remove incorrect items
          </p>

          <div className="ingredient-list">
            {items.map((item, i) => (
              <div key={i} className="ingredient-item">
                <input
                  value={item.name}
                  onChange={(e) => updateItem(i, 'name', e.target.value)}
                  placeholder="Ingredient name"
                />
                <span className="mass">{item.mass} {item.unit}</span>
                <button className="remove-btn" onClick={() => removeItem(i)}>
                  ✕
                </button>
              </div>
            ))}
          </div>

          <div className="ingredient-actions">
            <button className="btn btn-secondary" onClick={addItem}>
              + Add Item
            </button>
            <button
              className="btn btn-primary"
              onClick={handleConfirm}
              disabled={loading || items.filter((i) => i.name.trim()).length === 0}
              style={{ marginLeft: 'auto' }}
            >
              {loading ? 'Saving...' : `✅ Confirm & Find Recipes`}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
