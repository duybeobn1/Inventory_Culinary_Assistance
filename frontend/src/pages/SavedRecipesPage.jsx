import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { getSavedRecipes } from '../api'

export default function SavedRecipesPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    getSavedRecipes(true)
      .then((res) => setRecipes(res.data.recipes || []))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load recipes'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading saved recipes...</p>
        </div>
      </div>
    )
  }

  if (selected) {
    return (
      <div className="page">
        <button className="btn btn-secondary" onClick={() => setSelected(null)} style={{ marginBottom: 16 }}>
          ← Back to Recipes
        </button>
        <div className="recipe-card">
          <div className="recipe-header">
            <h2>🍽️ {selected.recipe_name}</h2>
          </div>
          <div className="recipe-body">
            <ReactMarkdown>{selected.recipe_data?.recipe || ''}</ReactMarkdown>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <h1 className="page-title">⭐ Saved Recipes</h1>
      <p className="page-subtitle">
        {recipes.length} saved recipe{recipes.length !== 1 ? 's' : ''}
      </p>

      {error && <div className="error-state">{error}</div>}

      {recipes.length === 0 && !error && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ fontSize: '2rem', marginBottom: 12 }}>📭</p>
          <p style={{ color: 'var(--gray-500)' }}>No saved recipes yet.</p>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-400)', marginTop: 4 }}>
            Generate a recipe and save it from the Chef page
          </p>
        </div>
      )}

      <div className="recipe-grid">
        {recipes.map((r) => (
          <div key={r.id} className="card recipe-card-clickable" onClick={() => setSelected(r)}>
            <h3 style={{ marginBottom: 8 }}>{r.recipe_name}</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-400)' }}>
              {new Date(r.created_at).toLocaleDateString()}
            </p>
            {r.is_favorite && <span className="favorite-badge">⭐ Favorite</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
