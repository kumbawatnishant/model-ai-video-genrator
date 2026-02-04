const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const { v4: uuidv4 } = require('uuid');

const { Subscription, User } = require('../models');

// Whop product link supplied by user; used as checkout target in this scaffold
const WHOP_PRODUCT_URL = process.env.WHOP_PRODUCT_URL || 'https://whop.com/model-ai-video/model-ai-9f/';

router.use(auth);

router.get('/', async (req, res) => {
  const email = req.user.email;
  try {
    const user = await User.findOne({ where: { email }, include: ['subscription'] });
    if (!user || !user.subscription) return res.json({ status: 'none' });
    res.json(user.subscription);
  } catch (e) {
    console.error('get subscription', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.post('/', async (req, res) => {
  const email = req.user.email;
  const { plan_id } = req.body;
  try {
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(500).json({ error: 'user not found' });
    const now = new Date();
    const nextBilling = new Date(now.getTime() + 30 * 24 * 3600 * 1000);
    const sub = await Subscription.create({ plan_id: plan_id || 'starter', status: 'active', tier: 'starter', quotas: { videos_per_month: 10 }, next_billing_at: nextBilling, UserId: user.id });
    const checkout_url = `${WHOP_PRODUCT_URL}`;
    res.status(201).json({ checkout_url, subscription: sub });
  } catch (e) {
    console.error('create subscription', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.post('/:id/cancel', async (req, res) => {
  const email = req.user.email;
  const id = req.params.id;
  try {
    const user = await User.findOne({ where: { email }, include: ['subscription'] });
    if (!user || !user.subscription || user.subscription.id !== id) return res.status(404).json({ error: 'not found' });
    user.subscription.status = 'canceled';
    await user.subscription.save();
    res.status(204).end();
  } catch (e) {
    console.error('cancel subscription', e);
    res.status(500).json({ error: 'internal' });
  }
});

router.get('/portal', async (req, res) => {
  const portal_url = process.env.WHOP_PORTAL_URL || WHOP_PRODUCT_URL;
  res.json({ portal_url });
});

module.exports = router;
