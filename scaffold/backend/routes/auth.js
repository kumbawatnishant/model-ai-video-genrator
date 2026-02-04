const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

const { User } = require('../models');

// Helper for tokens
const ACCESS_EXPIRES = process.env.ACCESS_TOKEN_EXPIRES || '15m';
const REFRESH_EXPIRES = process.env.REFRESH_TOKEN_EXPIRES || '7d';
const COOKIE_SECURE = process.env.COOKIE_SECURE === 'true' || process.env.NODE_ENV === 'production';

function signAccess(email) {
  return jwt.sign({ sub: email }, process.env.JWT_SECRET || 'dev-secret', { expiresIn: ACCESS_EXPIRES });
}

function signRefresh(email) {
  return jwt.sign({ sub: email }, process.env.REFRESH_SECRET || process.env.JWT_SECRET || 'dev-secret', { expiresIn: REFRESH_EXPIRES });
}

// Create user and set httpOnly cookies for access & refresh
router.post('/signup', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ error: 'email & password required' });
  try {
    const existing = await User.findOne({ where: { email } });
    if (existing) return res.status(409).json({ error: 'user exists' });
    const hash = await bcrypt.hash(password, 8);
    const user = await User.create({ email, passwordHash: hash });
    const access = signAccess(email);
    const refresh = signRefresh(email);
    // persist refresh token for simple revocation
    user.refreshToken = refresh;
    await user.save();
    res.cookie('access_token', access, { httpOnly: true, secure: COOKIE_SECURE, sameSite: 'lax', maxAge: 15 * 60 * 1000 });
    res.cookie('refresh_token', refresh, { httpOnly: true, secure: COOKIE_SECURE, sameSite: 'lax', maxAge: 7 * 24 * 3600 * 1000 });
    res.json({ email: user.email });
  } catch (e) {
    console.error('signup error', e);
    res.status(500).json({ error: 'internal' });
  }
});

// Login: verify and set cookies
router.post('/login', async (req, res) => {
  const { email, password } = req.body;
  try {
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(401).json({ error: 'invalid credentials' });
    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) return res.status(401).json({ error: 'invalid credentials' });
    const access = signAccess(email);
    const refresh = signRefresh(email);
    user.refreshToken = refresh;
    await user.save();
    res.cookie('access_token', access, { httpOnly: true, secure: COOKIE_SECURE, sameSite: 'lax', maxAge: 15 * 60 * 1000 });
    res.cookie('refresh_token', refresh, { httpOnly: true, secure: COOKIE_SECURE, sameSite: 'lax', maxAge: 7 * 24 * 3600 * 1000 });
    res.json({ email: user.email });
  } catch (e) {
    console.error('login error', e);
    res.status(500).json({ error: 'internal' });
  }
});

// Refresh endpoint - issues a new access token if refresh cookie valid
router.post('/refresh', async (req, res) => {
  try {
    const token = req.cookies && req.cookies.refresh_token;
    if (!token) return res.status(401).json({ error: 'missing refresh token' });
    const payload = jwt.verify(token, process.env.REFRESH_SECRET || process.env.JWT_SECRET || 'dev-secret');
    const email = payload.sub;
    const user = await User.findOne({ where: { email } });
    if (!user || !user.refreshToken) return res.status(401).json({ error: 'invalid refresh' });
    // simple check: tokens must match stored
    if (user.refreshToken !== token) return res.status(401).json({ error: 'token mismatch' });
    const access = signAccess(email);
    res.cookie('access_token', access, { httpOnly: true, secure: COOKIE_SECURE, sameSite: 'lax', maxAge: 15 * 60 * 1000 });
    res.json({ email });
  } catch (e) {
    console.error('refresh error', e);
    res.status(401).json({ error: 'invalid refresh' });
  }
});

// Logout: clear cookies and remove stored refresh token
router.post('/logout', async (req, res) => {
  try {
    const token = req.cookies && req.cookies.refresh_token;
    if (token) {
      try {
        const payload = jwt.verify(token, process.env.REFRESH_SECRET || process.env.JWT_SECRET || 'dev-secret');
        const email = payload.sub;
        const user = await User.findOne({ where: { email } });
        if (user) { user.refreshToken = null; await user.save(); }
      } catch (e) {}
    }
    res.clearCookie('access_token');
    res.clearCookie('refresh_token');
    res.status(204).end();
  } catch (e) {
    res.status(500).end();
  }
});

// Me endpoint: returns current user when access token cookie present
router.get('/me', async (req, res) => {
  try {
    // auth middleware not used here; read cookie or header
    let token = null;
    const h = req.headers.authorization;
    if (h && h.startsWith('Bearer ')) token = h.split(' ')[1];
    else if (req.cookies && req.cookies.access_token) token = req.cookies.access_token;
    if (!token) return res.status(401).json({ error: 'unauthenticated' });
    const payload = jwt.verify(token, process.env.JWT_SECRET || 'dev-secret');
    res.json({ email: payload.sub });
  } catch (e) {
    res.status(401).json({ error: 'unauthenticated' });
  }
});

module.exports = router;
