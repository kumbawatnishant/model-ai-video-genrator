require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const { initDb } = require('./models');

const authRoutes = require('./routes/auth');
const jobsRoutes = require('./routes/jobs');
const keysRoutes = require('./routes/keys');
const subsRoutes = require('./routes/subscriptions');
const uploadsRoutes = require('./routes/uploads');

const app = express();
app.use(cors({ origin: true, credentials: true }));
app.use(bodyParser.json());
app.use(cookieParser());

// Allow credentials from frontend dev (Vite) by allowing credentials in CORS and handling cookies.

app.use('/api/auth', authRoutes);
app.use('/api/jobs', jobsRoutes);
app.use('/api/user/keys', keysRoutes);
app.use('/api/subscriptions', subsRoutes);
app.use('/api/uploads', uploadsRoutes);

app.get('/api/health', (req, res) => res.json({status: 'ok'}));

async function start() {
	try {
		await initDb();
		console.log('Database initialized (scaffold)');
	} catch (e) {
		console.warn('Database unavailable at start:', e.message || e);
	}
	const port = process.env.PORT || 4000;
	app.listen(port, () => console.log(`Backend scaffold listening on ${port}`));
}

start();
