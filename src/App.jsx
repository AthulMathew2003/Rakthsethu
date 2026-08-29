import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login.jsx';
import Dashboard from './Dashboard.jsx';
import { getToken, clearToken, fetchCurrentUser } from './api.js';

const isAdminRole = (role) => {
  if (!role) return false;
  const r = String(role).toLowerCase();
  return r.includes('admin') || r.includes('staff');
};

function ProtectedRoute({ user, children }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdminRole(user.role)) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function LoginWrapper({ user, onLoginSuccess }) {
  if (user && isAdminRole(user.role)) {
    return <Navigate to="/admin/dashboard" replace />;
  }
  return <Login onLoginSuccess={onLoginSuccess} />;
}

function App() {
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch (e) {
      console.error('Error loading user from localStorage:', e);
      return null;
    }
  });

  // On mount, validate stored token against backend
  useEffect(() => {
    const token = getToken();
    if (token && user) {
      fetchCurrentUser()
        .then((apiUser) => {
          // Update stored user with latest data from backend
          const updatedUser = {
            name: apiUser.full_name || apiUser.email,
            role: apiUser.role || 'Admin',
            email: apiUser.email,
            id: apiUser.id,
          };
          setUser(updatedUser);
          localStorage.setItem('user', JSON.stringify(updatedUser));
        })
        .catch(() => {
          // Token is invalid or expired — clear session
          console.warn('Token validation failed, clearing session.');
          clearToken();
          localStorage.removeItem('user');
          setUser(null);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogin = (userData) => {
    const adminUser = userData || { name: 'Admin', role: 'Admin' };
    setUser(adminUser);
    localStorage.setItem('user', JSON.stringify(adminUser));
  };

  const handleLogout = () => {
    setUser(null);
    clearToken();
    localStorage.removeItem('user');
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<LoginWrapper user={user} onLoginSuccess={handleLogin} />}
        />
        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/hospitals"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/blood-requests"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/blood-donations"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/blood-inventory"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/campus-events"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/reports"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute user={user}>
              <Dashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/"
          element={
            <Navigate to={user && isAdminRole(user.role) ? '/admin/dashboard' : '/login'} replace />
          }
        />
        <Route
          path="*"
          element={
            <Navigate to={user && isAdminRole(user.role) ? '/admin/dashboard' : '/login'} replace />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
