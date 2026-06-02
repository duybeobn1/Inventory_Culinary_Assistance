import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { CookingPot, Clock, Play, ChefHat } from '@phosphor-icons/react'
import { getSavedRecipes, createCookSession } from '../api'
import api from '../api'

export default function CookDashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [activeSessions, setActiveSessions] = useState([])
  const [savedRecipes, setSavedRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(null)

  useEffect(() => {
    api.get('/cook/sessions')
      .then((res) => setActiveSessions(res.data.sessions || []))
      .catch(() => {})
    getSavedRecipes()
      .then((res) => setSavedRecipes(res.data.recipes || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleStartCooking = async (recipeId) => {
    setStarting(recipeId)
    try {
      const res = await createCookSession(recipeId)
      const session = res.data.session
      localStorage.setItem('active_cook_session', session.session_id)
      navigate(`/cook/${session.session_id}`)
    } catch {
      setStarting(null)
    }
  }

  const handleResume = (sessionId) => {
    localStorage.setItem('active_cook_session', sessionId)
    navigate(`/cook/${sessionId}`)
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading-state"><div className="spinner" /><p>{t('cook.loading')}</p></div>
      </div>
    )
  }

  return (
    <div className="page">
      <h1 className="page-title">{t('nav.cook')}</h1>
      <p className="page-subtitle">{t('cook.dashboard_subtitle')}</p>

      {activeSessions.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h3 style={{ marginBottom: 12, fontSize: '1rem', color: 'var(--text-secondary)' }}>
            {t('cook.active_sessions')}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {activeSessions.map((s) => (
              <motion.div
                key={s.id}
                className="card"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px' }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{s.recipe_name}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    <Clock size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                    {t('cook.step')} {s.current_step}/{s.total_steps} &middot; {s.status === 'paused' ? t('cook.paused') : t('cook.in_progress')}
                  </div>
                </div>
                <button className="btn btn-primary" onClick={() => handleResume(s.id)}>
                  <Play size={16} /> {t('cook.resume')}
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 style={{ marginBottom: 12, fontSize: '1rem', color: 'var(--text-secondary)' }}>
          {t('chef.saved_recipes')}
        </h3>
        {savedRecipes.length === 0 ? (
          <div className="empty-state">
            <ChefHat size={32} style={{ marginBottom: 12, opacity: 0.3 }} />
            <p>{t('cook.no_recipes')}</p>
            <p>{t('cook.no_recipes_hint')}</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/chef')}>
              <ChefHat size={16} /> {t('cook.go_to_chef')}
            </button>
          </div>
        ) : (
          <div className="recipe-grid">
            {savedRecipes.map((r) => (
              <div key={r.id} className="card saved-recipe-card" style={{ padding: 16 }}>
                <div className="saved-recipe-main" onClick={() => handleStartCooking(r.id)}>
                  <h3 style={{ marginBottom: 4, fontSize: '1rem' }}>{r.recipe_name}</h3>
                  <p className="saved-recipe-date">{new Date(r.created_at).toLocaleDateString()}</p>
                  {r.is_favorite && <span className="favorite-badge">{t('recipes.favorite')}</span>}
                </div>
                <div className="saved-recipe-actions" style={{ marginTop: 12 }}>
                  <button
                    className="btn btn-primary btn-full"
                    onClick={() => handleStartCooking(r.id)}
                    disabled={starting === r.id}
                  >
                    <CookingPot size={14} /> {starting === r.id ? t('chef.starting') : t('chef.start_cooking')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
