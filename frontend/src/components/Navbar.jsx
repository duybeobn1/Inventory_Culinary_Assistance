import { Link, useLocation } from 'react-router-dom'

export default function Navbar({ user, onLogout }) {
  const location = useLocation()

  const linkStyle = (path) => ({
    background: location.pathname === path ? 'var(--green-100)' : '',
  })

  return (
    <nav className="navbar">
      <Link to="/scan" className="navbar-brand">
        <span>🍳</span> Culinary AI
      </Link>
      <div className="navbar-right">
        {user && (
          <>
            <Link to="/scan" className="btn btn-secondary" style={linkStyle('/scan')}>
              📸 Scan
            </Link>
            <Link to="/inventory" className="btn btn-secondary" style={linkStyle('/inventory')}>
              📦 Stock
            </Link>
            <Link to="/receipt" className="btn btn-secondary" style={linkStyle('/receipt')}>
              🧾 Receipt
            </Link>
            <Link to="/chef" className="btn btn-secondary" style={linkStyle('/chef')}>
              🧑‍🍳 Chef
            </Link>
            <Link to="/recipes" className="btn btn-secondary" style={linkStyle('/recipes')}>
              ⭐ Recipes
            </Link>
            <span className="navbar-user">{user.display_name || user.email}</span>
            <button className="btn btn-outline" onClick={onLogout}>
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
