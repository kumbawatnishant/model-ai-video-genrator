import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function Billing(){
  const [sub, setSub] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load(){
    try{
      const res = await axios.get('/api/subscriptions')
      setSub(res.data)
    }catch(e){ console.error(e) }
  }

  useEffect(()=>{ load() },[])

  async function create(){
    try{
      setLoading(true)
      const res = await axios.post('/api/subscriptions', { plan_id: 'starter' })
      window.open(res.data.checkout_url, '_blank')
      await load()
    }catch(e){ console.error(e) }
    finally{ setLoading(false) }
  }

  return (
    <div style={{padding:16}}>
      <h2>Billing</h2>
      {sub && sub.status !== 'none' ? (
        <div>
          <p>Plan: {sub.plan_id} — Status: {sub.status}</p>
          <button onClick={async ()=>{ await axios.post(`/api/subscriptions/${sub.id}/cancel`); load()}}>Cancel</button>
        </div>
      ) : (
        <div>
          <p>No active subscription.</p>
          <button onClick={create}>Subscribe (open Whop)</button>
        </div>
      )}
    </div>
  )
}
