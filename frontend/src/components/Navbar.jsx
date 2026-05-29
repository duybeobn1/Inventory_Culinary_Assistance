import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from '../contexts/ThemeContext'
import { MagnifyingGlass, Clipboard, Receipt, ChefHat, BookmarkSimple, Sun, Moon, SignOut } from '@phosphor-icons/react'

const NAV_LINKS = [
  { to: '/scan', labelKey: 'nav.scan', icon: MagnifyingGlass },
  { to: '/inventory', labelKey: 'nav.stock', icon: Clipboard },
  { to: '/receipt', labelKey: 'nav.receipt', icon: Receipt },
  { to: '/chef', labelKey: 'nav.chef', icon: ChefHat },
  { to: '/recipes', labelKey: 'nav.recipes', icon: BookmarkSimple },
]

export default function Navbar({ user, onLogout }) {
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme } = useTheme()

  return (
    <nav className="navbar">
      <Link to="/scan" className="navbar-brand">
        <ChefHat size={20} weight="fill" />
        Culinary AI
      </Link>
      <div className="navbar-center">
        {user && NAV_LINKS.map(({ to, labelKey, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={`btn ${location.pathname === to ? 'active' : ''}`}
          >
            <Icon size={16} />
            {t(labelKey)}
          </Link>
        ))}
      </div>
      <div className="navbar-right">
        {user && (
          <>
            <div className="navbar-controls">
              <button className="icon-btn" onClick={toggleTheme} title={theme === 'light' ? t('nav.dark_mode') : t('nav.light_mode')}>
                {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
              </button>
              <select
                className="lang-select"
                value={i18n.language}
                onChange={(e) => {
                  i18n.changeLanguage(e.target.value)
                  localStorage.setItem('language', e.target.value)
                }}
              >
                <option value="en">EN</option>
                <option value="fr">FR</option>
                <option value="vi">VI</option>
              </select>
            </div>
            <span className="navbar-user">{user.display_name || user.email}</span>
            <button className="btn btn-outline" onClick={onLogout}>
              <SignOut size={16} />
              {t('nav.logout')}
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
