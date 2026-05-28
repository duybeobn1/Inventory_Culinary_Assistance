import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { suggestRecipe, getInventory, saveRecipe } from '../api'

const TIME_OPTIONS = [
  {
    id: 'quick',
    emoji: '⚡',
    label: 'Quick & Pragmatic',
    desc: 'Under 30 mins',
  },
  {
    id: 'weekend',
    emoji: '🧘',
    label: 'Weekend Mode',
    desc: 'Over 60 mins',
  },
]

export default function RecipeDashboard() {
  const [timeMode, setTimeMode] = useState(null)
  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [inventory, setInventory] = useState([])
  useEffect(() => {
    getInventory()
      .then((res) => setInventory(res.data.inventory || []))
      .catch(() => setInventory([]))
  }, [])

  const inventoryNames = inventory.map((i) => i.name)
  const hasInventory = inventory.length > 0

  const handleGenerate = async () => {
    if (!timeMode) return
    setLoading(true)
    setError('')
    setRecipe(null)
    setSaved(false)

    const items = hasInventory ? inventoryNames : [
      'chicken', 'rice', 'carrot', 'onion', 'garlic',
      'ginger', 'soy sauce', 'egg', 'tofu', 'broccoli',
    ]

    try {
      const res = await suggestRecipe(items, timeMode)
      setRecipe(res.data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Failed to generate recipe. Is the AI Chef service running?'
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
      setError('Failed to save recipe')
    }
  }

  const recipeText = recipe?.recipe || ''

  return (
    <div className="page">
      <h1 className="page-title">🧑‍🍳 AI Chef</h1>
      <p className="page-subtitle">
        {hasInventory
          ? `Using your ${inventory.length} tracked ingredients`
          : 'Select your cooking mode and let the AI find the perfect recipe'}
      </p>

      {error && <div className="error-state">{error}</div>}
      {saved && <div className="success-msg">⭐ Recipe saved to favorites!</div>}

      {/* Time Filter */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>⏱️ How much time do you have?</h3>
        <div className="time-filter">
          {TIME_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              className={`time-btn ${timeMode === opt.id ? 'active' : ''}`}
              onClick={() => setTimeMode(opt.id)}
            >
              <span className="emoji">{opt.emoji}</span>
              <span className="label">{opt.label}</span>
              <span className="desc">{opt.desc}</span>
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
            ? 'Consulting culinary graph...'
            : timeMode
              ? '🔍 Find Recipe'
              : 'Select a time mode above'}
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <div className="spinner" />
          <p>Consulting culinary science...</p>
          <p style={{ fontSize: '0.85rem', marginTop: 4, color: 'var(--gray-400)' }}>
            Querying Neo4j graph & generating recipe
          </p>
        </div>
      )}

      {/* Recipe Display */}
      {recipe && !loading && (
        <div className="recipe-card">
          <div className="recipe-header">
            <h2>🍽️ Your Recipe</h2>
            {recipe.context_used?.length > 0 && (
              <span style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                Context: {recipe.context_used.join('; ')}
              </span>
            )}
          </div>
          <div className="recipe-body">
            <ReactMarkdown>{recipeText}</ReactMarkdown>
          </div>
          <div className="recipe-footer">
            <button className="btn btn-primary" onClick={handleGenerate}>
              🔄 Regenerate
            </button>
            <button className="btn btn-outline" onClick={handleSave}>
              ⭐ Save to Favorites
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
