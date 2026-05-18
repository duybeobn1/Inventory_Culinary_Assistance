import { Link, useLocation } from 'react-router-dom'

export default function Navbar({ user, onLogout }) {
  const location = useLocation()

  return (
    <nav className="navbar">
      <Link to="/scan" className="navbar-brand">
        <span>🍳</span> Culinary AI
      </Link>
      <div className="navbar-right">
        {user && (
          <>
            <Link
              to="/scan"
              className="btn btn-secondary"
              style={{
                background: location.pathname === '/scan' ? 'var(--green-100)' : '',
              }}
            >
              📸 Scan
            </Link>
            <Link
              to="/chef"
              className="btn btn-secondary"
              style={{
                background: location.pathname === '/chef' ? 'var(--green-100)' : '',
              }}
            >
              🧑‍🍳 Chef
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
