import express from 'express';
import path from 'path';
import authRouter from './routes/auth';

const app = express();
const PORT = process.env.PORT ?? 4000;

app.use(express.json());
app.use('/api/auth', authRouter);

app.get('/api/health', (_req, res) => {
  res.json({ ok: true });
});

// Serve the built React app (client/dist) in front of oauth2-proxy's single upstream.
const clientDist = path.join(__dirname, '..', '..', 'client', 'dist');
app.use(express.static(clientDist));
app.get('*', (_req, res) => {
  res.sendFile(path.join(clientDist, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`LMS server listening on port ${PORT}`);
});
