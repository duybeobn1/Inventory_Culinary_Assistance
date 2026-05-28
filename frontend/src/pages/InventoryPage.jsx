import { useState, useEffect } from 'react'
import { getInventory } from '../api'

export default function InventoryPage() {
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load inventory'))
      .finally(() => setLoading(false))
  }, [])

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
      <h1 className="page-title">📦 My Inventory</h1>
      <p className="page-subtitle">
        {inventory.length} ingredient{inventory.length !== 1 ? 's' : ''} tracked
      </p>

      {error && <div className="error-state">{error}</div>}

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
            {inventory.map((item) => (
              <div key={item.id} className="ingredient-item">
                <span className="manual-item-name">{item.name}</span>
                <span className="mass">
                  {item.quantity} {item.unit}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
