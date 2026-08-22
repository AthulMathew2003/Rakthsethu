/**
 * Rakthasethu API Service Layer
 * Centralized module for all backend API calls.
 * Connects React frontend to FastAPI + PostgreSQL backend.
 */

const API_BASE = 'http://127.0.0.1:8000';

// ─── Token helpers ──────────────────────────────────────────
function getToken() {
  return localStorage.getItem('access_token');
}

function setToken(token) {
  localStorage.setItem('access_token', token);
}

function clearToken() {
  localStorage.removeItem('access_token');
}

// ─── Base fetch wrapper ─────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      errorDetail = errBody.detail || errorDetail;
    } catch {
      // ignore parse errors
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// ─── Auth ───────────────────────────────────────────────────
export async function loginUser(email, password) {
  const data = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (data.access_token) {
    setToken(data.access_token);
  }

  return data; // { access_token, token_type, user }
}

export async function fetchCurrentUser() {
  return apiFetch('/api/auth/me');
}

export function logoutUser() {
  clearToken();
  localStorage.removeItem('user');
}

// ─── Dashboard Stats ────────────────────────────────────────
export async function fetchDashboardStats(period = 'This Month') {
  return apiFetch(`/api/dashboard/stats?period=${encodeURIComponent(period)}`);
}

// ─── Donors ─────────────────────────────────────────────────
export async function fetchDonors({
  search = '',
  group = 'All',
  status = 'All',
  location = 'All',
  page = 1,
  limit = 7,
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (group && group !== 'All') params.set('group', group);
  if (status && status !== 'All') params.set('status', status);
  if (location && location !== 'All') params.set('location', location);
  params.set('page', String(page));
  params.set('limit', String(limit));

  return apiFetch(`/api/donors?${params.toString()}`);
}

export async function createDonor(donorData) {
  return apiFetch('/api/donors', {
    method: 'POST',
    body: JSON.stringify(donorData),
  });
}

export async function updateDonor(id, donorData) {
  return apiFetch(`/api/donors/${id}`, {
    method: 'PUT',
    body: JSON.stringify(donorData),
  });
}

export async function deleteDonorApi(id) {
  return apiFetch(`/api/donors/${id}`, {
    method: 'DELETE',
  });
}

// ─── Blood Requests ─────────────────────────────────────────
export async function fetchBloodRequests(statusFilter, urgency) {
  const params = new URLSearchParams();
  if (statusFilter && statusFilter !== 'All') params.set('status', statusFilter);
  if (urgency && urgency !== 'All') params.set('urgency', urgency);
  return apiFetch(`/api/requests?${params.toString()}`);
}

// ─── Inventory ──────────────────────────────────────────────
export async function fetchInventory() {
  return apiFetch('/api/inventory');
}

export { getToken, clearToken };
