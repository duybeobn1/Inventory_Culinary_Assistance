import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { getInventory, updateInventoryItem, deleteInventoryItem, manualAdd } from '../api'

function daysUntil(dateStr) {
  if (!dateStr) return null
  return Math.ceil((new Date(dateStr) - new Date()) / 86400000)
}

function expiryLabel(dateStr, t) {
  const days = daysUntil(dateStr)
  if (days === null) return null
  if (days < 0) return { text: t('inventory.expired', { days: Math.abs(days) }), cls: 'expiry-expired' }
  if (days === 0) return { text: t('inventory.expires_today'), cls: 'expiry-soon' }
  if (days <= 3) return { text: t('inventory.days_left', { days }), cls: 'expiry-soon' }
  if (days <= 7) return { text: t('inventory.days_left', { days }), cls: 'expiry-week' }
  return { text: t('inventory.days_left', { days }), cls: 'expiry-ok' }
}

const FILTERS = [
  { key: 'all', labelKey: 'inventory.filter_all' },
  { key: 'expiring', labelKey: 'inventory.filter_expiring' },
  { key: 'expired', labelKey: 'inventory.filter_expired' },
  { key: 'no_date', labelKey: 'inventory.filter_no_date' },
]

export default function InventoryPage() {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editQty, setEditQty] = useState('')
  const [editUnit, setEditUnit] = useState('')
  const [editExpiry, setEditExpiry] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [addName, setAddName] = useState('')
  const [addQty, setAddQty] = useState('')
  const [addUnit, setAddUnit] = useState('g')
  const [addExpiry, setAddExpiry] = useState('')
  const [deleteId, setDeleteId] = useState(null)
  const [activeFilter, setActiveFilter] = useState('all')
  const { t } = useTranslation()

  useEffect(() => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch((err) => setError(err.response?.data?.detail || t('inventory.failed_load')))
      .finally(() => setLoading(false))
  }, [t])

  const refetch = () => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch((err) => setError(err.response?.data?.detail || t('inventory.failed_load')))
  }

  const filtered = useMemo(() => {
    let list = [...inventory]

    if (activeFilter === 'expiring') {
      list = list.filter((i) => {
        const d = daysUntil(i.expiry_date)
        return d !== null && d >= 0 && d <= 7
      })
    } else if (activeFilter === 'expired') {
      list = list.filter((i) => {
        const d = daysUntil(i.expiry_date)
        return d !== null && d < 0
      })
    } else if (activeFilter === 'no_date') {
      list = list.filter((i) => !i.expiry_date)
    }

    list.sort((a, b) => {
      const da = a.expiry_date ? daysUntil(a.expiry_date) ?? 999 : 999
      const db = b.expiry_date ? daysUntil(b.expiry_date) ?? 999 : 999
      return da - db
    })

    return list
  }, [inventory, activeFilter])

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditQty(String(item.quantity))
    setEditUnit(item.unit)
    setEditExpiry(item.expiry_date || '')
  }

  const cancelEdit = () => setEditingId(null)

  const saveEdit = async (id) => {
    try {
      await updateInventoryItem(id, {
        quantity: parseFloat(editQty),
        unit: editUnit,
        expiry_date: editExpiry || null,
      })
      setEditingId(null)
      refetch()
    } catch (err) {
      setError(err.response?.data?.detail || t('inventory.failed_update'))
    }
  }

  const confirmDelete = async (id) => {
    try {
      await deleteInventoryItem(id)
      setDeleteId(null)
      refetch()
    } catch (err) {
      setError(err.response?.data?.detail || t('inventory.failed_delete'))
    }
  }

  const handleAdd = async () => {
    if (!addName.trim() || !addQty) return
    try {
      await manualAdd({
        name: addName.trim(),
        estimated_mass: parseFloat(addQty),
        unit: addUnit,
        expiry_date: addExpiry || null,
      })
      setShowAdd(false)
      setAddName('')
      setAddQty('')
      setAddUnit('g')
      setAddExpiry('')
      refetch()
    } catch (err) {
      setError(err.response?.data?.detail || t('inventory.failed_add'))
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="page-header-row">
          <h1 className="page-title">{t('inventory.title')}</h1>
        </div>
        <div className="skeleton skeleton-heading" style={{ width: '40%' }} />
        <div className="card" style={{ marginTop: 8 }}>
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header-row">
        <h1 className="page-title">{t('inventory.title')}</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? 'X ' + t('inventory.cancel') : '+ ' + t('inventory.add')}
        </button>
      </div>
      <p className="page-subtitle">
        {t('inventory.tracked', { count: inventory.length })}
      </p>

      {error && <div className="error-state" onClick={() => setError('')}>{error}</div>}

      {showAdd && (
        <div className="card add-card">
          <h4>{t('inventory.add_title')}</h4>
          <div className="add-form">
            <input className="input" placeholder={t('inventory.name')} value={addName} onChange={(e) => setAddName(e.target.value)} />
            <div className="add-row">
              <input className="input" type="number" placeholder={t('inventory.qty')} value={addQty} onChange={(e) => setAddQty(e.target.value)} />
              <select className="input input-select" value={addUnit} onChange={(e) => setAddUnit(e.target.value)}>
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="L">L</option>
                <option value="pcs">pcs</option>
              </select>
            </div>
            <input className="input" type="date" value={addExpiry} onChange={(e) => setAddExpiry(e.target.value)} placeholder="Expiry date (optional)" />
            <button className="btn btn-primary btn-full" onClick={handleAdd}>{t('inventory.add_to_inventory')}</button>
          </div>
        </div>
      )}

      {inventory.length > 0 && (
        <div className="inv-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`inv-filter-btn ${activeFilter === f.key ? 'active' : ''}`}
              onClick={() => setActiveFilter(f.key)}
            >
              {t(f.labelKey)}
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 && !error && (
        <div className="empty-state">
          <p>{activeFilter === 'all' ? t('inventory.empty_title') : t('inventory.filter_empty')}</p>
          <p>{activeFilter === 'all' ? t('inventory.empty_hint') : ''}</p>
        </div>
      )}

      {filtered.length > 0 && (
        <div className="card">
          <div className="ingredient-list">
            {filtered.map((item) => {
              const label = expiryLabel(item.expiry_date, t)
              const itemClass = ['ingredient-item']
              if (label) {
                if (label.cls === 'expiry-expired') itemClass.push('item-expired')
                else if (label.cls === 'expiry-soon') itemClass.push('item-urgent')
                else if (label.cls === 'expiry-week') itemClass.push('item-warning')
              }
              return (
                <div key={item.id} className={itemClass.join(' ')}>
                  {editingId === item.id ? (
                    <div className="edit-wrap">
                      <span className="manual-item-name">{item.name}</span>
                      <div className="edit-controls">
                        <input
                          className="input input-sm"
                          type="number"
                          value={editQty}
                          onChange={(e) => setEditQty(e.target.value)}
                        />
                        <select className="input input-sm input-select" value={editUnit} onChange={(e) => setEditUnit(e.target.value)}>
                          <option value="g">g</option>
                          <option value="kg">kg</option>
                          <option value="ml">ml</option>
                          <option value="L">L</option>
                          <option value="pcs">pcs</option>
                        </select>
                        <input
                          className="input input-sm"
                          type="date"
                          value={editExpiry}
                          onChange={(e) => setEditExpiry(e.target.value)}
                        />
                        <button className="btn btn-sm" onClick={() => saveEdit(item.id)} title={t('inventory.save')}>
                          {t('inventory.save')}
                        </button>
                        <button className="btn btn-sm" onClick={cancelEdit} title={t('inventory.cancel')}>
                          X
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="item-info">
                        <span className="manual-item-name">{item.name}</span>
                        <span className="item-meta">
                          {item.quantity} {item.unit}
                          {label && (
                            <span className={`expiry-badge ${label.cls}`}>
                              {label.text}
                              {item.expiry_date && (
                                <span className="expiry-date-raw">{item.expiry_date}</span>
                              )}
                            </span>
                          )}
                          {!label && (
                            <span className="expiry-none">{t('inventory.no_expiry')}</span>
                          )}
                        </span>
                      </div>
                      <div className="item-actions">
                        <button className="btn btn-sm" onClick={() => startEdit(item)} title={t('inventory.edit')}>
                          {t('inventory.edit')}
                        </button>
                        {deleteId === item.id ? (
                          <>
                            <button className="btn btn-sm btn-danger" onClick={() => confirmDelete(item.id)} title={t('inventory.confirm_delete')}>
                              {t('inventory.confirm_delete')}
                            </button>
                            <button className="btn btn-sm" onClick={() => setDeleteId(null)} title={t('inventory.cancel')}>
                              X
                            </button>
                          </>
                        ) : (
                          <button className="btn btn-sm" onClick={() => setDeleteId(item.id)} title={t('inventory.delete')}>
                            {t('inventory.delete')}
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
