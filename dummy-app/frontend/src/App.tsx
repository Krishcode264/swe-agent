import React, { useState } from 'react';

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:5000/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message);
      } else {
        setMessage(`Error: ${data.error} - ${data.detail}`);
      }
    } catch (error: any) {
      console.log(" issue withy efcthcing ")
      setMessage(`Network error: ${error.message}`);
    }
  };

  const simulateIncident = async () => {
    const incident = {
      "incidentId": "INC-100112",
      "title": "Validation middleware broken after express-validator upgrade to v7",
      "severity": "P2 - High",
      "service": "node-service",
      "reported_by": "Backend Team",
      "environment": "all",
      "timestamp": "2026-02-27T14:00:00Z",
      "description": "After upgrading express-validator from v6 to v7, all request validation has stopped working. Routes that should reject invalid input are accepting everything. The validation middleware runs without errors but never catches invalid data. The express-validator v7 release changed the API — validationResult() and check() were replaced with a new API pattern.",
      "steps_to_reproduce": [
        "Send POST /api/users/register with empty body",
        "Expected: 400 error with validation messages",
        "Actual: Request passes validation and fails at database level with a 500 error"
      ],
      "error_log": "No validation errors returned. Database errors occur instead:\nSequelizeValidationError: notNull Violation: users.email cannot be null",
      "expected_behavior": "Invalid requests are caught by validation middleware and return 400 with descriptive error messages",
      "actual_behavior": "Validation middleware passes all requests through, database constraint violations cause 500 errors",
      "recent_changes": "Updated express-validator from ^6.14.0 to ^7.0.0 in package.json",
      "tags": ["dependency-issue", "validation", "breaking-change"],
      "status": "queued",
      "repository": "https://github.com/Rezinix-AI/shopstack-platform.git"
    };

    try {
      const res = await fetch('http://localhost:5000/webhook/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(incident),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message || 'Simulated incident triggered successfully!');
      } else {
        setMessage(`Error: ${data.error || 'Failed to trigger simulation'}`);
      }
    } catch (error: any) {
      setMessage(`Failed to trigger simulation: ${error.message}`);
    }
  };

  const simulateMathIncident = async () => {
    const incident = {
      "incidentId": "INC-MATH-FIX",
      "title": "Logic Error in math.js (Multiplication performing Addition)",
      "severity": "P2 - High",
      "service": "node-service",
      "reported_by": "QA",
      "environment": "production",
      "timestamp": new Date().toISOString(),
      "description": "The math.js file has a logic bug where the multiply function is adding numbers instead of multiplying them. Please correct the operator in math.js.",
      "steps_to_reproduce": [
        "Call multiply(2, 3)",
        "Expected: 6",
        "Actual: 5"
      ],
      "error_log": "Logic Error: multiply(2, 3) returned 5. The implementation in math.js is likely using '+' instead of '*'.",
      "expected_behavior": "multiply(a, b) should return a * b.",
      "actual_behavior": "multiply(a, b) returns a + b.",
      "tags": ["logic-bug", "math"],
      "status": "queued",
      "repository": "https://github.com/Krishcode264/testing-repo-for-swe-agent.git"
    };

    try {
      const res = await fetch('http://localhost:5000/webhook/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(incident),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message || 'Math incident triggered successfully!');
      } else {
        setMessage(`Error: ${data.error || 'Failed to trigger simulation'}`);
      }
    } catch (error: any) {
      setMessage(`Failed to trigger simulation: ${error.message}`);
    }
  };

  const simulateDiscountIncident = async () => {
    const incident = {
      "id": "INC-12345678",
      "incidentId": "INC-006",
      "title": "Discount code applied twice during checkout resulting in incorrect order totals",
      "severity": "P1 - Critical",
      "service": "python-service",
      "reported_by": "Finance Team",
      "environment": "production",
      "timestamp": "2026-02-27T19:00:00Z",
      "description": "Multiple customer orders show incorrect totals where the discount appears to have been applied twice. For example, a $100 order with a 20% discount code should total $80, but customers are being charged $64 (discount applied twice: $100 -> $80 -> $64). This is causing revenue loss.",
      "steps_to_reproduce": [
        "Add items to cart totaling $100",
        "Apply discount code 'SAVE20' (20% off)",
        "Proceed to checkout",
        "Observe final total is $64 instead of $80"
      ],
      "error_log": "No errors in logs. The system processes the order successfully but with wrong totals.",
      "expected_behavior": "Discount is applied once: $100 * 0.80 = $80.00",
      "actual_behavior": "Discount is applied twice: $100 * 0.80 * 0.80 = $64.00",
      "recent_changes": "Added discount support to the cart summary endpoint and checkout flow",
      "tags": ["logic-bug", "payments", "revenue-impact"],
      "status": "queued",
      "repository": "https://github.com/Krishcode264/shopstack-platform.git"
    };

    try {
      const res = await fetch('http://localhost:5000/webhook/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(incident),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message || 'INC-006 Discount incident triggered successfully!');
      } else {
        setMessage(`Error: ${data.error || 'Failed to trigger simulation'}`);
      }
    } catch (error: any) {
      setMessage(`Failed to trigger simulation: ${error.message}`);
    }
  };

  const simulateCORSIncident = async () => {
    const incident = {
      "id": "INC-10002",
      "incidentId": "INC-1022222",
      "title": "CORS error blocking all frontend API requests",
      "severity": "P1 - Critical",
      "service": "node-service",
      "reported_by": "Frontend Team",
      "environment": "staging",
      "timestamp": "2026-02-28T10:00:00Z",
      "description": "After deploying the latest Node.js service update, all API requests from the frontend are being blocked by CORS policy. The browser console shows 'Access-Control-Allow-Origin' header mismatch. The frontend application runs on port 5173 (Vite dev server) but the CORS configuration only allows port 3000.",
      "steps_to_reproduce": [
        "Start the frontend dev server (runs on http://localhost:5173)",
        "Start the node-service API (runs on http://localhost:3000)",
        "Open the frontend in a browser",
        "Observe CORS errors on every API call in the browser console"
      ],
      "error_log": "Access to XMLHttpRequest at 'http://localhost:3000/api/products' from origin 'http://localhost:5173' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: The 'Access-Control-Allow-Origin' header has a value 'http://localhost:3000' that is not equal to the supplied origin.",
      "expected_behavior": "API accepts requests from the frontend origin (http://localhost:5173) and production domain",
      "actual_behavior": "CORS is configured to only allow requests from http://localhost:3000, which is the API's own origin",
      "recent_changes": "CORS middleware was added during security hardening sprint",
      "tags": ["misconfiguration", "cors", "frontend-blocked"],
      "status": "queued",
      "repository": "https://github.com/Krishcode264/shopstack-platform.git"
    };

    try {
      const res = await fetch('http://localhost:5000/webhook/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(incident),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message || 'INC-102 CORS incident triggered successfully!');
      } else {
        setMessage(`Error: ${data.error || 'Failed to trigger simulation'}`);
      }
    } catch (error: any) {
      setMessage(`Failed to trigger simulation: ${error.message}`);
    }
  };

  return (
    <div style={{ background: '#fff', padding: '2rem', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: '#1a1a1a' }}>Login to AwesomeApp</h2>
      <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <input
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={{ padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px' }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{ padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px' }}
        />
        <button type="submit" style={{ padding: '0.75rem', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
          Log In
        </button>
      </form>

      {message && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: '#fee2e2', color: '#991b1b', borderRadius: '4px', fontSize: '14px' }}>
          {message}
        </div>
      )}

      <hr style={{ margin: '2rem 0', border: 'none', borderTop: '1px solid #eee' }} />

      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <p style={{ fontSize: '12px', color: '#666' }}>Admin Tools:</p>
        <button onClick={simulateIncident} style={{ padding: '0.5rem 1rem', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
          🚨 Simulate Production Incident (Shopstack)
        </button>
        <button onClick={simulateMathIncident} style={{ padding: '0.5rem 1rem', background: '#059669', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
          🧪 Simulate Math Bug (Testing Repo)
        </button>
        <button onClick={simulateDiscountIncident} style={{ padding: '0.5rem 1rem', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
          🚨 Simulate Double Discount Bug (INC-006 - Shopstack)
        </button>
        <button onClick={simulateCORSIncident} style={{ padding: '0.5rem 1rem', background: '#d97706', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
          🌐 Simulate CORS Error (INC-102 - Shopstack)
        </button>
      </div>
    </div>
  );
}

export default App;
