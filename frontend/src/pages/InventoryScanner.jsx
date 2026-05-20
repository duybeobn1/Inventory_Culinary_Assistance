import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { scanFridge, confirmScan, manualAdd } from '../api'

const UNIT_OPTIONS = ['g', 'kg', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'piece', 'unit']

export default function InventoryScanner() {
  const [inputMode, setInputMode] = useState('scan') // scan | manual
  const [scanStage, setScanStage] = useState('upload') // upload | processing | review
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()
  const navigate = useNavigate()

  // Manual input fields
  const [newName, setNewName] = useState('')
  const [newMass, setNewMass] = useState('')
  const [newUnit, setNewUnit] = useState('g')

  const handleImage = async (file) => {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setScanStage('processing')
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
        setScanStage('review')
      } else {
        setError('Unexpected response from scan')
        setScanStage('upload')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed. Try again.')
      setScanStage('upload')
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
    setItems((prev) => [...prev, { name: '', mass: '', unit: 'g' }])
  }

  const handleConfirm = async () => {
    setLoading(true)
    setError('')
    try {
      const payload = items
        .filter((i) => i.name.trim())
        .map((i) => ({ name: i.name, estimated_mass: parseFloat(i.mass) || 0, unit: i.unit }))
      await confirmScan(payload)
      navigate('/chef')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save inventory')
    } finally {
      setLoading(false)
    }
  }

  // Manual input handlers
  const handleAddManualItem = () => {
    const trimmed = newName.trim()
    if (!trimmed) return
    const mass = parseFloat(newMass) || 0
    setItems((prev) => [...prev, { name: trimmed, mass, unit: newUnit }])
    setNewName('')
    setNewMass('')
    setNewUnit('g')
  }

  const handleSaveManual = async () => {
    const valid = items.filter((i) => i.name.trim())
    if (valid.length === 0) return

    setLoading(true)
    setError('')
    try {
      for (const item of valid) {
        await manualAdd({
          name: item.name,
          estimated_mass: parseFloat(item.mass) || 0,
          unit: item.unit,
        })
      }
      navigate('/chef')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save items')
    } finally {
      setLoading(false)
    }
  }

  const handleModeSwitch = (mode) => {
    setInputMode(mode)
    setError('')
    setItems([])
    setPreview(null)
    setScanStage('upload')
  }

  return (
    <div className="page">
      <h1 className="page-title">📸 Scan Your Fridge</h1>
      <p className="page-subtitle">
        Take a photo or manually add your ingredients
      </p>

      {/* Mode Toggle */}
      <div className="mode-toggle">
        <button
          className={`mode-btn ${inputMode === 'scan' ? 'active' : ''}`}
          onClick={() => handleModeSwitch('scan')}
        >
          📷 Scan Photo
        </button>
        <button
          className={`mode-btn ${inputMode === 'manual' ? 'active' : ''}`}
          onClick={() => handleModeSwitch('manual')}
        >
          ✏️ Manual Input
        </button>
      </div>

      {error && <div className="error-state" style={{ marginTop: 16 }}>{error}</div>}

      {/* Scan Mode */}
      {inputMode === 'scan' && (
        <>
          {(scanStage === 'upload' || scanStage === 'processing') && (
            <div
              className="upload-zone"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileRef.current?.click()}
            >
              {scanStage === 'processing' ? (
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

          {preview && scanStage !== 'upload' && (
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

          {scanStage === 'review' && (
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
                    <input
                      type="number"
                      value={item.mass}
                      onChange={(e) => updateItem(i, 'mass', e.target.value)}
                      className="mass-input"
                      min="0"
                      step="0.1"
                    />
                    <select
                      value={item.unit}
                      onChange={(e) => updateItem(i, 'unit', e.target.value)}
                      className="unit-select"
                    >
                      {UNIT_OPTIONS.map((u) => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
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
                  {loading ? 'Saving...' : '✅ Confirm & Find Recipes'}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Manual Input Mode */}
      {inputMode === 'manual' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>✏️ Add Ingredients Manually</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: 16 }}>
            Type in the ingredients you have in your kitchen
          </p>

          <div className="manual-form">
            <input
              className="manual-input"
              placeholder="Ingredient name (e.g., Chicken breast)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddManualItem()}
            />
            <div className="manual-row">
              <input
                type="number"
                className="manual-input manual-mass"
                placeholder="Qty"
                value={newMass}
                onChange={(e) => setNewMass(e.target.value)}
                min="0"
                step="0.1"
              />
              <select
                className="unit-select"
                value={newUnit}
                onChange={(e) => setNewUnit(e.target.value)}
              >
                {UNIT_OPTIONS.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
              <button className="btn btn-primary" onClick={handleAddManualItem}>
                + Add
              </button>
            </div>
          </div>

          {items.length > 0 && (
            <>
              <div className="ingredient-list">
                {items.map((item, i) => (
                  <div key={i} className="ingredient-item">
                    <span className="manual-item-name">{item.name}</span>
                    <span className="mass">{item.mass} {item.unit}</span>
                    <button className="remove-btn" onClick={() => removeItem(i)}>
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <div className="ingredient-actions">
                <button
                  className="btn btn-primary"
                  onClick={handleSaveManual}
                  disabled={loading}
                  style={{ width: '100%' }}
                >
                  {loading ? 'Saving...' : '✅ Save All to Inventory'}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
