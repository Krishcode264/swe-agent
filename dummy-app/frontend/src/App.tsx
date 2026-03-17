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
      const res = await fetch('http://localhost:5000/simulate-incident', { method: 'POST' });
      const data = await res.json();
      setMessage(data.message || 'Simulated incident triggered on backend!');
    } catch (error: any) {
      setMessage('Failed to trigger simulation');
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
