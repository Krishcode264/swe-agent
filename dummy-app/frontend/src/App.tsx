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
      "incidentId": "INC-100333999",
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
      
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '1rem' }}>Admin Tools:</p>
        <button onClick={simulateIncident} style={{ padding: '0.5rem 1rem', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
          🚨 Simulate Production Incident
        </button>
      </div>
    </div>
  );
}

export default App;
