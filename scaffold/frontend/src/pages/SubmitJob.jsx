import React, { useState } from 'react'
import axios from 'axios'

export default function SubmitJob(){
  const [prompt, setPrompt] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e){
    e.preventDefault()
    if (!prompt) return alert('prompt required')
    try{
      setLoading(true)
      const res = await axios.post('/api/jobs', { prompt })
      setMessage(`Job queued: ${res.data.id}`)
      setPrompt('')
    }catch(e){
      console.error(e)
      setMessage('Failed to submit')
    }finally{ setLoading(false) }
  }

  return (
    <div style={{padding:16}}>
      <h2>Submit Job</h2>
      <form onSubmit={submit}>
        <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} rows={6} cols={60} placeholder="Enter prompt" />
        <br />
  <button type="submit">{loading ? 'Submitting...' : 'Submit'}</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  )
}
