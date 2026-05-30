import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { getSavedRecipes, updateRecipe } from '../api'

export default function SavedRecipesPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editData, setEditData] = useState('')
  const [saving, setSaving] = useState(false)
  const { t } = useTranslation()

  useEffect(() => {
    getSavedRecipes(true)
      .then((res) => setRecipes(res.data.recipes || []))
      .catch((err) => setError(err.response?.data?.detail || t('recipes.failed_load')))
      .finally(() => setLoading(false))
  }, [t])

  const refresh = () => {
    getSavedRecipes(true)
      .then((res) => setRecipes(res.data.recipes || []))
      .catch((err) => setError(err.response?.data?.detail || t('recipes.failed_load')))
  }

  const startEdit = (recipe) => {
    setEditName(recipe.recipe_name)
    setEditData(recipe.recipe_data?.recipe || '')
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setEditName('')
    setEditData('')
  }

  const handleSave = async () => {
    if (!editName.trim()) return
    setSaving(true)
    setError('')
    try {
      const updated = await updateRecipe(selected.id, {
        recipe_name: editName.trim(),
        recipe_data: { ...selected.recipe_data, recipe: editData },
      })
      setSelected(updated.data.recipe)
      setEditing(false)
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update recipe')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleFavorite = async (recipe) => {
    try {
      await updateRecipe(recipe.id, { is_favorite: !recipe.is_favorite })
      if (selected?.id === recipe.id) {
        setSelected({ ...selected, is_favorite: !recipe.is_favorite })
      }
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update recipe')
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="page-header-row">
          <h1 className="page-title">{t('recipes.title')}</h1>
        </div>
        <div className="skeleton skeleton-heading" style={{ width: '40%' }} />
        <div className="recipe-grid" style={{ marginTop: 16 }}>
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
        </div>
      </div>
    )
  }

  if (selected) {
    return (
      <div className="page">
        <button className="btn btn-secondary" onClick={() => { setSelected(null); setEditing(false) }} style={{ marginBottom: 16 }}>
          &larr; {t('recipes.back')}
        </button>

        {error && <div className="error-state">{error}</div>}

        {editing ? (
          <div className="card">
            <div className="edit-recipe-form">
              <div className="form-group">
                <label htmlFor="edit-name">{t('recipes.recipe_name')}</label>
                <input
                  id="edit-name"
                  className="input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="edit-content">{t('recipes.recipe_content')}</label>
                <textarea
                  id="edit-content"
                  className="input edit-textarea"
                  value={editData}
                  onChange={(e) => setEditData(e.target.value)}
                  rows={16}
                />
              </div>
              <div className="edit-recipe-actions">
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                  {saving ? t('recipes.saving') : t('recipes.save')}
                </button>
                <button className="btn btn-secondary" onClick={cancelEdit}>
                  {t('recipes.cancel')}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <motion.div
            className="recipe-card"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="recipe-header">
              <h2>{selected.recipe_name}</h2>
              <div className="recipe-header-actions">
                <button className="btn btn-sm" onClick={() => startEdit(selected)}>
                  {t('recipes.edit')}
                </button>
                <button
                  className={`btn btn-sm ${selected.is_favorite ? 'btn-fav-active' : ''}`}
                  onClick={() => handleToggleFavorite(selected)}
                  title={selected.is_favorite ? t('recipes.remove_favorite') : t('recipes.add_favorite')}
                >
                  {selected.is_favorite ? '\u2605' : '\u2606'}
                </button>
              </div>
            </div>
            <div className="recipe-body">
              <ReactMarkdown>{editData || selected.recipe_data?.recipe || ''}</ReactMarkdown>
            </div>
          </motion.div>
        )}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header-row">
        <h1 className="page-title">{t('recipes.title')}</h1>
      </div>
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
          <motion.div
            key={r.id}
            className="card recipe-card-clickable saved-recipe-card"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: recipes.indexOf(r) * 0.03 }}
          >
            <div className="saved-recipe-main" onClick={() => setSelected(r)}>
              <h3>{r.recipe_name}</h3>
              <p className="saved-recipe-date">
                {new Date(r.created_at).toLocaleDateString()}
              </p>
              {r.is_favorite && <span className="favorite-badge">{t('recipes.favorite')}</span>}
            </div>
            <div className="saved-recipe-actions">
              <button
                className={`btn btn-sm ${r.is_favorite ? 'btn-fav-active' : ''}`}
                onClick={() => handleToggleFavorite(r)}
                title={r.is_favorite ? t('recipes.remove_favorite') : t('recipes.add_favorite')}
              >
                {r.is_favorite ? '\u2605' : '\u2606'}
              </button>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
