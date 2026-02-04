import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function Keys(){
  const [keys, setKeys] = useState([])
  const [provider, setProvider] = useState('')
  const [keyVal, setKeyVal] = useState('')

  async function load(){
    try{
      const res = await axios.get('/api/user/keys')
      setKeys(res.data)
    }catch(e){ console.error(e) }
  }

  useEffect(()=>{ load() },[])

  async function add(e){
    e.preventDefault()
    if (!provider || !keyVal) return alert('provider and key required')
    try{
      setLoading(true)
      await axios.post('/api/user/keys', { provider, key: keyVal })
      setProvider(''); setKeyVal('')
      await load()
    }catch(e){ console.error(e); alert('Failed to add key') }
    finally{ setLoading(false) }
  }

  async function del(id){
    if (!confirm('Delete key?')) return
    try{ setLoading(true); await axios.delete(`/api/user/keys/${id}`) ; await load() }catch(e){console.error(e); alert('Failed to delete') } finally{ setLoading(false) }
  }

  return (
    <div style={{padding:16}}>
      <h2>API Keys</h2>
      <form onSubmit={add}>
        <input placeholder="provider" value={provider} onChange={e=>setProvider(e.target.value)} />
        <input placeholder="key" value={keyVal} onChange={e=>setKeyVal(e.target.value)} />
        <button type="submit">{loading ? 'Adding...' : 'Add'}</button>
      </form>
      <ul>
        {keys.map(k => (
          <li key={k.id}>{k.provider} — {k.created_at} <button onClick={()=>del(k.id)} disabled={loading}>{loading ? '...' : 'Delete'}</button></li>
        ))}
      </ul>
    </div>
  )
}
