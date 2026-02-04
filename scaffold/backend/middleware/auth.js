const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

// Auth middleware accepts either Authorization: Bearer <access_token>
// or an httpOnly cookie named 'access_token'.
function authMiddleware(req, res, next) {
  const header = req.headers.authorization;
  let token = null;
  if (header && header.startsWith('Bearer ')) {
    token = header.split(' ')[1];
  } else if (req.cookies && req.cookies.access_token) {
    token = req.cookies.access_token;
  }
  if (!token) return res.status(401).json({ error: 'missing auth' });
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = { email: payload.sub };
    next();
  } catch (e) {
    return res.status(401).json({ error: 'invalid token', detail: String(e) });
  }
}

module.exports = authMiddleware;
