import { useState, useEffect } from 'react'
import { getInventory, updateInventoryItem, deleteInventoryItem, manualAdd } from '../api'

function expiryLabel(dateStr) {
  if (!dateStr) return null
  const days = Math.ceil((new Date(dateStr) - new Date()) / 86400000)
  if (days < 0) return { text: `Expired ${Math.abs(days)}d ago`, cls: 'expiry-expired' }
  if (days === 0) return { text: 'Expires today', cls: 'expiry-soon' }
  if (days <= 3) return { text: `${days}d left`, cls: 'expiry-soon' }
  if (days <= 7) return { text: `${days}d left`, cls: 'expiry-week' }
  return { text: dateStr, cls: 'expiry-ok' }
}

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

  useEffect(() => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load inventory'))
      .finally(() => setLoading(false))
  }, [])

  const refetch = () => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load inventory'))
  }

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
      setError(err.response?.data?.detail || 'Failed to update')
    }
  }

  const confirmDelete = async (id) => {
    try {
      await deleteInventoryItem(id)
      setDeleteId(null)
      refetch()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete')
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
      setError(err.response?.data?.detail || 'Failed to add ingredient')
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading inventory...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header-row">
        <h1 className="page-title" style={{ margin: 0 }}>📦 My Inventory</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? '✕ Cancel' : '+ Add'}
        </button>
      </div>
      <p className="page-subtitle">
        {inventory.length} ingredient{inventory.length !== 1 ? 's' : ''} tracked
      </p>

      {error && <div className="error-state" onClick={() => setError('')}>{error}</div>}

      {showAdd && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h4>Add Ingredient</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            <input className="input" placeholder="Name" value={addName} onChange={(e) => setAddName(e.target.value)} />
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="input" type="number" placeholder="Qty" value={addQty} onChange={(e) => setAddQty(e.target.value)} style={{ flex: 1 }} />
              <select className="input" value={addUnit} onChange={(e) => setAddUnit(e.target.value)} style={{ width: 80 }}>
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="L">L</option>
                <option value="pcs">pcs</option>
              </select>
            </div>
            <input className="input" type="date" value={addExpiry} onChange={(e) => setAddExpiry(e.target.value)} placeholder="Expiry date (optional)" />
            <button className="btn btn-primary" onClick={handleAdd}>Add to Inventory</button>
          </div>
        </div>
      )}

      {inventory.length === 0 && !error && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ fontSize: '2rem', marginBottom: 12 }}>📭</p>
          <p style={{ color: 'var(--gray-500)' }}>
            No ingredients in your inventory yet.
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-400)', marginTop: 4 }}>
            Scan your fridge or add ingredients manually
          </p>
        </div>
      )}

      {inventory.length > 0 && (
        <div className="card">
          <div className="ingredient-list">
            {inventory.map((item) => {
              const label = expiryLabel(item.expiry_date)
              return (
                <div key={item.id} className="ingredient-item">
                  {editingId === item.id ? (
                    <>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span className="manual-item-name">{item.name}</span>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                          <input
                            className="input"
                            type="number"
                            value={editQty}
                            onChange={(e) => setEditQty(e.target.value)}
                            style={{ width: 70, padding: '4px 8px' }}
                          />
                          <select className="input" value={editUnit} onChange={(e) => setEditUnit(e.target.value)} style={{ width: 64, padding: '4px 8px' }}>
                            <option value="g">g</option>
                            <option value="kg">kg</option>
                            <option value="ml">ml</option>
                            <option value="L">L</option>
                            <option value="pcs">pcs</option>
                          </select>
                          <input
                            className="input"
                            type="date"
                            value={editExpiry}
                            onChange={(e) => setEditExpiry(e.target.value)}
                            style={{ width: 140, padding: '4px 8px' }}
                          />
                          <button className="btn btn-sm" onClick={() => saveEdit(item.id)}>💾</button>
                          <button className="btn btn-sm" onClick={cancelEdit}>✕</button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span className="manual-item-name">{item.name}</span>
                        <span style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>
                          {item.quantity} {item.unit}
                          {label && <span className={label.cls} style={{ marginLeft: 8 }}>{label.text}</span>}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        <button className="btn btn-sm" onClick={() => startEdit(item)}>✏️</button>
                        {deleteId === item.id ? (
                          <>
                            <button className="btn btn-sm btn-danger" onClick={() => confirmDelete(item.id)}>✓</button>
                            <button className="btn btn-sm" onClick={() => setDeleteId(null)}>✕</button>
                          </>
                        ) : (
                          <button className="btn btn-sm" onClick={() => setDeleteId(item.id)}>🗑️</button>
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
