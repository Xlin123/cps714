import { Router } from 'express';
import { createUser, findUserByEmail } from '../db';
import { requireProxyAuth } from '../middleware/requireProxyAuth';

const router = Router();

router.use(requireProxyAuth);

// GET /api/auth/session — is the Google-authenticated caller registered locally?
router.get('/session', (req, res) => {
  const email = req.authEmail as string;
  const user = findUserByEmail(email);
  if (!user) {
    res.json({ needsRegistration: true, email });
    return;
  }
  res.json({ needsRegistration: false, user: { name: user.name, email: user.email, role: user.role } });
});

// POST /api/auth/register — create the local profile for an authenticated email.
router.post('/register', (req, res) => {
  const email = req.authEmail as string;
  const name = typeof req.body?.name === 'string' ? req.body.name.trim() : '';

  if (!name) {
    res.status(400).json({ error: 'Name is required.' });
    return;
  }

  if (findUserByEmail(email)) {
    res.status(409).json({ error: 'An account already exists for this email.' });
    return;
  }

  const user = createUser(name, email, 'member');
  res.status(201).json({ user: { name: user.name, email: user.email, role: user.role } });
});

export default router;
