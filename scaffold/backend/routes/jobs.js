const express = require('express');
const router = express.Router();
const Redis = require('redis');

// Very small in-memory job store for scaffold/demo
let jobs = [];
let nextId = 1;

// Redis client (optional) - if REDIS_URL present we enqueue jobs into Redis list 'ai_jobs'
const REDIS_URL = process.env.REDIS_URL;
let redisClient = null;
let useRedis = false;
if (REDIS_URL) {
  try {
    redisClient = Redis.createClient({ url: REDIS_URL });
    redisClient.connect().catch((e) => console.error('Redis connect error', e));
    useRedis = true;
    console.log('Jobs route: configured to push to Redis at', REDIS_URL);
  } catch (e) {
    console.error('Failed to create Redis client:', e);
  }
}

// Simple auth middleware that checks Authorization: Bearer <token>
function authMiddleware(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth) return res.status(401).json({ error: 'missing auth' });
  // For scaffold we accept any non-empty token; in real app verify JWT
  next();
}

router.use(authMiddleware);

router.post('/', async (req, res) => {
  const { prompt, settings } = req.body;
  if (!prompt) return res.status(400).json({ error: 'prompt required' });
  const job = { id: String(nextId++), prompt, settings: settings || {}, status: 'queued', created_at: new Date().toISOString() };
  jobs.push(job);

  // If Redis is configured, enqueue the job payload for workers to pick up.
  if (useRedis && redisClient) {
    try {
      await redisClient.lPush('ai_jobs', JSON.stringify(job));
      console.log('Enqueued job to Redis:', job.id);
    } catch (e) {
      console.error('Failed to enqueue job to Redis:', e);
    }
  } else {
    // Simulate progress locally when no Redis is available
    setTimeout(() => {
      job.status = 'running';
      setTimeout(() => { job.status = 'succeeded'; job.result = { url: '/tmp/dry_run_video.mp4' }; }, 1500);
    }, 500);
  }

  res.status(202).json(job);
});

router.get('/', async (req, res) => {
  // If Redis is configured, attempt to read recent queued jobs (best-effort)
  if (useRedis && redisClient) {
    try {
      const raw = await redisClient.lRange('ai_jobs', 0, -1);
      const list = raw.map((r) => {
        try { return JSON.parse(r); } catch { return null; }
      }).filter(Boolean);
      // Merge with in-memory jobs (deduplicating by id)
      const merged = [...list, ...jobs].reduce((acc, cur) => {
        if (!acc.find((x) => x.id === cur.id)) acc.push(cur);
        return acc;
      }, []).slice().reverse();
      return res.json(merged);
    } catch (e) {
      console.error('Failed to read jobs from Redis:', e);
    }
  }
  res.json(jobs.slice().reverse());
});

router.get('/:id', (req, res) => {
  const job = jobs.find(j => j.id === req.params.id);
  if (!job) return res.status(404).json({ error: 'not found' });
  res.json(job);
});

module.exports = router;
