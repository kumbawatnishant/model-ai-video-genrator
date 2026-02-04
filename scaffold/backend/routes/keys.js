const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const { ApiKey, User } = require('../models');

router.use(auth);

router.post('/', async (req, res) => {
  const email = req.user.email;
  const { provider, key, meta } = req.body;
  if (!provider || !key) return res.status(400).json({ error: 'provider and key are required' });
  try {
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(500).json({ error: 'user not found' });
    const entry = await ApiKey.create({ provider, key, meta: meta || {}, UserId: user.id });
    res.status(201).json({ id: entry.id, provider: entry.provider, created_at: entry.createdAt, last_tested: entry.last_tested });
  } catch (e) {
    console.error('create api key', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.get('/', async (req, res) => {
  const email = req.user.email;
  try {
    const user = await User.findOne({ where: { email }, include: [{ model: ApiKey, as: 'apiKeys' }] });
    if (!user) return res.json([]);
    const list = (user.apiKeys || []).map((k) => ({ id: k.id, provider: k.provider, created_at: k.createdAt, last_tested: k.last_tested, meta: k.meta }));
    res.json(list);
  } catch (e) {
    console.error('list keys', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.get('/:id', async (req, res) => {
  const email = req.user.email;
  const id = req.params.id;
  try {
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(404).json({ error: 'not found' });
    const key = await ApiKey.findOne({ where: { id, UserId: user.id } });
    if (!key) return res.status(404).json({ error: 'not found' });
    res.json({ id: key.id, provider: key.provider, created_at: key.createdAt, last_tested: key.last_tested, meta: key.meta });
  } catch (e) {
    console.error('get key', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.delete('/:id', async (req, res) => {
  const email = req.user.email;
  const id = req.params.id;
  try {
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(404).json({ error: 'not found' });
    await ApiKey.destroy({ where: { id, UserId: user.id } });
    res.status(204).end();
  } catch (e) {
    console.error('delete key', e);
    res.status(500).json({ error: 'internal' });
  }
});

module.exports = router;
