import { useState, useId } from 'react'
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
  const errorId = useId()

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
        <div className="auth-logo">
          <ChefHat size={36} color="var(--accent-600)" weight="fill" />
        </div>
        <h1>{t('auth.title')}</h1>
        <p className="auth-subtitle">{isSignup ? t('auth.signup_subtitle') : t('auth.signin_subtitle')}</p>

        {error && (
          <div className="form-error" role="alert" id={errorId}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} aria-describedby={error ? errorId : undefined}>
          <div className="form-group">
            <label htmlFor="login-email">{t('auth.email')}</label>
            <div className="input-wrap">
              <Envelope size={16} className="input-icon" />
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.email_placeholder')}
                autoComplete="email"
                required
              />
            </div>
          </div>
          {isSignup && (
            <div className="form-group">
              <label htmlFor="login-name">{t('auth.display_name')}</label>
              <div className="input-wrap">
                <User size={16} className="input-icon" />
                <input
                  id="login-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder={t('auth.display_name_placeholder')}
                  autoComplete="name"
                />
              </div>
            </div>
          )}
          <div className="form-group">
            <label htmlFor="login-password">{t('auth.password')}</label>
            <div className="input-wrap">
              <Lock size={16} className="input-icon" />
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.password_placeholder')}
                minLength={6}
                required
                autoComplete={isSignup ? 'new-password' : 'current-password'}
              />
            </div>
          </div>
          <button className="btn btn-primary btn-full" disabled={loading}>
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
