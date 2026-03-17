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
    try {
      const res = await fetch('http://localhost:5000/api/simulate-incident', { method: 'POST' });
      const data = await res.json();
      setMessage(data.message || 'Simulated incident triggered via Dummy Backend!');
    } catch (error: any) {
      setMessage('Failed to trigger simulation through backend');
    }
  };

  const reportLoginBug = async () => {
    try {
      const incidentData = {
        id: "INC-000003",
        title: "Server returns 500 error on POST /api/auth/login",
        severity: "P1 - Critical",
        service: "python-service",
        repository: "Krishcode264/shopstack-platform",
        description: "After the latest deployment, users are unable to log in. The POST /api/auth/login endpoint returns a 500 Internal Server Error. TypeError: a bytes-like object is required, not 'str' in app/routes/auth.py line 42",
        error_log: "TypeError: a bytes-like object is required, not 'str' in app/routes/auth.py line 42",
        suggested_files: ["app/routes/auth.py"]
      };

      const res = await fetch('http://localhost:4000/api/simulation/trigger', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(incidentData)
      });

      if (res.ok) {
        setMessage('Python Login Bug reported to Orchestrator!');
      } else {
        setMessage('Failed to report incident');
      }
    } catch (error: any) {
      setMessage(`Trigger failed: ${error.message}`);
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
      
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'center' }}>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '0.5rem' }}>Admin Tools:</p>
        <button onClick={simulateIncident} style={{ padding: '0.5rem 1rem', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', width: '220px' }}>
          🚨 Simulate Payment Bug (via DB)
        </button>
        <button onClick={reportLoginBug} style={{ padding: '0.5rem 1rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', width: '220px' }}>
          ⚡ Simulate Python Auth Bug
        </button>
      </div>
    </div>
  );
}

export default App;
