import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function Dashboard(){
  const [jobs, setJobs] = useState([])
  useEffect(()=>{
    async function load(){
      try{
        const res = await axios.get('/api/jobs')
        setJobs(res.data)
      }catch(e){
        console.error(e)
      }
    }
    load()
  },[])

  return (
    <div style={{padding:16}}>
      <h2>Jobs</h2>
      {jobs.length === 0 && <p>No jobs yet.</p>}
      <ul>
        {jobs.map(j=> (
          <li key={j.id}>{j.id} — {j.prompt} — {j.status}</li>
        ))}
      </ul>
    </div>
  )
}
