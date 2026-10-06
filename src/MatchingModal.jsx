import React, { useState, useEffect } from 'react';
import {
  Users,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Droplet,
  MapPin,
  Calendar,
  ShieldCheck,
  Info
} from 'lucide-react';
import { fetchRequestMatches } from './api.js';

export default function MatchingModal({ isOpen, onClose, request, onScheduleDonation }) {
  const [loading, setLoading] = useState(false);
  const [matchResult, setMatchResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (isOpen && request?.dbId) {
      loadMatches(request.dbId);
    } else if (isOpen && request?.id && !request?.dbId) {
      loadMatches(request.id);
    }
  }, [isOpen, request]);

  const loadMatches = async (reqId) => {
    setLoading(true);
    setErrorMessage('');
    setMatchResult(null);

    try {
      const data = await fetchRequestMatches(reqId);
      setMatchResult(data);
    } catch (err) {
      console.error('Failed to load matching donors:', err);
      setErrorMessage(err.message || 'Failed to find matching donors for this request.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ zIndex: 1100 }}>
      <div className="modal-content-card" style={{ maxWidth: '850px', width: '90%', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: '#FFE4E6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#E11D48'
            }}>
              <Droplet size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#0F172A' }}>
                Eligible Donors for Request #{request?.id || request?.dbId}
              </h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748B' }}>
                Recipient: <strong>{request?.patientName}</strong> | Group: <strong style={{ color: '#E11D48' }}>{request?.bloodGroup}</strong> | Units: <strong>{request?.unitsRequired}</strong> | District: <strong>{request?.district}</strong>
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Clinical / Legal Disclaimer Banner */}
        <div style={{
          margin: '16px 24px 0',
          padding: '12px 16px',
          backgroundColor: '#EFF6FF',
          border: '1px solid #BFDBFE',
          borderRadius: '8px',
          color: '#1E40AF',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          lineHeight: '1.4'
        }}>
          <Info size={20} style={{ flexShrink: 0, marginTop: '2px', color: '#2563EB' }} />
          <div>
            <strong>Medical Notice:</strong> Donor matching reflects ABO/Rh compatibility and 90-day cooldown compliance based on records in the system. <em>Matching an eligible donor does NOT mean the donor has agreed to donate.</em>
          </div>
        </div>

        {errorMessage && (
          <div style={{
            margin: '16px 24px 0',
            padding: '12px 16px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            color: '#DC2626',
            fontSize: '0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        <div style={{ padding: '20px 24px' }}>
          {loading && (
            <div style={{ padding: '48px 0', textAlign: 'center', color: '#64748B' }}>
              <Loader2 className="spinner" size={32} style={{ margin: '0 auto 12px', display: 'block', color: '#E11D48' }} />
              <p style={{ margin: 0, fontSize: '0.95rem' }}>Evaluating ABO/Rh compatibility and donor cooldown status...</p>
            </div>
          )}

          {!loading && matchResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Summary Metrics */}
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
                  <span style={{ color: '#64748B' }}>Compatible Groups: </span>
                  <span style={{ fontWeight: 600, color: '#0F172A' }}>
                    {matchResult.compatible_blood_groups?.join(', ') || 'None'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>Eligible Donors in {matchResult.district}: </span>
                  <strong style={{ color: '#059669', fontSize: '1.05rem' }}>
                    {matchResult.total_eligible_found} Found
                  </strong>
                </div>
              </div>

              {/* Matched Donors Table */}
              <div>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', color: '#334155' }}>Ranked Eligible Donors:</h4>
                <div style={{ maxHeight: '350px', overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                    <thead style={{ backgroundColor: '#F1F5F9', position: 'sticky', top: 0, zIndex: 1 }}>
                      <tr>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Donor Code</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Donor Name</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Group</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Location</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Last Donation</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Eligibility Status</th>
                        <th style={{ padding: '10px 12px', borderBottom: '1px solid #E2E8F0' }}>Match Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {matchResult.items?.length > 0 ? (
                        matchResult.items.map((donor) => (
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
                        ))
                      ) : (
                        <tr>
                          <td colSpan="7" style={{ padding: '32px 16px', textAlign: 'center', color: '#94A3B8' }}>
                            No eligible donors found matching compatibility and cooldown criteria in {matchResult.district}.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

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
