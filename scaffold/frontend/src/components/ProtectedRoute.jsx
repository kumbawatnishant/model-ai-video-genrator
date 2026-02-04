import React, { useContext } from 'react'
import { Navigate } from 'react-router-dom'
import { AuthContext } from '../AuthProvider'

export default function ProtectedRoute({ children }){
  const { user, loading } = useContext(AuthContext)
  if (loading) return <div style={{padding:16}}>Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}
