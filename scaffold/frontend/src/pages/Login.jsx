import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { saveEmail, isAuthenticated } from '../auth'
import { useNavigate } from 'react-router-dom'

export default function Login(){
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('login')
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('') // 'ok' | 'error'
  const navigate = useNavigate()

  useEffect(()=>{
    if (isAuthenticated()) navigate('/')
  },[navigate])

  async function submit(e){
    e.preventDefault()
    setMessage('')
    setStatus('')
    try{
      const path = mode === 'login' ? '/api/auth/login' : '/api/auth/signup'
      const res = await axios.post(path, { email, password })
      const token = res.data.token
      if (res.status === 200) {
        // backend sets httpOnly cookies; call /api/auth/me to confirm
        saveEmail(email)
        setMessage('Authenticated — redirecting...')
        setStatus('ok')
        setTimeout(()=> navigate('/'), 600)
      } else {
        setMessage('Auth failed')
        setStatus('error')
      }
    }catch(e){
      console.error(e)
      const err = e?.response?.data?.error || e.message || 'Auth failed'
      setMessage(String(err))
      setStatus('error')
    }
  }

  return (
    <div style={{padding:16}}>
      <h2>{mode === 'login' ? 'Login' : 'Sign up'}</h2>
      <form onSubmit={submit}>
        <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
        <input placeholder="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        <br />
        <button type="submit">{mode === 'login' ? 'Login' : 'Sign up'}</button>
      </form>
      <p>
        <button onClick={()=>setMode(mode==='login'?'signup':'login')}>Switch to {mode==='login'?'Sign up':'Login'}</button>
      </p>
      {message && (
        <p style={{ color: status === 'ok' ? 'green' : 'crimson' }}>{message}</p>
      )}
    </div>
  )
}
