import React, { useState, useEffect } from 'react';

// @ts-ignore
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

interface Product {
  id: number;
  title: string;
  price: number;
  thumbnail: string;
}

function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [maxPrice, setMaxPrice] = useState<number>(1000);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [showPortal, setShowPortal] = useState(false);

  useEffect(() => {
    fetch('https://dummyjson.com/products?limit=12')
      .then(res => res.json())
      .then(data => setProducts(data.products || []))
      .catch(err => console.error("Failed to load products", err));
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(data.message);
      } else {
        setMessage(`Error: ${data.error} - ${data.detail}`);
      }
    } catch (error: any) {
      setMessage(`Network error: ${error.message}`);
    }
  };

  const filteredProducts = products.filter(p => p.price <= maxPrice);

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '1000px', margin: '0 auto', padding: '2rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eaeaea', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <h1 style={{ margin: 0, color: '#2563eb' }}>NextGen Electronics</h1>
        <button 
          onClick={() => setShowPortal(!showPortal)} 
          style={{ background: 'none', border: '1px solid #d1d5db', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>
          {showPortal ? 'Return to Store' : 'Customer Portal'}
        </button>
      </header>

      {!showPortal ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', margin: 0, color: '#374151' }}>Featured Products</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <label htmlFor="price-filter" style={{ fontSize: '0.9rem', color: '#4b5563' }}>
                Max Price: ${maxPrice}
              </label>
              <input 
                id="price-filter"
                type="range" 
                min="0" 
                max="2000" 
                step="50" 
                value={maxPrice} 
                onChange={(e) => setMaxPrice(Number(e.target.value))} 
              />
            </div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '2rem' }}>
            {filteredProducts.map(p => (
              <div key={p.id} style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '1.5rem', textAlign: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <div style={{ width: '100%', height: '150px', background: '#f3f4f6', borderRadius: '4px', marginBottom: '1rem', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img src={p.thumbnail} alt={p.title} style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }} />
                </div>
                <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem', color: '#111827' }}>{p.title}</h3>
                <p style={{ margin: 0, fontWeight: 'bold', color: '#2563eb' }}>${p.price.toFixed(2)}</p>
                <button style={{ marginTop: '1rem', width: '100%', background: '#111827', color: 'white', padding: '0.5rem', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                  Add to Cart
                </button>
              </div>
            ))}
            {filteredProducts.length === 0 && (
              <p style={{ color: '#6b7280', gridColumn: '1 / -1', textAlign: 'center', padding: '2rem' }}>No products found under ${maxPrice}.</p>
            )}
          </div>
        </div>
      ) : (
        <div style={{ maxWidth: '400px', margin: '3rem auto', background: '#f9fafb', padding: '2rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h2 style={{ textAlign: 'center', marginTop: 0, marginBottom: '1.5rem', color: '#111827' }}>Sign In to Portal</h2>
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <input 
              type="email" 
              placeholder="user@example.com" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              style={{ padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '4px' }}
            />
            <input 
              type="password" 
              placeholder="Password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              style={{ padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '4px' }}
            />
            <button type="submit" style={{ padding: '0.75rem', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              Log In
            </button>
          </form>
          {message && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: '#fee2e2', color: '#991b1b', borderRadius: '4px', fontSize: '14px', border: '1px solid #fecaca' }}>
              {message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
