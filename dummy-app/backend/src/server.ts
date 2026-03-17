import express, { Request, Response } from 'express';
import cors from 'cors';
import bcrypt from 'bcrypt';

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 5000;

// Intentional Bug Details
const BUGGY_CODE_LINE = 42;

// Healthcheck Route
app.get('/api/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', uptime: process.uptime() });
});

// Dummy Users Route
app.get('/api/users', (req: Request, res: Response) => {
  res.status(200).json([
    { id: 1, name: 'Alice', role: 'admin' },
    { id: 2, name: 'Bob', role: 'user' },
    { id: 3, name: 'Charlie', role: 'user' }
  ]);
});

// Removed local /api/products route since frontend expects DummyJSON now


app.post('/api/auth/login', async (req: Request, res: Response): Promise<void> => {
  try {
    const { email, password } = req.body;
    
    // INTENTIONAL BUG: Passing a non-string or expecting old behavior 
    // "TypeError: a bytes-like object is required, not 'str' in app/routes/auth.py line 42"
    // Here we'll simulate the Python failure equivalent as best as we can in Node.
    if (!password) {
      throw new TypeError("a bytes-like object is required, not 'str' in app/routes/auth.py line 42");
    }
    
    // Simulate some logic
    const dummyHash = await bcrypt.hash(password, 10);
    
    // If it reaches here, the bug didn't trigger, or we simulated it passing post-fix
    res.json({ token: "fake-jwt-token-12345", message: "Login successful!" });
  } catch (error: any) {
    console.error("Crash during login:", error.message);
    res.status(500).json({ error: 'Internal Server Error', detail: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Dummy backend listening on port ${PORT}`);
});
