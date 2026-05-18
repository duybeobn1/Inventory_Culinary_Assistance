import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import LoginPage from './pages/LoginPage'
import InventoryScanner from './pages/InventoryScanner'
import RecipeDashboard from './pages/RecipeDashboard'
import api from './api'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.get('/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => localStorage.removeItem('access_token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading Culinary AI...</p>
      </div>
    )
  }

  return (
    <div className="app">
      {user && <Navbar user={user} onLogout={() => { setUser(null); localStorage.clear() }} />}
      <main className="main-content">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/scan" /> : <LoginPage onAuth={setUser} />} />
          <Route path="/scan" element={user ? <InventoryScanner /> : <Navigate to="/login" />} />
          <Route path="/chef" element={user ? <RecipeDashboard /> : <Navigate to="/login" />} />
          <Route path="*" element={<Navigate to={user ? '/scan' : '/login'} />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
