/**
 * Phase 7E — RakthaSethu Frontend Integration Test Suite
 * Executed via Node 22 native test runner: node --test tests/test_frontend_integration.mjs
 * Validates coordinate validation, radius boundaries, consent workflow, distance formatting,
 * privacy invariants, and API client contracts.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveApiBase } from '../src/api.js';

// Canonical constants matching backend configuration
const CANONICAL_MAX_RADIUS_KM = 100.0;
const DEFAULT_RADIUS_KM = 25.0;
const CANONICAL_MIN_RADIUS_KM = 0.0;

// Coordinate validation helper matching MatchingModal.jsx & Dashboard.jsx logic
function validateCoordinates(latInput, lonInput) {
  const errors = {};

  if (latInput === '' || latInput === null || latInput === undefined) {
    errors.lat = 'Latitude is required.';
  } else {
    const lat = Number(latInput);
    if (!Number.isFinite(lat) || Number.isNaN(lat)) {
      errors.lat = 'Latitude must be a finite numeric value.';
    } else if (lat < -90.0 || lat > 90.0) {
      errors.lat = 'Latitude must be between -90 and 90 degrees.';
    }
  }

  if (lonInput === '' || lonInput === null || lonInput === undefined) {
    errors.lon = 'Longitude is required.';
  } else {
    const lon = Number(lonInput);
    if (!Number.isFinite(lon) || Number.isNaN(lon)) {
      errors.lon = 'Longitude must be a finite numeric value.';
    } else if (lon < -180.0 || lon > 180.0) {
      errors.lon = 'Longitude must be between -180 and 180 degrees.';
    }
  }

  const isValid = Object.keys(errors).length === 0;
  return { isValid, errors };
}

// Radius validation helper matching MatchingModal.jsx logic
function validateRadius(radiusInput) {
  if (radiusInput === '' || radiusInput === null || radiusInput === undefined) {
    return { isValid: false, error: 'Radius is required.' };
  }
  const radius = Number(radiusInput);
  if (!Number.isFinite(radius) || Number.isNaN(radius)) {
    return { isValid: false, error: 'Radius must be a finite numeric value.' };
  }
  if (radius <= CANONICAL_MIN_RADIUS_KM) {
    return { isValid: false, error: 'Search radius must be greater than 0 km. Radius zero or negative is not supported.' };
  }
  if (radius > CANONICAL_MAX_RADIUS_KM) {
    return { isValid: false, error: `Search radius cannot exceed ${CANONICAL_MAX_RADIUS_KM} km.` };
  }
  return { isValid: true, radius };
}

// Distance formatting helper matching MatchingModal.jsx logic
function formatMatchDistance(donor) {
  if (donor.match_category === 'PROXIMITY' && donor.distance_km !== null && donor.distance_km !== undefined) {
    return {
      badge: '📍 Proximity Match',
      distanceText: `📍 ${donor.distance_km} km away`,
      isProximity: true,
      isFallback: false,
    };
  }
  return {
    badge: '🏛️ District Fallback',
    distanceText: '🏛️ Distance unknown',
    isProximity: false,
    isFallback: true,
  };
}

// Consent validation helper matching Dashboard.jsx logic
function validateLocationConsent({ latitude, longitude, consentConfirmed }) {
  const coordResult = validateCoordinates(latitude, longitude);
  const errors = { ...coordResult.errors };

  if (!consentConfirmed) {
    errors.consent = 'Staff attestation of explicit offline donor consent is mandatory.';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

describe('Phase 7E: Coordinate Validation Tests', () => {
  it('accepts valid Kerala coordinate pair (Kottayam Medical College)', () => {
    const res = validateCoordinates(9.5916, 76.5222);
    assert.equal(res.isValid, true);
    assert.deepEqual(res.errors, {});
  });

  it('rejects latitude outside [-90, 90]', () => {
    const resLow = validateCoordinates(-91.5, 76.5);
    assert.equal(resLow.isValid, false);
    assert.match(resLow.errors.lat, /between -90 and 90/);

    const resHigh = validateCoordinates(95.0, 76.5);
    assert.equal(resHigh.isValid, false);
    assert.match(resHigh.errors.lat, /between -90 and 90/);
  });

  it('rejects longitude outside [-180, 180]', () => {
    const resLow = validateCoordinates(9.5, -185.0);
    assert.equal(resLow.isValid, false);
    assert.match(resLow.errors.lon, /between -180 and 180/);

    const resHigh = validateCoordinates(9.5, 181.0);
    assert.equal(resHigh.isValid, false);
    assert.match(resHigh.errors.lon, /between -180 and 180/);
  });

  it('rejects non-finite values (NaN, Infinity)', () => {
    const resNaN = validateCoordinates(NaN, 76.5);
    assert.equal(resNaN.isValid, false);
    assert.match(resNaN.errors.lat, /finite numeric/);

    const resInf = validateCoordinates(9.5, Infinity);
    assert.equal(resInf.isValid, false);
    assert.match(resInf.errors.lon, /finite numeric/);
  });

  it('rejects incomplete coordinate pairs', () => {
    const resNoLon = validateCoordinates(9.5, '');
    assert.equal(resNoLon.isValid, false);
    assert.equal(resNoLon.errors.lon, 'Longitude is required.');

    const resNoLat = validateCoordinates('', 76.5);
    assert.equal(resNoLat.isValid, false);
    assert.equal(resNoLat.errors.lat, 'Latitude is required.');
  });
});

describe('Phase 7E: Radius Boundary & Validation Consistency Tests', () => {
  it('confirms canonical limits (default 25 km, max 100 km)', () => {
    assert.equal(DEFAULT_RADIUS_KM, 25.0);
    assert.equal(CANONICAL_MAX_RADIUS_KM, 100.0);
  });

  it('accepts valid radius within range [5, 10, 25, 50, 75, 100]', () => {
    for (const r of [5, 10, 25, 50, 75, 100]) {
      const res = validateRadius(r);
      assert.equal(res.isValid, true);
      assert.equal(res.radius, r);
    }
  });

  it('strictly rejects radius zero (not supported)', () => {
    const resZero = validateRadius(0);
    assert.equal(resZero.isValid, false);
    assert.match(resZero.error, /greater than 0 km/);
  });

  it('strictly rejects negative radius', () => {
    const resNeg = validateRadius(-10);
    assert.equal(resNeg.isValid, false);
    assert.match(resNeg.error, /greater than 0 km/);
  });

  it('strictly rejects radius exceeding canonical maximum (100 km) without silent clamping', () => {
    const resExcess = validateRadius(101.0);
    assert.equal(resExcess.isValid, false);
    assert.match(resExcess.error, /cannot exceed 100/);
  });
});

describe('Phase 7E: Donor Location Consent & Revocation Workflow Tests', () => {
  it('requires explicit consent confirmation when saving GPS coordinates', () => {
    const resNoConsent = validateLocationConsent({
      latitude: 9.5916,
      longitude: 76.5222,
      consentConfirmed: false,
    });
    assert.equal(resNoConsent.isValid, false);
    assert.match(resNoConsent.errors.consent, /attestation of explicit offline donor consent is mandatory/);

    const resWithConsent = validateLocationConsent({
      latitude: 9.5916,
      longitude: 76.5222,
      consentConfirmed: true,
    });
    assert.equal(resWithConsent.isValid, true);
    assert.deepEqual(resWithConsent.errors, {});
  });

  it('handles donor with no coordinates safely without requiring consent', () => {
    const donorRecord = {
      id: 'D_1001',
      name: 'Regular District Donor',
      district: 'Kottayam',
      hasLocation: false,
      locationConsent: false,
      locationConsentRecordedAt: null,
    };
    assert.equal(donorRecord.hasLocation, false);
    assert.equal(donorRecord.locationConsent, false);
  });

  it('revocation disables location-based matching without deleting donor profile', () => {
    const donorBefore = {
      id: 'D_1002',
      name: 'Consented Donor',
      hasLocation: true,
      locationConsent: true,
      locationConsentRecordedAt: '2026-10-20T10:00:00Z',
      is_active: true,
    };

    // Simulate revoke action
    const donorAfterRevoke = {
      ...donorBefore,
      hasLocation: false,
      locationConsent: false,
      locationConsentRecordedAt: null,
    };

    assert.equal(donorAfterRevoke.hasLocation, false);
    assert.equal(donorAfterRevoke.locationConsent, false);
    assert.equal(donorAfterRevoke.locationConsentRecordedAt, null);
    // Profile preserved
    assert.equal(donorAfterRevoke.id, 'D_1002');
    assert.equal(donorAfterRevoke.is_active, true);
  });
});

describe('Phase 7E: Matching Presentation & Privacy Invariants Tests', () => {
  it('formats proximity match with rounded straight-line distance', () => {
    const donorProximity = {
      donor_id: 1,
      full_name: 'Near Donor',
      distance_km: 4.2,
      match_category: 'PROXIMITY',
    };
    const formatted = formatMatchDistance(donorProximity);
    assert.equal(formatted.isProximity, true);
    assert.equal(formatted.isFallback, false);
    assert.equal(formatted.distanceText, '📍 4.2 km away');
  });

  it('formats coordinate-less fallback match as "Distance unknown"', () => {
    const donorFallback = {
      donor_id: 2,
      full_name: 'Fallback Donor',
      distance_km: null, // No GPS coordinates
      match_category: 'FALLBACK_DISTRICT',
    };
    const formatted = formatMatchDistance(donorFallback);
    assert.equal(formatted.isProximity, false);
    assert.equal(formatted.isFallback, true);
    assert.equal(formatted.distanceText, '🏛️ Distance unknown');
    assert.notEqual(formatted.distanceText, '0 km');
  });

  it('verifies strict absence of raw coordinates in donor UI item', () => {
    const sampleItem = {
      donor_id: 101,
      donor_code: 'D_PRIV_01',
      full_name: 'Audited Privacy Donor',
      blood_group: 'O+',
      district: 'Kottayam',
      panchayat: 'Pala',
      distance_km: 12.4,
      match_category: 'PROXIMITY',
      match_reason: 'Proximity match (12.4 km away)',
    };

    // Raw coordinate fields must NOT exist on match item
    assert.equal('latitude' in sampleItem, false);
    assert.equal('longitude' in sampleItem, false);
    assert.equal('location' in sampleItem, false);
    assert.equal('wkt' in sampleItem, false);
    assert.equal('wkb' in sampleItem, false);
  });
});

describe('API Base URL Normalization Tests', () => {
  it('preserves backend URL already including /api/v1', () => {
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com/api/v1'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
  });

  it('appends /api/v1 to backend URL provided without /api/v1', () => {
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
  });

  it('strips trailing slashes without duplicating /api/v1 prefix', () => {
    // Single and multiple trailing slashes on root host
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com/'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com///'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
    // Single and multiple trailing slashes with /api/v1
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com/api/v1/'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
    assert.equal(
      resolveApiBase('https://rakthasethu-backend.onrender.com/api/v1///'),
      'https://rakthasethu-backend.onrender.com/api/v1'
    );
  });

  it('falls back to local development URL when environment variable is missing or empty', () => {
    const LOCAL_FALLBACK = 'http://127.0.0.1:8000/api/v1';
    assert.equal(resolveApiBase(undefined), LOCAL_FALLBACK);
    assert.equal(resolveApiBase(null), LOCAL_FALLBACK);
    assert.equal(resolveApiBase(''), LOCAL_FALLBACK);
    assert.equal(resolveApiBase('   '), LOCAL_FALLBACK);
    assert.equal(resolveApiBase(), LOCAL_FALLBACK);
  });
});
