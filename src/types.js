/**
 * Rakthasethu Frontend Constants and Enums
 * Mirrors backend PostgreSQL ENUM types and system standards.
 */

export const BLOOD_GROUPS = [
  'A+',
  'A-',
  'B+',
  'B-',
  'AB+',
  'AB-',
  'O+',
  'O-'
];

export const DISTRICTS = [
  'Kottayam',
  'Ernakulam',
  'Kozhikode',
  'Thiruvananthapuram',
  'Alappuzha',
  'Idukki',
  'Kannur',
  'Kasaragod',
  'Kollam',
  'Malappuram',
  'Palakkad',
  'Pathanamthitta',
  'Thrissur',
  'Wayanad'
];

export const USER_ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  HOSPITAL_ADMIN: 'HOSPITAL_ADMIN',
  STAFF: 'STAFF',
  CITIZEN: 'CITIZEN'
};

export const REQUEST_STATUSES = {
  PENDING: 'PENDING',
  IN_PROGRESS: 'IN_PROGRESS',
  FULFILLED: 'FULFILLED',
  CANCELLED: 'CANCELLED',
  REJECTED: 'REJECTED'
};

export const REQUEST_URGENCY = {
  NORMAL: 'NORMAL',
  URGENT: 'URGENT',
  CRITICAL: 'CRITICAL'
};

export const DONATION_STATUSES = {
  SCHEDULED: 'SCHEDULED',
  COMPLETED: 'COMPLETED',
  CANCELLED: 'CANCELLED',
  REJECTED: 'REJECTED'
};

export const HOSPITAL_TYPES = [
  'Government',
  'Private',
  'Cooperative',
  'Medical College',
  'Blood Bank'
];

export const DONATION_TYPES = [
  'Whole Blood',
  'Platelets',
  'Plasma',
  'Voluntary',
  'Replacement'
];
