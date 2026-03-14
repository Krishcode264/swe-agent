import express, { Request, Response } from 'express';
import cors from 'cors';
import axios from 'axios';
import bcrypt from 'bcrypt';

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 5000;
const BACKEND_WEBHOOK_URL = process.env.BACKEND_WEBHOOK_URL || 'http://localhost:4000/webhook/github';

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

// Dummy Products Route
app.get('/api/products', (req: Request, res: Response) => {
  res.status(200).json([
    { id: 101, name: 'Wireless Mouse', price: 29.99 },
    { id: 102, name: 'Mechanical Keyboard', price: 89.99 },
    { id: 103, name: 'Monitor Stand', price: 35.00 }
  ]);
});


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

app.post('/simulate-incident', async (req: Request, res: Response): Promise<void> => {
  const simulatedIncident = {
    title: "Server returns 500 error on POST /api/auth/login after latest deployment",
    body: "After the latest deployment to staging, users cannot log in. The POST /api/auth/login endpoint returns a 500 Internal Server Error.\n\nSteps to reproduce:\n1. Send POST request to /api/auth/login\n2. Payload: {\"email\": \"user@example.com\", \"password\": \"correctpassword\"}\n3. Observe HTTP 500 response\n\nError Log:\nTypeError: a bytes-like object is required, not 'str' in app/routes/auth.py line 42",
    repository: "https://github.com/org/python-service",
    sender: { login: "Frontend Team" }
  };

  try {
    console.log("Triggering webhook at", BACKEND_WEBHOOK_URL);
    await axios.post(BACKEND_WEBHOOK_URL, simulatedIncident);
    res.status(200).json({ message: "Incident simulated and webhook sent!" });
  } catch (error: any) {
    console.error("Failed to send webhook:", error.message);
    res.status(500).json({ error: "Failed to send webhook" });
  }
});

app.listen(PORT, () => {
  console.log(`Dummy backend listening on port ${PORT}`);
});
