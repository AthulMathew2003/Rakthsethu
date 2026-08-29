/**
 * Rakthasethu API Service Layer
 * Centralized module for all backend API calls connecting the React frontend to FastAPI database backend.
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

  return data;
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

// ─── Blood Inventory (Batches & Summary) ─────────────────────
export async function fetchInventory() {
  return apiFetch('/api/inventory');
}

export async function fetchInventoryBatches({
  search = '',
  bloodGroup = 'All',
  component = 'All',
  status = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (bloodGroup && bloodGroup !== 'All') params.set('blood_group', bloodGroup);
  if (component && component !== 'All') params.set('component', component);
  if (status && status !== 'All') params.set('status', status);

  return apiFetch(`/api/inventory/batches?${params.toString()}`);
}

export async function createInventoryBatch(batchData) {
  return apiFetch('/api/inventory/batches', {
    method: 'POST',
    body: JSON.stringify({
      blood_group: batchData.bloodGroup,
      component: batchData.component,
      available_units: Number(batchData.availableUnits),
      reserved_units: Number(batchData.reservedUnits || 0),
      collection_date: batchData.collectionDate,
      expiry_date: batchData.expiryDate,
      storage_location: batchData.storageLocation,
      status: batchData.status || 'Available',
      notes: batchData.notes || '',
    }),
  });
}

export async function updateInventoryBatch(id, batchData) {
  return apiFetch(`/api/inventory/batches/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      blood_group: batchData.bloodGroup,
      component: batchData.component,
      available_units: Number(batchData.availableUnits),
      reserved_units: Number(batchData.reservedUnits || 0),
      collection_date: batchData.collectionDate,
      expiry_date: batchData.expiryDate,
      storage_location: batchData.storageLocation,
      status: batchData.status,
      notes: batchData.notes,
    }),
  });
}

export async function adjustInventoryBatch(id, type, quantity, reason) {
  return apiFetch(`/api/inventory/batches/${id}/adjust`, {
    method: 'POST',
    body: JSON.stringify({ type, quantity: Number(quantity), reason }),
  });
}

export async function deleteInventoryBatch(id) {
  return apiFetch(`/api/inventory/batches/${id}`, {
    method: 'DELETE',
  });
}

// ─── Blood Requests ─────────────────────────────────────────
export async function fetchBloodRequests({
  search = '',
  bloodGroup = 'All',
  status = 'All',
  urgency = 'All',
  district = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (bloodGroup && bloodGroup !== 'All') params.set('blood_group', bloodGroup);
  if (status && status !== 'All') params.set('status', status);
  if (urgency && urgency !== 'All') params.set('urgency', urgency);
  if (district && district !== 'All') params.set('district', district);

  return apiFetch(`/api/requests?${params.toString()}`);
}

export async function createBloodRequest(reqData) {
  return apiFetch('/api/requests', {
    method: 'POST',
    body: JSON.stringify({
      patient_name: reqData.patientName,
      blood_group: reqData.bloodGroup,
      units_requested: Number(reqData.unitsRequired || reqData.units_requested || 1),
      hospital_name: reqData.hospital || reqData.hospital_name,
      district: reqData.district || 'Kottayam',
      location: reqData.location || reqData.district || 'Kottayam',
      contact_phone: reqData.contactNumber || reqData.contact_phone,
      emergency_contact: reqData.emergencyContact || reqData.emergency_contact,
      required_date: reqData.requiredDate || reqData.required_date,
      urgency: reqData.urgency || 'Normal',
      status: reqData.status || 'Pending',
      notes: reqData.notes || '',
    }),
  });
}

export async function updateBloodRequest(id, reqData) {
  return apiFetch(`/api/requests/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      patient_name: reqData.patientName,
      blood_group: reqData.bloodGroup,
      units_requested: Number(reqData.unitsRequired || reqData.units_requested || 1),
      hospital_name: reqData.hospital || reqData.hospital_name,
      district: reqData.district,
      location: reqData.location || reqData.district,
      contact_phone: reqData.contactNumber || reqData.contact_phone,
      emergency_contact: reqData.emergencyContact || reqData.emergency_contact,
      required_date: reqData.requiredDate || reqData.required_date,
      urgency: reqData.urgency,
      status: reqData.status,
      notes: reqData.notes,
    }),
  });
}

export async function updateBloodRequestStatus(id, newStatus) {
  return apiFetch(`/api/requests/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus }),
  });
}

export async function deleteBloodRequest(id) {
  return apiFetch(`/api/requests/${id}`, {
    method: 'DELETE',
  });
}

// ─── Campus Events ──────────────────────────────────────────
export async function fetchCampusEvents({
  search = '',
  type = 'All',
  status = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (type && type !== 'All') params.set('type', type);
  if (status && status !== 'All') params.set('status', status);

  return apiFetch(`/api/camps?${params.toString()}`);
}

export async function createCampusEvent(eventData) {
  return apiFetch('/api/camps', {
    method: 'POST',
    body: JSON.stringify({
      title: eventData.title,
      type: eventData.type || 'Blood Donation',
      location: eventData.venue || eventData.location,
      venue: eventData.venue,
      event_date: eventData.date || eventData.event_date,
      start_time: eventData.startTime || eventData.start_time || '09:00 AM',
      end_time: eventData.endTime || eventData.end_time || '03:00 PM',
      time_slot: eventData.time_slot || `${eventData.startTime || '09:00 AM'} – ${eventData.endTime || '03:00 PM'}`,
      organizer: eventData.organizer,
      participants: Number(eventData.participants || 0),
      max_participants: Number(eventData.maxParticipants || eventData.max_participants || 100),
      target_units: Number(eventData.target_units || 50),
      collected_units: Number(eventData.collected_units || 0),
      description: eventData.description,
      contact_number: eventData.contactNumber || eventData.contact_number,
      registration_required: Boolean(eventData.registrationRequired),
      registration_deadline: eventData.registrationDeadline || eventData.registration_deadline,
      image_banner: eventData.imageBanner || eventData.image_banner,
      status: eventData.status || 'Upcoming',
    }),
  });
}

export async function updateCampusEvent(id, eventData) {
  return apiFetch(`/api/camps/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      title: eventData.title,
      type: eventData.type,
      location: eventData.venue || eventData.location,
      venue: eventData.venue,
      event_date: eventData.date || eventData.event_date,
      start_time: eventData.startTime || eventData.start_time,
      end_time: eventData.endTime || eventData.end_time,
      time_slot: eventData.time_slot || `${eventData.startTime || '09:00 AM'} – ${eventData.endTime || '03:00 PM'}`,
      organizer: eventData.organizer,
      participants: Number(eventData.participants || 0),
      max_participants: Number(eventData.maxParticipants || eventData.max_participants || 100),
      description: eventData.description,
      contact_number: eventData.contactNumber || eventData.contact_number,
      registration_required: Boolean(eventData.registrationRequired),
      registration_deadline: eventData.registrationDeadline || eventData.registration_deadline,
      image_banner: eventData.imageBanner || eventData.image_banner,
      status: eventData.status,
    }),
  });
}

export async function updateCampusEventStatus(id, newStatus) {
  return apiFetch(`/api/camps/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus }),
  });
}

export async function deleteCampusEvent(id) {
  return apiFetch(`/api/camps/${id}`, {
    method: 'DELETE',
  });
}

// ─── Hospitals ──────────────────────────────────────────────
export async function fetchHospitals({
  search = '',
  district = 'All',
  type = 'All',
  status = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (district && district !== 'All') params.set('district', district);
  if (type && type !== 'All') params.set('type', type);
  if (status && status !== 'All') params.set('status', status);

  return apiFetch(`/api/hospitals?${params.toString()}`);
}

export async function createHospital(hospData) {
  return apiFetch('/api/hospitals', {
    method: 'POST',
    body: JSON.stringify({
      name: hospData.name,
      type: hospData.type || 'Government',
      district: hospData.district || 'Kottayam',
      panchayat: hospData.panchayat,
      address: hospData.address,
      phone: hospData.phone,
      email: hospData.email,
      emergency_number: hospData.emergencyNumber || '108',
      latitude: hospData.latitude ? Number(hospData.latitude) : null,
      longitude: hospData.longitude ? Number(hospData.longitude) : null,
      services: Array.isArray(hospData.services) ? hospData.services.join(', ') : hospData.servicesInput || hospData.services,
      status: hospData.status || 'Active',
    }),
  });
}

export async function updateHospital(id, hospData) {
  return apiFetch(`/api/hospitals/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      name: hospData.name,
      type: hospData.type,
      district: hospData.district,
      panchayat: hospData.panchayat,
      address: hospData.address,
      phone: hospData.phone,
      email: hospData.email,
      emergency_number: hospData.emergencyNumber,
      latitude: hospData.latitude ? Number(hospData.latitude) : null,
      longitude: hospData.longitude ? Number(hospData.longitude) : null,
      services: Array.isArray(hospData.services) ? hospData.services.join(', ') : hospData.servicesInput || hospData.services,
      status: hospData.status,
    }),
  });
}

export async function deleteHospital(id) {
  return apiFetch(`/api/hospitals/${id}`, {
    method: 'DELETE',
  });
}

// ─── Users & Staff ──────────────────────────────────────────
export async function fetchAllUsers({
  search = '',
  role = 'All',
  status = 'All',
  district = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (role && role !== 'All') params.set('role', role);
  if (status && status !== 'All') params.set('status', status);
  if (district && district !== 'All') params.set('district', district);

  return apiFetch(`/api/users?${params.toString()}`);
}

export async function createUser(userData) {
  return apiFetch('/api/users', {
    method: 'POST',
    body: JSON.stringify({
      full_name: userData.name || userData.full_name,
      email: userData.email,
      phone_number: userData.phone || userData.phone_number,
      role: userData.role || 'Citizen',
      district: userData.district || 'Kottayam',
      panchayat: userData.panchayat,
      status: userData.status || 'Active',
      password: userData.password || 'password123',
    }),
  });
}

export async function updateUser(id, userData) {
  return apiFetch(`/api/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      full_name: userData.name || userData.full_name,
      email: userData.email,
      phone_number: userData.phone || userData.phone_number,
      role: userData.role,
      district: userData.district,
      panchayat: userData.panchayat,
      status: userData.status,
    }),
  });
}

export async function updateUserStatus(id, newStatus) {
  return apiFetch(`/api/users/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus }),
  });
}

export async function deleteUser(id) {
  return apiFetch(`/api/users/${id}`, {
    method: 'DELETE',
  });
}

// ─── Blood Donations ────────────────────────────────────────
export async function fetchDonations({
  search = '',
  bloodGroup = 'All',
  donationType = 'All',
  status = 'All',
  district = 'All',
} = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (bloodGroup && bloodGroup !== 'All') params.set('blood_group', bloodGroup);
  if (donationType && donationType !== 'All') params.set('donation_type', donationType);
  if (status && status !== 'All') params.set('status', status);
  if (district && district !== 'All') params.set('district', district);

  return apiFetch(`/api/donations?${params.toString()}`);
}

export async function createDonation(donData) {
  return apiFetch('/api/donations', {
    method: 'POST',
    body: JSON.stringify({
      donor_name: donData.donorName,
      blood_group: donData.bloodGroup,
      phone: donData.phone,
      email: donData.email,
      district: donData.district || 'Kottayam',
      address: donData.address,
      donation_date: donData.donationDate,
      donation_type: donData.donationType || 'Voluntary',
      units: Number(donData.unitsDonated || donData.units || 1),
      hospital: donData.hospital || 'Blood Bank',
      venue: donData.hospital || 'Blood Bank',
      status: donData.status || 'Completed',
      notes: donData.notes || '',
    }),
  });
}

export async function updateDonation(id, donData) {
  return apiFetch(`/api/donations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      donor_name: donData.donorName,
      blood_group: donData.bloodGroup,
      phone: donData.phone,
      email: donData.email,
      district: donData.district,
      address: donData.address,
      donation_date: donData.donationDate,
      donation_type: donData.donationType,
      units: Number(donData.unitsDonated || donData.units || 1),
      hospital: donData.hospital,
      venue: donData.hospital,
      status: donData.status,
      notes: donData.notes,
    }),
  });
}

export async function updateDonationStatus(id, newStatus) {
  return apiFetch(`/api/donations/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus }),
  });
}

export async function deleteDonation(id) {
  return apiFetch(`/api/donations/${id}`, {
    method: 'DELETE',
  });
}

// ─── Settings ───────────────────────────────────────────────
export async function fetchSettings() {
  return apiFetch('/api/settings');
}

export async function saveSettings(settingsData) {
  return apiFetch('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(settingsData),
  });
}

export async function updateProfileSettings(profileData) {
  return apiFetch('/api/settings/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData),
  });
}

export async function changePasswordApi(oldPassword, newPassword) {
  return apiFetch('/api/settings/change-password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

// ─── Reports & Analytics ────────────────────────────────────
export async function fetchReportsAnalytics(range = 'Last 30 Days', category = 'Overview') {
  return apiFetch(`/api/reports/analytics?range=${encodeURIComponent(range)}&category=${encodeURIComponent(category)}`);
}

export async function fetchActivityLogs(category = 'All', limit = 20) {
  return apiFetch(`/api/reports/activity-logs?category=${encodeURIComponent(category)}&limit=${limit}`);
}

export { getToken, clearToken, setToken };
