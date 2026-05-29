import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { useTranslation } from 'react-i18next'
import { suggestRecipe, getInventory, saveRecipe } from '../api'

const TIME_OPTIONS = [
  {
    id: 'quick',
    labelKey: 'chef.quick_label',
    descKey: 'chef.quick_desc',
  },
  {
    id: 'weekend',
    labelKey: 'chef.weekend_label',
    descKey: 'chef.weekend_desc',
  },
]

export default function RecipeDashboard() {
  const [timeMode, setTimeMode] = useState(null)
  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [inventory, setInventory] = useState([])
  const { t } = useTranslation()

  useEffect(() => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch(() => setInventory([]))
  }, [])

  const hasInventory = inventory.length > 0

  const handleGenerate = async () => {
    if (!timeMode) return
    setLoading(true)
    setError('')
    setRecipe(null)
    setSaved(false)

    const items = hasInventory
      ? inventory.map((i) => ({ name: i.name, expiry_date: i.expiry_date }))
      : [
          { name: 'chicken' }, { name: 'rice' }, { name: 'carrot' },
          { name: 'onion' }, { name: 'garlic' }, { name: 'ginger' },
          { name: 'soy sauce' }, { name: 'egg' }, { name: 'tofu' },
          { name: 'broccoli' },
        ]

    try {
      const res = await suggestRecipe(items, timeMode)
      setRecipe(res.data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        t('chef.failed_generate')
      )
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!recipe) return
    try {
      await saveRecipe({
        recipe_name: recipe.recipe?.split('\n')[0]?.replace('## ', '').trim() || 'Untitled Recipe',
        recipe_data: recipe,
        is_favorite: true,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError(t('chef.failed_save'))
    }
  }

  const recipeText = recipe?.recipe || ''

  return (
    <div className="page">
      <h1 className="page-title">{t('chef.title')}</h1>
      <p className="page-subtitle">
        {hasInventory
          ? t('chef.subtitle_with_inventory', { count: inventory.length })
          : t('chef.subtitle_without_inventory')}
      </p>

      {error && <div className="error-state">{error}</div>}
      {saved && <div className="success-msg">{t('chef.saved_message')}</div>}

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>{t('chef.time_question')}</h3>
        <div className="time-filter">
          {TIME_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              className={`time-btn ${timeMode === opt.id ? 'active' : ''}`}
              onClick={() => setTimeMode(opt.id)}
            >
              <span className="label">{t(opt.labelKey)}</span>
              <span className="desc">{t(opt.descKey)}</span>
            </button>
          ))}
        </div>
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={loading || !timeMode}
          style={{ width: '100%' }}
        >
          {loading
            ? t('chef.consulting')
            : timeMode
              ? t('chef.find_recipe')
              : t('chef.select_time')}
        </button>
      </div>

      {loading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>{t('chef.loading')}</p>
          <p style={{ fontSize: '0.85rem', marginTop: 4, color: 'var(--text-muted)' }}>
            {t('chef.loading_detail')}
          </p>
        </div>
      )}

      {recipe && !loading && (
        <div className="recipe-card">
          <div className="recipe-header">
            <h2>{t('chef.your_recipe')}</h2>
            {recipe.context_used?.length > 0 && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {t('chef.context')}: {recipe.context_used.join('; ')}
              </span>
            )}
          </div>
          <div className="recipe-body">
            <ReactMarkdown>{recipeText}</ReactMarkdown>
          </div>
          <div className="recipe-footer">
            <button className="btn btn-primary" onClick={handleGenerate}>
              {t('chef.regenerate')}
            </button>
            <button className="btn btn-outline" onClick={handleSave}>
              {t('chef.save_favorites')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
