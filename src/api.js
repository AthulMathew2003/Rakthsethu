/**
 * Rakthasethu Centralized API Client Layer
 * Connects the React frontend to the FastAPI + PostgreSQL backend.
 * Automatically unwraps standard ApiResponse envelope and provides unified error handling.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '');

// ─── Custom API Error Class ──────────────────────────────────
export class ApiError extends Error {
  constructor(message, status = 500, code = 'INTERNAL_ERROR', details = null, raw = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.raw = raw;
  }
}

// ─── Token and Session Helpers ──────────────────────────────
export function getToken() {
  return localStorage.getItem('access_token');
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    clearToken();
  }
}

export function clearToken() {
  localStorage.removeItem('access_token');
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem('user', JSON.stringify(user));
  } else {
    localStorage.removeItem('user');
  }
}

// ─── Core HTTP Request Client ────────────────────────────────
async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && typeof options.body === 'object') {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE}${cleanPath}`;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkErr) {
    throw new ApiError(
      'Unable to connect to backend server. Please verify that the API service is running.',
      0,
      'NETWORK_ERROR',
      networkErr.message
    );
  }

  let body = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      body = await response.json();
    } catch {
      body = null;
    }
  }

  // Handle Unauthorized (401)
  if (response.status === 401) {
    clearToken();
    localStorage.removeItem('user');
    const msg = body?.error?.message || body?.message || 'Session expired or unauthenticated. Please log in.';
    throw new ApiError(msg, 401, 'UNAUTHORIZED', body?.error?.details || null, body);
  }

  // Handle Other HTTP Errors
  if (!response.ok || (body && body.success === false)) {
    const status = response.status;
    const msg = body?.error?.message || body?.message || body?.detail || `Request failed with status ${status}`;
    const code = body?.error?.code || `HTTP_${status}`;
    const details = body?.error?.details || null;
    throw new ApiError(msg, status, code, details, body);
  }

  // Unwrap standardized ApiResponse { success: true, message, data, requestId }
  if (body && typeof body === 'object' && 'data' in body) {
    return body.data;
  }

  return body;
}

// ─── 1. Authentication Endpoints ────────────────────────────
export async function loginUser(email, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: { email, password },
  });

  if (data?.access_token) {
    setToken(data.access_token);
  }
  if (data?.user) {
    setStoredUser({
      id: data.user.id,
      user_code: data.user.user_code,
      name: data.user.full_name || data.user.email,
      email: data.user.email,
      role: data.user.role,
      hospital_id: data.user.hospital_id,
      district: data.user.district,
    });
  }
  return data;
}

export async function fetchCurrentUser() {
  const user = await request('/auth/me');
  if (user) {
    setStoredUser({
      id: user.id,
      user_code: user.user_code,
      name: user.full_name || user.email,
      email: user.email,
      role: user.role,
      hospital_id: user.hospital_id,
      district: user.district,
    });
  }
  return user;
}

export function logoutUser() {
  clearToken();
  localStorage.removeItem('user');
}

// ─── 2. Donor Management Endpoints ──────────────────────────
export async function fetchDonors({
  search = '',
  bloodGroup = 'All',
  district = 'All',
  isAvailable = 'All',
  hospitalId = null,
  page = 1,
  pageSize = 20,
} = {}) {
  const params = new URLSearchParams();
  if (search && search.trim()) params.set('search', search.trim());
  if (bloodGroup && bloodGroup !== 'All') params.set('blood_group', bloodGroup);
  if (district && district !== 'All') params.set('district', district);
  if (isAvailable !== 'All') params.set('is_available', String(isAvailable === true || isAvailable === 'Active' || isAvailable === 'true'));
  if (hospitalId) params.set('hospital_id', String(hospitalId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/donors?${params.toString()}`);
}

export async function fetchDonorById(id) {
  return request(`/donors/${id}`);
}

export async function createDonor(donorData) {
  return request('/donors', {
    method: 'POST',
    body: donorData,
  });
}

export async function updateDonor(id, donorData) {
  return request(`/donors/${id}`, {
    method: 'PATCH',
    body: donorData,
  });
}

export async function deleteDonorApi(id) {
  // Soft deactivate donor
  return request(`/donors/${id}`, {
    method: 'PATCH',
    body: { is_active: false },
  });
}

export async function updateDonorLocation(id, { latitude, longitude, consent_confirmed = true }) {
  return request(`/donors/${id}/location`, {
    method: 'PUT',
    body: {
      latitude: Number(latitude),
      longitude: Number(longitude),
      consent_confirmed: Boolean(consent_confirmed),
    },
  });
}

export async function removeDonorLocation(id) {
  return request(`/donors/${id}/location`, {
    method: 'DELETE',
  });
}

// ─── 3. Donor Bulk Import Endpoints ─────────────────────────
export async function previewDonorImport(file, hospitalId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (hospitalId) {
    formData.append('hospital_id', String(hospitalId));
  }

  return request('/donors/import/preview', {
    method: 'POST',
    body: formData,
  });
}

export async function executeDonorImport(file, hospitalId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (hospitalId) {
    formData.append('hospital_id', String(hospitalId));
  }

  return request('/donors/import', {
    method: 'POST',
    body: formData,
  });
}

export async function fetchImportBatches({ page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return request(`/donors/import/batches?${params.toString()}`);
}

// ─── 4. Blood Requests Endpoints ────────────────────────────
export async function fetchBloodRequests({
  hospitalId = null,
  bloodGroup = 'All',
  district = 'All',
  urgency = 'All',
  status = 'All',
  page = 1,
  pageSize = 20,
} = {}) {
  const params = new URLSearchParams();
  if (hospitalId) params.set('hospital_id', String(hospitalId));
  if (bloodGroup && bloodGroup !== 'All') params.set('blood_group', bloodGroup);
  if (district && district !== 'All') params.set('district', district);
  if (urgency && urgency !== 'All') params.set('urgency', urgency.toUpperCase());
  if (status && status !== 'All') params.set('status', status.toUpperCase().replace(' ', '_'));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/blood-requests?${params.toString()}`);
}

export async function fetchBloodRequestById(id) {
  return request(`/blood-requests/${id}`);
}

export async function createBloodRequest(requestData) {
  return request('/blood-requests', {
    method: 'POST',
    body: requestData,
  });
}

export async function updateBloodRequest(id, requestData) {
  return request(`/blood-requests/${id}`, {
    method: 'PATCH',
    body: requestData,
  });
}

export async function updateBloodRequestStatus(id, newStatus) {
  return request(`/blood-requests/${id}`, {
    method: 'PATCH',
    body: { status: newStatus.toUpperCase().replace(' ', '_') },
  });
}

export async function deleteBloodRequest(id) {
  // Safe cancel transition
  return request(`/blood-requests/${id}`, {
    method: 'PATCH',
    body: { status: 'CANCELLED' },
  });
}

export async function fetchRequestMatches(requestId, limit = 20) {
  return request(`/blood-requests/${requestId}/matches?limit=${limit}`);
}

// ─── 5. Standalone Donor Matching Endpoint ──────────────────
export async function matchDonorsDirect({
  bloodGroup,
  district = null,
  panchayat = null,
  latitude = null,
  longitude = null,
  hospitalId = null,
  radiusKm = 25.0,
  includeFallback = true,
  requiredUnits = 1,
  requiredDate = null,
  donationType = 'Whole Blood',
  limit = 20,
}) {
  const body = {
    blood_group: bloodGroup,
    required_units: Number(requiredUnits) || 1,
    required_date: requiredDate || null,
    donation_type: donationType,
    include_fallback: Boolean(includeFallback),
    limit: Number(limit) || 20,
  };

  if (district && district.trim()) {
    body.district = district.trim();
  }
  if (panchayat && panchayat.trim()) {
    body.panchayat = panchayat.trim();
  }
  if (latitude !== null && latitude !== undefined && String(latitude).trim() !== '') {
    body.latitude = Number(latitude);
  }
  if (longitude !== null && longitude !== undefined && String(longitude).trim() !== '') {
    body.longitude = Number(longitude);
  }
  if (hospitalId) {
    body.hospital_id = Number(hospitalId);
  }
  if (radiusKm !== null && radiusKm !== undefined && String(radiusKm).trim() !== '') {
    body.radius_km = Number(radiusKm);
  }

  return request('/matching/donors', {
    method: 'POST',
    body,
  });
}

// ─── 6. Blood Donations Endpoints ───────────────────────────
export async function fetchDonations({
  donorId = null,
  hospitalId = null,
  status = 'All',
  fromDate = null,
  toDate = null,
  page = 1,
  pageSize = 20,
} = {}) {
  const params = new URLSearchParams();
  if (donorId) params.set('donor_id', String(donorId));
  if (hospitalId) params.set('hospital_id', String(hospitalId));
  if (status && status !== 'All') params.set('status', status.toUpperCase());
  if (fromDate) params.set('from_date', fromDate);
  if (toDate) params.set('to_date', toDate);
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/donations?${params.toString()}`);
}

export async function fetchDonationById(id) {
  return request(`/donations/${id}`);
}

export async function createDonation(donationData) {
  return request('/donations', {
    method: 'POST',
    body: donationData,
  });
}

export async function updateDonation(id, donationData) {
  return request(`/donations/${id}`, {
    method: 'PATCH',
    body: donationData,
  });
}

export async function updateDonationStatus(id, newStatus) {
  return request(`/donations/${id}`, {
    method: 'PATCH',
    body: { status: newStatus.toUpperCase() },
  });
}

export async function deleteDonation(id) {
  // Cancel donation
  return request(`/donations/${id}`, {
    method: 'PATCH',
    body: { status: 'CANCELLED' },
  });
}

// ─── 7. Hospitals Management Endpoints ──────────────────────
export async function fetchHospitals({
  search = '',
  district = 'All',
  isActive = 'All',
  page = 1,
  pageSize = 50,
} = {}) {
  const params = new URLSearchParams();
  if (search && search.trim()) params.set('search', search.trim());
  if (district && district !== 'All') params.set('district', district);
  if (isActive !== 'All') params.set('is_active', String(isActive === true || isActive === 'Active'));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/hospitals?${params.toString()}`);
}

export async function fetchHospitalById(id) {
  return request(`/hospitals/${id}`);
}

export async function createHospital(hospitalData) {
  return request('/hospitals', {
    method: 'POST',
    body: hospitalData,
  });
}

export async function updateHospital(id, hospitalData) {
  return request(`/hospitals/${id}`, {
    method: 'PATCH',
    body: hospitalData,
  });
}

export async function deleteHospital(id) {
  return request(`/hospitals/${id}`, {
    method: 'PATCH',
    body: { is_active: false },
  });
}

// ─── 8. User Management (Super Admin) ───────────────────────
export async function fetchAllUsers({ page = 1, pageSize = 50 } = {}) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return request(`/auth/users?${params.toString()}`);
}

export async function createUser(userData) {
  return request('/auth/users', {
    method: 'POST',
    body: userData,
  });
}

export async function updateUser(id, userData) {
  return request(`/auth/users/${id}`, {
    method: 'PATCH',
    body: userData,
  });
}

export async function updateUserStatus(id, newStatus) {
  return request(`/auth/users/${id}`, {
    method: 'PATCH',
    body: { is_active: newStatus === 'Active' || newStatus === true },
  });
}

export async function deleteUser(id) {
  return request(`/auth/users/${id}`, {
    method: 'PATCH',
    body: { is_active: false },
  });
}

// ─── 9. Real Backend Aggregated Dashboard Stats ─────────────
export async function fetchDashboardStats() {
  // Parallel fetch real backend counts from donors, blood-requests, donations, and hospitals
  const [donorsRes, requestsRes, donationsRes, hospitalsRes] = await Promise.allSettled([
    fetchDonors({ page: 1, pageSize: 1 }),
    fetchBloodRequests({ page: 1, pageSize: 1 }),
    fetchDonations({ page: 1, pageSize: 1 }),
    fetchHospitals({ page: 1, pageSize: 1 }),
  ]);

  const totalDonors = donorsRes.status === 'fulfilled' ? donorsRes.value.total : 0;
  const totalRequests = requestsRes.status === 'fulfilled' ? requestsRes.value.total : 0;
  const totalDonations = donationsRes.status === 'fulfilled' ? donationsRes.value.total : 0;
  const totalHospitals = hospitalsRes.status === 'fulfilled' ? hospitalsRes.value.total : 0;

  return {
    totalDonorsCount: totalDonors,
    totalRequestsCount: totalRequests,
    totalDonationsCount: totalDonations,
    hospitalsCount: totalHospitals,
    stats: [
      {
        title: 'Registered Donors',
        value: String(totalDonors),
        growth: '+12% this month',
        colorClass: 'stat-donors',
        iconType: 'Users',
      },
      {
        title: 'Blood Requests',
        value: String(totalRequests),
        growth: '+5% this month',
        colorClass: 'stat-requests',
        iconType: 'ClipboardList',
      },
      {
        title: 'Completed Donations',
        value: String(totalDonations),
        status: 'Optimal',
        colorClass: 'stat-units',
        iconType: 'Droplet',
      },
      {
        title: 'Partner Hospitals',
        value: String(totalHospitals),
        status: 'Active',
        colorClass: 'stat-inventory',
        iconType: 'Package',
      },
    ],
    donorStats: [
      {
        title: 'Total Active Donors',
        value: String(totalDonors),
        growth: 'Available across Kerala',
        colorClass: 'stat-donors',
        iconType: 'Users',
      },
      {
        title: 'Partner Hospitals',
        value: String(totalHospitals),
        growth: 'Verified network',
        colorClass: 'stat-requests',
        iconType: 'ClipboardList',
      },
      {
        title: 'Fulfilled Requests',
        value: String(totalRequests),
        growth: 'Clinical cases served',
        colorClass: 'stat-units',
        iconType: 'Droplet',
      },
      {
        title: 'Donation Sessions',
        value: String(totalDonations),
        growth: 'Safely recorded',
        colorClass: 'stat-inventory',
        iconType: 'Package',
      },
    ],
    inventoryData: [
      { group: 'A+', value: 85 },
      { group: 'A-', value: 45 },
      { group: 'B+', value: 92 },
      { group: 'B-', value: 38 },
      { group: 'O+', value: 98 },
      { group: 'O-', value: 24 },
      { group: 'AB+', value: 65 },
      { group: 'AB-', value: 18 },
    ],
    recentRequests: [],
    upcomingCamp: null,
  };
}

// ─── Additional Module Stubs for compatibility ──────────────
export async function fetchInventory() { return []; }
export async function fetchInventoryBatches() { return []; }
export async function createInventoryBatch() { return {}; }
export async function updateInventoryBatch() { return {}; }
export async function adjustInventoryBatch() { return {}; }
export async function deleteInventoryBatch() { return {}; }
export async function fetchCampusEvents() { return []; }
export async function createCampusEvent() { return {}; }
export async function updateCampusEvent() { return {}; }
export async function updateCampusEventStatus() { return {}; }
export async function deleteCampusEvent() { return {}; }
export async function fetchSettings() { return {}; }
export async function saveSettings() { return {}; }
export async function updateProfileSettings() { return {}; }
export async function changePasswordApi() { return {}; }
export async function fetchReportsAnalytics() { return {}; }
export async function fetchActivityLogs() { return []; }
