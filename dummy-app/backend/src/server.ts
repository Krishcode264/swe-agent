import express, { Request, Response } from 'express';
import cors from 'cors';
import bcrypt from 'bcrypt';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

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
    
    // INTENTIONAL BUG
    if (!password) {
      throw new TypeError("a bytes-like object is required, not 'str' in app/routes/auth.py line 42");
    }
    
    res.json({ token: "fake-jwt-token-12345", message: "Login successful!" });
  } catch (error: any) {
    console.error("Crash during login:", error.message);
    res.status(500).json({ error: 'Internal Server Error', detail: error.message });
  }
});

// Specialized Simulator for Local Demo
app.post('/api/simulate-incident', async (req: Request, res: Response) => {
  try {
    const webhookUrl = process.env.BACKEND_WEBHOOK_URL || 'http://localhost:4000/api/webhooks/github';
    
    const incidentData = {
      action: "labeled",
      label: { name: "assign to agent" },
      issue: {
        number: 4,
        title: "test_payment_flow failing in CI pipeline",
        body: "The test_payment_flow test suite has been failing consistently in the CI pipeline since the last merge. The payment total calculation appears to be incorrect — tax amounts are computed as zero for order subtotals under $100. This is causing incorrect totals in the checkout flow.",
        user: { login: "QA Team" },
        html_url: "https://github.com/Rezinix-AI/shopstack-platform/issues/4"
      },
      repository: {
        full_name: "Rezinix-AI/shopstack-platform",
        html_url: "https://github.com/Rezinix-AI/shopstack-platform"
      },
      // Enhanced data passed directly as requested
      extra_info: {
        id: "INC-004",
        severity: "P2 - High",
        service: "python-service",
        repository: "Rezinix-AI/shopstack-platform",
        environment: "CI",
        timestamp: "2026-02-28T11:30:00Z",
        steps_to_reproduce: [
          "Run: python -m pytest tests/test_payments.py -v",
          "Observe test_calculate_total_with_tax fails",
          "Observe test_checkout_flow_complete fails"
        ],
        error_log: "FAILED tests/test_payments.py::TestPaymentFlow::test_calculate_total_with_tax - AssertionError: 49.99 != 54.24\nFAILED tests/test_payments.py::TestPaymentFlow::test_checkout_flow_complete - AssertionError: Order total mismatch",
        expected_behavior: "Tax of 8.5% is correctly applied to all order subtotals",
        actual_behavior: "Tax calculation returns 0 for subtotals under $100, resulting in incorrect totals",
        recent_changes: "Refactored payment calculation logic to use integer arithmetic for precision",
        tags: ["test-failure", "payments", "calculation-error"]
      }
    };

    console.log(`Sending simulated webhook to ${webhookUrl}...`);
    const response = await axios.post(webhookUrl, incidentData, {
      headers: { 'x-github-event': 'issues' }
    });

    res.json({ 
      message: 'Simulated incident webhook sent successfully', 
      backend_response: response.data 
    });
  } catch (error: any) {
    console.error("Failed to simulate incident:", error.message);
    res.status(500).json({ error: 'Simulation failed', detail: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Dummy backend listening on port ${PORT}`);
});
