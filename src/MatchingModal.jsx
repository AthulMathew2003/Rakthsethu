import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Info,
  Navigation,
  Compass,
  RefreshCw
} from 'lucide-react';
import { matchDonorsDirect } from './api.js';

const CANONICAL_MAX_RADIUS_KM = 100.0;
const DEFAULT_RADIUS_KM = 25.0;
const RADIUS_OPTIONS = [5, 10, 25, 50, 75, 100];

export default function MatchingModal({ isOpen, onClose, request, userHospitalId }) {
  const [loading, setLoading] = useState(false);
  const [matchResult, setMatchResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  // Search parameters
  const [originMode, setOriginMode] = useState('HOSPITAL_ORIGIN'); // 'HOSPITAL_ORIGIN' | 'EXPLICIT_GPS' | 'DISTRICT_ONLY'
  const [radiusKm, setRadiusKm] = useState(DEFAULT_RADIUS_KM);
  const [includeFallback, setIncludeFallback] = useState(true);
  const [customLat, setCustomLat] = useState('');
  const [customLon, setCustomLon] = useState('');

  // Extract initial values from request
  const bloodGroup = request?.bloodGroup || request?.blood_group || 'O+';
  const district = request?.district || 'Kottayam';
  const panchayat = request?.location || request?.panchayat || '';
  const hospitalId = request?.hospitalId || request?.hospital_id || userHospitalId || null;
  const patientName = request?.patientName || request?.patient_name || 'Patient';
  const unitsRequired = request?.unitsRequired || request?.units_requested || 1;
  const requestId = request?.id || request?.dbId;

  // Initialize and load matches when modal opens
  const executeSearch = useCallback(async (overrideRadius, overrideFallback) => {
    setLoading(true);
    setErrorMessage('');
    setValidationErrors({});

    const activeRadius = overrideRadius !== undefined ? overrideRadius : radiusKm;
    const activeFallback = overrideFallback !== undefined ? overrideFallback : includeFallback;

    // Client-side validations
    const errors = {};

    // Validate Radius: strictly positive and <= CANONICAL_MAX_RADIUS_KM
    if (activeRadius === null || activeRadius === undefined || isNaN(activeRadius)) {
      errors.radius = 'Radius must be a valid numeric value.';
    } else if (Number(activeRadius) <= 0) {
      errors.radius = 'Search radius must be greater than 0 km.';
    } else if (Number(activeRadius) > CANONICAL_MAX_RADIUS_KM) {
      errors.radius = `Search radius cannot exceed ${CANONICAL_MAX_RADIUS_KM} km.`;
    }

    // Validate custom coordinates if in EXPLICIT_GPS mode
    let searchLat = null;
    let searchLon = null;
    if (originMode === 'EXPLICIT_GPS') {
      const latVal = parseFloat(customLat);
      const lonVal = parseFloat(customLon);

      if (customLat === '' || isNaN(latVal) || !isFinite(latVal)) {
        errors.lat = 'Valid latitude between -90 and 90 is required.';
      } else if (latVal < -90 || latVal > 90) {
        errors.lat = 'Latitude must be between -90 and 90 degrees.';
      }

      if (customLon === '' || isNaN(lonVal) || !isFinite(lonVal)) {
        errors.lon = 'Valid longitude between -180 and 180 is required.';
      } else if (lonVal < -180 || lonVal > 180) {
        errors.lon = 'Longitude must be between -180 and 180 degrees.';
      }

      searchLat = latVal;
      searchLon = lonVal;
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      setLoading(false);
      return;
    }

    try {
      const payload = {
        bloodGroup,
        district,
        panchayat: panchayat || null,
        requiredUnits: Number(unitsRequired) || 1,
        includeFallback: activeFallback,
        radiusKm: Number(activeRadius),
        limit: 50,
      };

      if (originMode === 'EXPLICIT_GPS') {
        payload.latitude = searchLat;
        payload.longitude = searchLon;
      } else if (originMode === 'HOSPITAL_ORIGIN' && hospitalId) {
        payload.hospitalId = Number(hospitalId);
      }
      // If DISTRICT_ONLY, we pass no coordinates and no hospitalId for origin derivation

      const data = await matchDonorsDirect(payload);
      setMatchResult(data);
    } catch (err) {
      console.error('Failed to load matching donors:', err);
      setErrorMessage(err.message || 'Failed to find matching donors for this request.');
    } finally {
      setLoading(false);
    }
  }, [
    bloodGroup,
    district,
    panchayat,
    hospitalId,
    unitsRequired,
    originMode,
    radiusKm,
    includeFallback,
    customLat,
    customLon,
  ]);

  useEffect(() => {
    if (isOpen) {
      executeSearch();
    }
  }, [isOpen, originMode, executeSearch]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ zIndex: 1100 }}>
      <div className="modal-content-card" style={{ maxWidth: '920px', width: '92%', maxHeight: '92vh', overflowY: 'auto' }}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: '#FFE4E6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#E11D48',
              flexShrink: 0
            }}>
              <Compass size={22} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#0F172A', fontWeight: 700 }}>
                Proximity Donor Matching {requestId ? `(Request #${requestId})` : ''}
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: '#64748B' }}>
                Recipient: <strong>{patientName}</strong> | Group: <strong style={{ color: '#E11D48' }}>{bloodGroup}</strong> | Units: <strong>{unitsRequired}</strong> | District: <strong>{district}</strong>
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Clinical Disclaimer Banner */}
        <div style={{
          margin: '16px 24px 0',
          padding: '10px 14px',
          backgroundColor: '#EFF6FF',
          border: '1px solid #BFDBFE',
          borderRadius: '8px',
          color: '#1E40AF',
          fontSize: '0.83rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          lineHeight: '1.4'
        }}>
          <Info size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#2563EB' }} />
          <div>
            <strong>Medical Notice:</strong> Proximity matching evaluates ABO/Rh compatibility, 90-day cooldown compliance, and straight-line geographic proximity based on registered donor coordinates. <em>Distances are straight-line estimates and do not represent travel or driving time. Matching an eligible donor does not imply confirmed donor availability.</em>
          </div>
        </div>

        {/* Search & Spatial Controls Panel */}
        <div style={{
          margin: '16px 24px 0',
          padding: '16px',
          backgroundColor: '#F8FAFC',
          borderRadius: '10px',
          border: '1px solid #E2E8F0',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}>
          {/* Origin Mode Selection */}
          <div>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', display: 'block', marginBottom: '6px' }}>
              Spatial Origin Mode:
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              <button
                type="button"
                className={`menu-btn ${originMode === 'HOSPITAL_ORIGIN' ? 'active' : ''}`}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  border: originMode === 'HOSPITAL_ORIGIN' ? '1px solid #E11D48' : '1px solid #CBD5E1',
                  backgroundColor: originMode === 'HOSPITAL_ORIGIN' ? '#FFE4E6' : '#FFFFFF',
                  color: originMode === 'HOSPITAL_ORIGIN' ? '#BE123C' : '#475569',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
                onClick={() => setOriginMode('HOSPITAL_ORIGIN')}
              >
                🏥 Hospital Registered Location
              </button>

              <button
                type="button"
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  border: originMode === 'EXPLICIT_GPS' ? '1px solid #E11D48' : '1px solid #CBD5E1',
                  backgroundColor: originMode === 'EXPLICIT_GPS' ? '#FFE4E6' : '#FFFFFF',
                  color: originMode === 'EXPLICIT_GPS' ? '#BE123C' : '#475569',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
                onClick={() => setOriginMode('EXPLICIT_GPS')}
              >
                📍 Custom GPS Coordinates
              </button>

              <button
                type="button"
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.82rem',
                  border: originMode === 'DISTRICT_ONLY' ? '1px solid #E11D48' : '1px solid #CBD5E1',
                  backgroundColor: originMode === 'DISTRICT_ONLY' ? '#FFE4E6' : '#FFFFFF',
                  color: originMode === 'DISTRICT_ONLY' ? '#BE123C' : '#475569',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
                onClick={() => setOriginMode('DISTRICT_ONLY')}
              >
                🏛️ District Only (No GPS)
              </button>
            </div>
          </div>

          {/* Custom Coordinate Inputs (Visible if EXPLICIT_GPS mode) */}
          {originMode === 'EXPLICIT_GPS' && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              padding: '12px',
              backgroundColor: '#FFFFFF',
              borderRadius: '8px',
              border: '1px solid #E2E8F0'
            }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Origin Latitude (-90 to 90) *
                </label>
                <input
                  type="number"
                  step="0.0001"
                  placeholder="e.g. 9.5916"
                  value={customLat}
                  onChange={(e) => setCustomLat(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: validationErrors.lat ? '1px solid #EF4444' : '1px solid #CBD5E1',
                    fontSize: '0.85rem'
                  }}
                />
                {validationErrors.lat && (
                  <span style={{ color: '#EF4444', fontSize: '0.75rem', marginTop: '2px', display: 'block' }}>
                    {validationErrors.lat}
                  </span>
                )}
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Origin Longitude (-180 to 180) *
                </label>
                <input
                  type="number"
                  step="0.0001"
                  placeholder="e.g. 76.5222"
                  value={customLon}
                  onChange={(e) => setCustomLon(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: validationErrors.lon ? '1px solid #EF4444' : '1px solid #CBD5E1',
                    fontSize: '0.85rem'
                  }}
                />
                {validationErrors.lon && (
                  <span style={{ color: '#EF4444', fontSize: '0.75rem', marginTop: '2px', display: 'block' }}>
                    {validationErrors.lon}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Radius & Fallback Controls (Visible if GPS modes) */}
          {originMode !== 'DISTRICT_ONLY' && (
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
              paddingTop: '6px',
              borderTop: '1px solid #E2E8F0'
            }}>
              {/* Radius Options */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>
                  Search Radius:
                </span>
                {RADIUS_OPTIONS.map((rad) => (
                  <button
                    key={rad}
                    type="button"
                    style={{
                      padding: '4px 10px',
                      borderRadius: '16px',
                      fontSize: '0.8rem',
                      border: radiusKm === rad ? '1px solid #059669' : '1px solid #CBD5E1',
                      backgroundColor: radiusKm === rad ? '#ECFDF5' : '#FFFFFF',
                      color: radiusKm === rad ? '#065F46' : '#475569',
                      fontWeight: radiusKm === rad ? 700 : 500,
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      setRadiusKm(rad);
                      executeSearch(rad, includeFallback);
                    }}
                  >
                    {rad} km {rad === DEFAULT_RADIUS_KM ? '(Default)' : ''} {rad === CANONICAL_MAX_RADIUS_KM ? '(Max)' : ''}
                  </button>
                ))}
              </div>

              {/* Include Fallback Checkbox */}
              <label style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.85rem',
                color: '#334155',
                cursor: 'pointer',
                fontWeight: 500
              }}>
                <input
                  type="checkbox"
                  checked={includeFallback}
                  onChange={(e) => {
                    const nextVal = e.target.checked;
                    setIncludeFallback(nextVal);
                    executeSearch(radiusKm, nextVal);
                  }}
                  style={{ width: '16px', height: '16px', accentColor: '#E11D48' }}
                />
                Include District Fallback Donors (without GPS)
              </label>
            </div>
          )}

          {/* Action Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button
              type="button"
              className="modal-primary-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 16px',
                fontSize: '0.85rem'
              }}
              onClick={() => executeSearch()}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? 'spinner' : ''} />
              {loading ? 'Evaluating...' : 'Apply & Search'}
            </button>
          </div>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div style={{
            margin: '16px 24px 0',
            padding: '12px 16px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            color: '#DC2626',
            fontSize: '0.88rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Main Body */}
        <div style={{ padding: '20px 24px' }}>
          {loading && (
            <div style={{ padding: '48px 0', textAlign: 'center', color: '#64748B' }}>
              <Loader2 className="spinner" size={32} style={{ margin: '0 auto 12px', display: 'block', color: '#E11D48' }} />
              <p style={{ margin: 0, fontSize: '0.95rem' }}>Evaluating PostGIS spatial proximity and donor eligibility...</p>
            </div>
          )}

          {!loading && matchResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {/* Origin & Matching Result Notice Banner */}
              {matchResult.origin_type === 'DISTRICT_DEFAULT' ? (
                <div style={{
                  padding: '10px 14px',
                  backgroundColor: '#FFFBEB',
                  border: '1px solid #FDE68A',
                  borderRadius: '8px',
                  color: '#92400E',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <Info size={18} style={{ color: '#D97706', flexShrink: 0 }} />
                  <span>
                    <strong>Location-based proximity matching unavailable:</strong> The selected hospital or origin has no registered GPS coordinates. Showing standard district-level fallback matches for <strong>{matchResult.district}</strong>.
                  </span>
                </div>
              ) : (
                <div style={{
                  padding: '10px 14px',
                  backgroundColor: '#ECFDF5',
                  border: '1px solid #A7F3D0',
                  borderRadius: '8px',
                  color: '#065F46',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <Navigation size={18} style={{ color: '#059669', flexShrink: 0 }} />
                  <span>
                    <strong>Proximity Matching Active:</strong> Evaluated donors within a <strong>{matchResult.radius_km} km radius</strong> of the {matchResult.origin_type === 'HOSPITAL_LOCATION' ? 'hospital' : 'specified'} coordinates.
                  </span>
                </div>
              )}

              {/* Summary Metrics Bar */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                backgroundColor: '#F8FAFC',
                borderRadius: '8px',
                border: '1px solid #E2E8F0',
                fontSize: '0.88rem'
              }}>
                <div>
                  <span style={{ color: '#64748B' }}>Compatible Blood Groups: </span>
                  <span style={{ fontWeight: 700, color: '#0F172A' }}>
                    {matchResult.compatible_blood_groups?.join(', ') || 'None'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>Eligible Donors Found: </span>
                  <strong style={{ color: '#059669', fontSize: '1.05rem' }}>
                    {matchResult.total_eligible_found} Donors
                  </strong>
                </div>
              </div>

              {/* Ranked Matches Table */}
              <div>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', color: '#334155' }}>
                  Ranked Eligible Candidates (Tier 1 Proximity followed by Tier 2 District Fallback):
                </h4>
                <div style={{ maxHeight: '360px', overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                    <thead style={{ backgroundColor: '#F1F5F9', position: 'sticky', top: 0, zIndex: 1 }}>
                      <tr>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Donor Code</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Donor Name</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Group</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Distance & Match Type</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Location</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Last Donation</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Eligibility</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Match Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {matchResult.items?.length > 0 ? (
                        matchResult.items.map((donor) => {
                          const isProximity = donor.match_category === 'PROXIMITY' && donor.distance_km !== null;
                          return (
                            <tr key={donor.donor_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                              <td style={{ padding: '10px 12px', fontWeight: 600, color: '#334155' }}>
                                {donor.donor_code}
                              </td>
                              <td style={{ padding: '10px 12px', fontWeight: 600, color: '#0F172A' }}>
                                {donor.full_name}
                              </td>
                              <td style={{ padding: '10px 12px' }}>
                                <span style={{
                                  padding: '2px 8px',
                                  borderRadius: '12px',
                                  backgroundColor: '#FFE4E6',
                                  color: '#BE123C',
                                  fontWeight: 700,
                                  fontSize: '0.78rem'
                                }}>
                                  {donor.blood_group}
                                </span>
                              </td>
                              {/* Distance & Match Type Pill */}
                              <td style={{ padding: '10px 12px' }}>
                                {isProximity ? (
                                  <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '2px' }}>
                                    <span style={{
                                      padding: '2px 8px',
                                      borderRadius: '10px',
                                      backgroundColor: '#ECFDF5',
                                      color: '#065F46',
                                      fontWeight: 700,
                                      fontSize: '0.78rem',
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: '4px'
                                    }}>
                                      📍 {donor.distance_km} km away
                                    </span>
                                    <span style={{ fontSize: '0.7rem', color: '#64748B' }}>
                                      Straight-line distance
                                    </span>
                                  </div>
                                ) : (
                                  <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '2px' }}>
                                    <span style={{
                                      padding: '2px 8px',
                                      borderRadius: '10px',
                                      backgroundColor: '#F1F5F9',
                                      color: '#475569',
                                      fontWeight: 600,
                                      fontSize: '0.78rem',
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: '4px'
                                    }}>
                                      🏛️ Distance unknown
                                    </span>
                                    <span style={{ fontSize: '0.7rem', color: '#64748B' }}>
                                      District fallback (No GPS)
                                    </span>
                                  </div>
                                )}
                              </td>
                              <td style={{ padding: '10px 12px', color: '#475569' }}>
                                {donor.panchayat ? `${donor.panchayat}, ${donor.district}` : donor.district}
                              </td>
                              <td style={{ padding: '10px 12px', color: '#64748B' }}>
                                {donor.last_donation_date ? (
                                  <span>{donor.last_donation_date} ({donor.days_since_last_donation}d ago)</span>
                                ) : (
                                  <span style={{ color: '#059669', fontWeight: 500 }}>First Time / Never</span>
                                )}
                              </td>
                              <td style={{ padding: '10px 12px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  color: '#059669',
                                  fontWeight: 600,
                                  fontSize: '0.78rem'
                                }}>
                                  <CheckCircle2 size={14} /> Ready
                                </span>
                              </td>
                              <td style={{ padding: '10px 12px', color: '#64748B', fontSize: '0.8rem' }}>
                                {donor.match_reason}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan="8" style={{ padding: '32px 16px', textAlign: 'center', color: '#94A3B8' }}>
                            No eligible donors found matching compatibility and cooldown criteria within the specified search parameters.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Footer */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="modal-primary-btn"
                  onClick={onClose}
                >
                  Close Matching Results
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
