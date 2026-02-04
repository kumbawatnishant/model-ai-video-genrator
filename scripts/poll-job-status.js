#!/usr/bin/env node
// Poll a job status from the backend until completion.
// Usage: node scripts/poll-job-status.js <jobId> [BASE_URL] [AUTH_TOKEN] [INTERVAL_SEC]

const jobId = process.argv[2];
const BASE_URL = process.argv[3] || 'http://localhost:4000';
const TOKEN = process.argv[4] || 'demo-token';
const INTERVAL = Number(process.argv[5] || 2);

if (!jobId) {
  console.error('Usage: node scripts/poll-job-status.js <jobId> [BASE_URL] [AUTH_TOKEN] [INTERVAL_SEC]');
  process.exit(2);
}

async function fetchStatus() {
  try {
    const url = `${BASE_URL.replace(/\/$/, '')}/api/jobs/${encodeURIComponent(jobId)}`;
    // Use global fetch if available (Node 18+), otherwise fallback to https
    if (typeof fetch === 'function') {
      const res = await fetch(url, { headers: { Authorization: `Bearer ${TOKEN}` } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    }
    // fallback: use https module
    return await new Promise((resolve, reject) => {
      const { URL } = require('url');
      const u = new URL(url);
      const https = require(u.protocol === 'https:' ? 'https' : 'http');
      const opts = { hostname: u.hostname, port: u.port, path: u.pathname + u.search, method: 'GET', headers: { Authorization: `Bearer ${TOKEN}` } };
      const req = https.request(opts, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            if (res.statusCode >= 200 && res.statusCode < 300) resolve(JSON.parse(data));
            else reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          } catch (err) { reject(err); }
        });
      });
      req.on('error', reject);
      req.end();
    });
  } catch (err) {
    throw err;
  }
}

let lastStatus = null;
(async () => {
  console.log(`Polling job ${jobId} every ${INTERVAL}s at ${BASE_URL}`);
  while (true) {
    try {
      const job = await fetchStatus();
      const status = job.status || 'unknown';
      if (status !== lastStatus) console.log(new Date().toISOString(), `status=${status}`, job);
      lastStatus = status;
      if (status === 'succeeded' || status === 'failed' || status === 'cancelled') {
        console.log('Job finished with status:', status);
        process.exit(status === 'succeeded' ? 0 : 1);
      }
    } catch (err) {
      console.error('Error fetching status:', err.message || err);
    }
    await new Promise((r) => setTimeout(r, INTERVAL * 1000));
  }
})();
