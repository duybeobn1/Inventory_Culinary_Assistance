import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion } from 'motion/react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { CookingPot } from '@phosphor-icons/react'
import { suggestRecipe, getInventory, saveRecipe, createCookSession, getSavedRecipes } from '../api'

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
  const [savedRecipes, setSavedRecipes] = useState([])
  const [startingCook, setStartingCook] = useState(null)
  const navigate = useNavigate()
  const { t } = useTranslation()

  const loadSavedRecipes = () =>
    getSavedRecipes(true)
      .then((res) => setSavedRecipes(res.data.recipes || []))
      .catch(() => {})

  useEffect(() => { loadSavedRecipes() }, [])

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
      loadSavedRecipes()
    } catch {
      setError(t('chef.failed_save'))
    }
  }

  const recipeText = recipe?.recipe || ''

  const handleStartCooking = async (savedRecipe) => {
    setStartingCook(true)
    try {
      const res = await createCookSession(savedRecipe.id)
      const session = res.data.session
      localStorage.setItem('active_cook_session', session.session_id)
      navigate(`/cook/${session.session_id}`)
    } catch {
      setError(t('chef.failed_start_cook'))
      setStartingCook(false)
    }
  }

  const handleStartCurrentRecipe = async () => {
    if (!recipe) return
    setStartingCook(true)
    try {
      const saveRes = await saveRecipe({
        recipe_name: recipe.recipe?.split('\n')[0]?.replace('## ', '').trim() || 'Current Recipe',
        recipe_data: recipe,
        is_favorite: false,
      })
      const savedId = saveRes.data.recipe?.id || saveRes.data.recipe_id
      if (savedId) {
        const res = await createCookSession(savedId)
        const session = res.data.session
        localStorage.setItem('active_cook_session', session.session_id)
        navigate(`/cook/${session.session_id}`)
      }
    } catch {
      setError(t('chef.failed_start_cook'))
      setStartingCook(false)
    }
  }

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
          className="btn btn-primary btn-full"
          onClick={handleGenerate}
          disabled={loading || !timeMode}
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
          <p className="loading-detail">{t('chef.loading_detail')}</p>
        </div>
      )}

      {recipe && !loading && (
        <motion.div
          className="recipe-card"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="recipe-header">
            <h2>{t('chef.your_recipe')}</h2>
            {recipe.context_used?.length > 0 && (
              <span className="recipe-context">{t('chef.context')}: {recipe.context_used.join('; ')}</span>
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
            <button className="btn btn-secondary" onClick={handleStartCurrentRecipe} disabled={startingCook}>
              <CookingPot size={16} /> {startingCook ? t('chef.starting') : t('chef.start_cooking')}
            </button>
          </div>
        </motion.div>
      )}

      {savedRecipes.length > 0 && (
        <div className="card" style={{ marginTop: 32 }}>
          <h3 style={{ marginBottom: 16 }}>{t('chef.saved_recipes')}</h3>
          <div className="recipe-grid">
            {savedRecipes.map((r) => (
              <div key={r.id} className="card recipe-card-clickable" style={{ padding: 12, cursor: 'pointer' }}
                onClick={() => handleStartCooking(r)}
              >
                <h4 style={{ margin: '0 0 4px' }}>{r.recipe_name}</h4>
                <p style={{ fontSize: 13, opacity: 0.6 }}>
                  {new Date(r.created_at).toLocaleDateString()}
                </p>
                <button className="btn btn-sm btn-primary" style={{ marginTop: 8 }}
                  onClick={(e) => { e.stopPropagation(); handleStartCooking(r) }}
                  disabled={startingCook}
                >
                  <CookingPot size={14} /> {t('chef.start_cooking')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
