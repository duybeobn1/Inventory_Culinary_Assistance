import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { scanFridge, confirmScan, manualAdd } from '../api'

const UNIT_OPTIONS = ['g', 'kg', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'piece', 'unit']

export default function InventoryScanner() {
  const [inputMode, setInputMode] = useState('scan')
  const [scanStage, setScanStage] = useState('upload')
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [newName, setNewName] = useState('')
  const [newMass, setNewMass] = useState('')
  const [newUnit, setNewUnit] = useState('g')
  const [newExpiry, setNewExpiry] = useState('')

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
            expiry_date: item.expiry_date || '',
          }))
        )
        setScanStage('review')
      } else {
        setError('Unexpected response from scan')
        setScanStage('upload')
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('scan.scan_failed'))
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
        .map((i) => ({
          name: i.name,
          estimated_mass: parseFloat(i.mass) || 0,
          unit: i.unit,
          expiry_date: i.expiry_date || null,
        }))
      await confirmScan(payload)
      navigate('/chef')
    } catch (err) {
      setError(err.response?.data?.detail || t('scan.save_failed'))
    } finally {
      setLoading(false)
    }
  }

  const handleAddManualItem = () => {
    const trimmed = newName.trim()
    if (!trimmed) return
    const mass = parseFloat(newMass) || 0
    setItems((prev) => [...prev, { name: trimmed, mass, unit: newUnit, expiry_date: newExpiry || null }])
    setNewName('')
    setNewMass('')
    setNewUnit('g')
    setNewExpiry('')
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
          expiry_date: item.expiry_date || null,
        })
      }
      navigate('/chef')
    } catch (err) {
      setError(err.response?.data?.detail || t('scan.save_items_failed'))
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
      <h1 className="page-title">{t('scan.title')}</h1>
      <p className="page-subtitle">
        {t('scan.subtitle')}
      </p>

      <div className="mode-toggle">
        <button
          className={`mode-btn ${inputMode === 'scan' ? 'active' : ''}`}
          onClick={() => handleModeSwitch('scan')}
        >
          {t('scan.scan_photo')}
        </button>
        <button
          className={`mode-btn ${inputMode === 'manual' ? 'active' : ''}`}
          onClick={() => handleModeSwitch('manual')}
        >
          {t('scan.manual_input')}
        </button>
      </div>

      {error && <div className="error-state">{error}</div>}

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
                  <p>{t('scan.ai_analyzing')}</p>
                </div>
              ) : (
                <>
                  <p className="upload-zone-hint">{t('scan.drop_hint')}</p>
                  <p className="upload-zone-formats">
                    {t('scan.accepted_formats')}
                  </p>
                  <button
                    className="btn btn-primary"
                    onClick={(e) => { e.stopPropagation(); fileRef.current?.click() }}
                  >
                    {t('scan.choose_photo')}
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
            <div className="preview-wrap">
              <img
                src={preview}
                alt="Fridge"
                className="preview-img"
              />
            </div>
          )}

          {scanStage === 'review' && (
            <motion.div
              className="card review-card"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <h3 className="review-title">
                {t('scan.verify_title', { count: items.length })}
              </h3>
              <p className="review-hint">
                {t('scan.verify_hint')}
              </p>

              <div className="ingredient-list">
                {items.map((item, i) => (
                  <div key={i} className="ingredient-item">
                    <input
                      value={item.name}
                      onChange={(e) => updateItem(i, 'name', e.target.value)}
                      placeholder={t('scan.ingredient_name_placeholder')}
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
                    <input
                      type="date"
                      value={item.expiry_date || ''}
                      onChange={(e) => updateItem(i, 'expiry_date', e.target.value)}
                      className="date-input"
                      title={t('scan.expiry')}
                    />
                    <button className="remove-btn" onClick={() => removeItem(i)}>
                      &times;
                    </button>
                  </div>
                ))}
              </div>

              <div className="ingredient-actions">
                <button className="btn btn-secondary" onClick={addItem}>
                  {t('scan.add_item')}
                </button>
                <button
                  className="btn btn-primary btn-full"
                  onClick={handleConfirm}
                  disabled={loading || items.filter((i) => i.name.trim()).length === 0}
                >
                  {loading ? t('scan.saving') : t('scan.confirm')}
                </button>
              </div>
            </motion.div>
          )}
        </>
      )}

      {inputMode === 'manual' && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <h3 className="manual-title">{t('scan.manual_title')}</h3>
          <p className="manual-subtitle">{t('scan.manual_hint')}</p>

          <div className="manual-form">
            <input
              className="manual-input"
              placeholder={t('scan.name_placeholder')}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddManualItem()}
              autoComplete="off"
            />
            <div className="manual-row">
              <input
                type="number"
                className="manual-input manual-mass"
                placeholder={t('scan.qty_placeholder')}
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
                {t('scan.add')}
              </button>
            </div>
            <input
              type="date"
              className="manual-input"
              placeholder={t('scan.expiry_placeholder')}
              value={newExpiry}
              onChange={(e) => setNewExpiry(e.target.value)}
            />
          </div>

          {items.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25 }}
            >
              <div className="ingredient-list">
                {items.map((item, i) => (
                  <div key={i} className="ingredient-item">
                    <span className="manual-item-name">{item.name}</span>
                    <span className="mass">{item.mass} {item.unit}</span>
                    {item.expiry_date && (
                      <span className="item-expiry">{t('scan.exp')}: {item.expiry_date}</span>
                    )}
                    <button className="remove-btn" onClick={() => removeItem(i)}>
                      &times;
                    </button>
                  </div>
                ))}
              </div>
              <div className="ingredient-actions">
                <button
                  className="btn btn-primary btn-full"
                  onClick={handleSaveManual}
                  disabled={loading}
                >
                  {loading ? t('scan.saving') : t('scan.save_all')}
                </button>
              </div>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  )
}
