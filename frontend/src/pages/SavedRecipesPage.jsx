import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { useTranslation } from 'react-i18next'
import { getSavedRecipes } from '../api'

export default function SavedRecipesPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const { t } = useTranslation()

  useEffect(() => {
    getSavedRecipes(true)
      .then((res) => setRecipes(res.data.recipes || []))
      .catch((err) => setError(err.response?.data?.detail || t('recipes.failed_load')))
      .finally(() => setLoading(false))
  }, [t])

  if (loading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          <p>{t('recipes.loading')}</p>
        </div>
      </div>
    )
  }

  if (selected) {
    return (
      <div className="page">
        <button className="btn btn-secondary" onClick={() => setSelected(null)} style={{ marginBottom: 16 }}>
          &larr; {t('recipes.back')}
        </button>
        <div className="recipe-card">
          <div className="recipe-header">
            <h2>{selected.recipe_name}</h2>
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
      <h1 className="page-title">{t('recipes.title')}</h1>
      <p className="page-subtitle">
        {t('recipes.count', { count: recipes.length })}
      </p>

      {error && <div className="error-state">{error}</div>}

      {recipes.length === 0 && !error && (
        <div className="empty-state">
          <p>{t('recipes.empty_title')}</p>
          <p>{t('recipes.empty_hint')}</p>
        </div>
      )}

      <div className="recipe-grid">
        {recipes.map((r) => (
          <div key={r.id} className="card recipe-card-clickable" onClick={() => setSelected(r)}>
            <h3 style={{ marginBottom: 8 }}>{r.recipe_name}</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {new Date(r.created_at).toLocaleDateString()}
            </p>
            {r.is_favorite && <span className="favorite-badge">{t('recipes.favorite')}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
