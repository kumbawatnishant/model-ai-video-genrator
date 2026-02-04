import React from 'react'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import SubmitJob from './pages/SubmitJob'
import Keys from './pages/Keys'
import Billing from './pages/Billing'
import Login from './pages/Login'
import { isAuthenticated, getEmail, logout } from './auth'
import AuthProvider, { AuthContext } from './AuthProvider'
import ProtectedRoute from './components/ProtectedRoute'
import { useContext } from 'react'

function Nav(){
  const navigate = useNavigate()
  const { user, loading } = useContext(AuthContext)
  return (
    <nav style={{padding:12}}>
      <Link to="/">Dashboard</Link> | <Link to="/submit">Submit Job</Link> | <Link to="/keys">API Keys</Link> | <Link to="/billing">Billing</Link>
      {loading ? null : user ? (
        <span style={{marginLeft:12}}>
          {user.email} <button onClick={()=>{ fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).then(()=>navigate('/login')) }}>Logout</button>
        </span>
      ) : (
        <span style={{marginLeft:12}}><Link to='/login'>Login</Link></span>
      )}
    </nav>
  )
}

export default function App(){
  return (
    <AuthProvider>
      <BrowserRouter>
        <Nav />
        <Routes>
          <Route path='/' element={<Dashboard/>} />
          <Route path='/submit' element={<ProtectedRoute><SubmitJob/></ProtectedRoute>} />
          <Route path='/keys' element={<ProtectedRoute><Keys/></ProtectedRoute>} />
          <Route path='/billing' element={<ProtectedRoute><Billing/></ProtectedRoute>} />
          <Route path='/login' element={<Login/>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
