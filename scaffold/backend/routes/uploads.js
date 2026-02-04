const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

// Simple in-memory token store for demo purposes
const tokens = {};

router.use(auth);

router.post('/token', (req, res) => {
  const { filename, content_type, expires_in } = req.body || {};
  if (!filename) return res.status(400).json({ error: 'filename is required' });
  const ttl = typeof expires_in === 'number' ? expires_in : 3600;
  const token = uuidv4();
  const expiresAt = new Date(Date.now() + ttl * 1000).toISOString();
  // Return a mocked presigned URL (for testing the frontend). In production generate an S3/GCS presigned URL.
  const url = `${req.protocol}://${req.get('host')}/uploads/mock/${token}/${encodeURIComponent(filename)}`;
  tokens[token] = { filename, content_type, expires_at: expiresAt };
  res.json({ url, method: 'PUT', expires_at: expiresAt, fields: {} });
});

module.exports = router;
