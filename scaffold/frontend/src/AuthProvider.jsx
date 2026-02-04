import React, { createContext, useEffect, useState } from 'react'
import axios from 'axios'

export const AuthContext = createContext({ user: null, loading: true, refresh: async ()=>{} })

export default function AuthProvider({ children }){
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  async function fetchMe(){
    try{
      const res = await axios.get('/api/auth/me', { withCredentials: true })
      setUser(res.data)
    }catch(e){
      setUser(null)
    }finally{
      setLoading(false)
    }
  }

  useEffect(()=>{
    axios.defaults.withCredentials = true
    fetchMe()
  },[])

  async function refresh(){
    try{
      await axios.post('/api/auth/refresh', {}, { withCredentials: true })
      await fetchMe()
    }catch(e){
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, refresh }}>{children}</AuthContext.Provider>
  )
}
