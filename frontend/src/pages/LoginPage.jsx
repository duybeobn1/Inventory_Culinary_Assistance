import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { signin, signup } from '../api'
import { useNavigate } from 'react-router-dom'
import { ChefHat, Envelope, Lock, User } from '@phosphor-icons/react'

export default function LoginPage({ onAuth }) {
  const [isSignup, setIsSignup] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { t } = useTranslation()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const fn = isSignup ? signup : signin
      const payload = isSignup
        ? { email, password, display_name: displayName || undefined }
        : { email, password }
      const res = await fn(payload)
      const data = res.data

      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('user_id', data.user_id)
      onAuth(data)
      navigate('/scan')
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || t('auth.error_generic')
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <ChefHat size={36} color="var(--accent-600)" weight="fill" />
        </div>
        <h1>{t('auth.title')}</h1>
        <p>{isSignup ? t('auth.signup_subtitle') : t('auth.signin_subtitle')}</p>

        {error && <div className="form-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>{t('auth.email')}</label>
            <div style={{ position: 'relative' }}>
              <Envelope size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.email_placeholder')}
                required
                style={{ paddingLeft: 34 }}
              />
            </div>
          </div>
          {isSignup && (
            <div className="form-group">
              <label>{t('auth.display_name')}</label>
              <div style={{ position: 'relative' }}>
                <User size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder={t('auth.display_name_placeholder')}
                  style={{ paddingLeft: 34 }}
                />
              </div>
            </div>
          )}
          <div className="form-group">
            <label>{t('auth.password')}</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.password_placeholder')}
                minLength={6}
                required
                style={{ paddingLeft: 34 }}
              />
            </div>
          </div>
          <button className="btn btn-primary" style={{ width: '100%', padding: '12px 20px' }} disabled={loading}>
            {loading ? t('auth.loading') : isSignup ? t('auth.sign_up') : t('auth.sign_in')}
          </button>
        </form>

        <div className="auth-toggle">
          {isSignup ? t('auth.already_account') : t('auth.no_account')}{' '}
          <button onClick={() => { setIsSignup(!isSignup); setError('') }}>
            {isSignup ? t('auth.sign_in') : t('auth.sign_up')}
          </button>
        </div>
      </div>
    </div>
  )
}
