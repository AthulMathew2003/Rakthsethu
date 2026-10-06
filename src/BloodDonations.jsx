import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  Droplet,
  Heart,
  Calendar,
  Phone,
  ShieldAlert,
  MapPin,
  FileText,
  AlertTriangle
} from 'lucide-react';
import { DISTRICTS, BLOOD_GROUPS, DONATION_STATUSES, DONATION_TYPES } from './types.js';

const ALL_STATUSES = ['Scheduled', 'Completed', 'Cancelled', 'Rejected'];

// Helper for allowed donation status transitions
function getAllowedDonationStatuses(currentStatus) {
  const norm = (currentStatus || 'Scheduled').toLowerCase();
  if (norm === 'scheduled') {
    return ['Scheduled', 'Completed', 'Cancelled', 'Rejected'];
  }
  // Terminal states cannot transition
  return [currentStatus];
}

// Helper to get status class for badge styling
function getStatusStyles(status) {
  const norm = (status || '').toLowerCase();
  switch (norm) {
    case 'scheduled':
      return { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' }; // blue
    case 'completed':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // green
    case 'cancelled':
      return { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1' }; // slate
    case 'rejected':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

export default function BloodDonationsPage({
  donations,
  onAddDonation,
  onEditDonation,
  onDeleteDonation,
  onStatusChange,
  donors = [],
  hospitals = []
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [bloodGroupFilter, setBloodGroupFilter] = useState('All');
  const [donationTypeFilter, setDonationTypeFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal states
  const [isAddingDonation, setIsAddingDonation] = useState(false);
  const [viewingDonation, setViewingDonation] = useState(null);
  const [editingDonation, setEditingDonation] = useState(null);
  const [deletingDonationId, setDeletingDonationId] = useState(null);

  // Form State
  const [donationForm, setDonationForm] = useState({
    donorId: '',
    donorName: '',
    bloodGroup: 'O+',
    phone: '',
    email: '',
    district: 'Kottayam',
    address: '',
    donationDate: new Date().toISOString().split('T')[0],
    donationType: 'Voluntary',
    unitsDonated: 1,
    hospital: '',
    hospitalId: '',
    status: 'Completed',
    notes: ''
  });

  const resetForm = () => {
    setDonationForm({
      donorId: donors[0]?.dbId || donors[0]?.id || '',
      donorName: donors[0]?.name || '',
      bloodGroup: donors[0]?.group || 'O+',
      phone: donors[0]?.phone || '',
      email: donors[0]?.email || '',
      district: donors[0]?.location || 'Kottayam',
      address: '',
      donationDate: new Date().toISOString().split('T')[0],
      donationType: 'Voluntary',
      unitsDonated: 1,
      hospital: hospitals[0]?.name || 'District Blood Bank',
      hospitalId: hospitals[0]?.dbId || hospitals[0]?.id || '',
      status: 'Completed',
      notes: ''
    });
  };

  const handleOpenAddModal = () => {
    resetForm();
    setIsAddingDonation(true);
  };

  const handleOpenEditModal = (don) => {
    setDonationForm({
      donorId: don.donorId || don.dbId || '',
      donorName: don.donorName,
      bloodGroup: don.bloodGroup,
      phone: don.phone,
      email: don.email || '',
      district: don.district,
      address: don.address || '',
      donationDate: don.donationDate,
      donationType: don.donationType || 'Voluntary',
      unitsDonated: don.unitsDonated || 1,
      hospital: don.hospital || 'District Blood Bank',
      hospitalId: don.hospitalId || '',
      status: don.status || 'Completed',
      notes: don.notes || ''
    });
    setEditingDonation(don);
  };

  const handleSaveDonationSubmit = (e) => {
    e.preventDefault();
    if (
      !donationForm.donationDate ||
      !donationForm.unitsDonated
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    if (donationForm.status === 'Completed' && donationForm.donationDate > todayStr) {
      alert('Completed donations cannot be recorded with a future date. Please select today or a past date, or set status to Scheduled.');
      return;
    }

    const donationData = {
      donor_id: donationForm.donorId ? parseInt(donationForm.donorId, 10) : undefined,
      donorName: donationForm.donorName,
      bloodGroup: donationForm.bloodGroup,
      phone: donationForm.phone,
      email: donationForm.email,
      district: donationForm.district,
      address: donationForm.address,
      donation_date: donationForm.donationDate,
      donation_type: donationForm.donationType,
      units_donated: parseInt(donationForm.unitsDonated, 10),
      hospital_id: donationForm.hospitalId ? parseInt(donationForm.hospitalId, 10) : undefined,
      hospital: donationForm.hospital,
      status: donationForm.status.toUpperCase(),
      notes: donationForm.notes
    };

    if (editingDonation) {
      onEditDonation({
        ...donationData,
        id: editingDonation.id,
        dbId: editingDonation.dbId
      });
      setEditingDonation(null);
    } else {
      onAddDonation(donationData);
      setIsAddingDonation(false);
    }
    resetForm();
  };

  const handleDeleteDonationConfirm = () => {
    if (deletingDonationId) {
      onDeleteDonation(deletingDonationId);
      setDeletingDonationId(null);

      const filtered = filteredDonations();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // Client-side filtering logic
  const filteredDonations = () => {
    return donations.filter((don) => {
      const matchesSearch =
        (don.donorName || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (don.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (don.phone || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (don.bloodGroup || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (don.hospital || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (don.district || '').toLowerCase().includes(searchQuery.toLowerCase());

      const matchesBloodGroup = bloodGroupFilter === 'All' || don.bloodGroup === bloodGroupFilter;
      const matchesDonationType = donationTypeFilter === 'All' || don.donationType === donationTypeFilter;
      const matchesStatus = statusFilter === 'All' || (don.status || '').toLowerCase() === statusFilter.toLowerCase();

      return matchesSearch && matchesBloodGroup && matchesDonationType && matchesStatus;
    });
  };

  const filteredList = filteredDonations();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // Page slice
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedDonations = filteredList.slice(startIndex, startIndex + itemsPerPage);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', width: '100%' }}>
      {/* Search & Filter Toolbar */}
      <section className="filters-toolbar">
        <div className="search-box-wrapper">
          <Search size={18} className="search-icon-input" />
          <input
            type="text"
            placeholder="Search donations by donor name, ID, phone, hospital..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            className="toolbar-search-input"
          />
        </div>

        <div className="dropdowns-group">
          <div className="filter-select-wrapper">
            <select
              value={bloodGroupFilter}
              onChange={(e) => {
                setBloodGroupFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Blood Groups</option>
              {BLOOD_GROUPS.map(g => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>

          <div className="filter-select-wrapper">
            <select
              value={donationTypeFilter}
              onChange={(e) => {
                setDonationTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Donation Types</option>
              {DONATION_TYPES.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="filter-select-wrapper">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Statuses</option>
              {ALL_STATUSES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <button className="add-donor-btn" onClick={handleOpenAddModal}>
            + Record Donation
          </button>
        </div>
      </section>

      {/* Blood Donations Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>Donation ID</th>
                <th>Donor Name</th>
                <th>Blood Group</th>
                <th>Units</th>
                <th>Date</th>
                <th>Type</th>
                <th>Hospital / Facility</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedDonations.length > 0 ? (
                paginatedDonations.map((don) => {
                  const statusColors = getStatusStyles(don.status);
                  const isTerminal = ['completed', 'cancelled', 'rejected'].includes((don.status || '').toLowerCase());
                  const allowedTransitions = getAllowedDonationStatuses(don.status);

                  return (
                    <tr key={don.id}>
                      <td className="donor-id-cell font-semibold">{don.id}</td>
                      <td className="donor-name-cell">{don.donorName || 'Registered Donor'}</td>
                      <td>
                        <span className="blood-group-badge">{don.bloodGroup}</span>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>{don.unitsDonated || 1}</td>
                      <td>{don.donationDate}</td>
                      <td>{don.donationType || 'Voluntary'}</td>
                      <td>{don.hospital || 'District Blood Bank'}</td>
                      <td>
                        {isTerminal ? (
                          <span style={{
                            backgroundColor: statusColors.bg,
                            color: statusColors.text,
                            border: `1px solid ${statusColors.border}`,
                            padding: '4px 10px',
                            borderRadius: '20px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            display: 'inline-block',
                            textAlign: 'center'
                          }}>
                            {don.status}
                          </span>
                        ) : (
                          <select
                            value={don.status}
                            onChange={(e) => onStatusChange && onStatusChange(don.id, e.target.value)}
                            style={{
                              backgroundColor: statusColors.bg,
                              color: statusColors.text,
                              border: `1px solid ${statusColors.border}`,
                              padding: '4px 10px',
                              borderRadius: '20px',
                              fontSize: '0.8rem',
                              fontWeight: '600',
                              cursor: 'pointer',
                              outline: 'none',
                              appearance: 'none',
                              WebkitAppearance: 'none',
                              textAlign: 'center'
                            }}
                          >
                            {allowedTransitions.map(s => (
                              <option key={s} value={s}>{s}</option>
                            ))}
                          </select>
                        )}
                      </td>
                      <td>
                        <div className="actions-cell-wrapper">
                          <button
                            className="action-icon-btn view"
                            onClick={() => setViewingDonation(don)}
                            title="View Details"
                          >
                            <Eye size={16} />
                          </button>
                          {!isTerminal && (
                            <button
                              className="action-icon-btn edit"
                              onClick={() => handleOpenEditModal(don)}
                              title="Edit Record"
                            >
                              <Edit2 size={16} />
                            </button>
                          )}
                          {!isTerminal && (
                            <button
                              className="action-icon-btn delete"
                              onClick={() => setDeletingDonationId(don.id)}
                              title="Cancel Donation"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="9" className="no-records-cell">
                    No donation records found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer / Pagination */}
        <div className="table-footer">
          <div className="footer-info-text">
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} donations
          </div>
          <div className="pagination-controls">
            <button
              className="pagination-btn"
              disabled={currentPage === 1}
              onClick={() => handlePageChange(currentPage - 1)}
            >
              Previous
            </button>
            
            {Array.from({ length: totalPages }, (_, index) => {
              const pageNum = index + 1;
              return (
                <button
                  key={pageNum}
                  className={`pagination-number-btn ${currentPage === pageNum ? 'active-page' : ''}`}
                  onClick={() => handlePageChange(pageNum)}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() => handlePageChange(currentPage + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {/* --- Add / Edit Blood Donation Modal --- */}
      {(isAddingDonation || editingDonation) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingDonation ? 'Edit Donation Record' : 'Record Blood Donation'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingDonation(false);
                  setEditingDonation(null);
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveDonationSubmit} className="modal-form">
              <div className="form-grid">
                {donors.length > 0 && !editingDonation && (
                  <div className="form-group-item">
                    <label htmlFor="don-donor-select">Select Registered Donor <span className="req-star">*</span></label>
                    <select
                      id="don-donor-select"
                      value={donationForm.donorId}
                      onChange={(e) => {
                        const dId = e.target.value;
                        const donor = donors.find(d => String(d.dbId || d.id) === String(dId));
                        if (donor) {
                          setDonationForm({
                            ...donationForm,
                            donorId: dId,
                            donorName: donor.name,
                            bloodGroup: donor.group,
                            phone: donor.phone,
                            email: donor.email,
                            district: donor.location || donationForm.district
                          });
                        } else {
                          setDonationForm({ ...donationForm, donorId: dId });
                        }
                      }}
                      required
                    >
                      <option value="">-- Choose Donor --</option>
                      {donors.map(d => (
                        <option key={d.dbId || d.id} value={d.dbId || d.id}>
                          {d.name} ({d.group}) — {d.id}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="form-group-item">
                  <label htmlFor="don-donor-name">Donor Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="don-donor-name"
                    value={donationForm.donorName}
                    onChange={(e) => setDonationForm({ ...donationForm, donorName: e.target.value })}
                    required
                    placeholder="e.g. Rahul Nair"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-blood-group">Blood Group <span className="req-star">*</span></label>
                  <select
                    id="don-blood-group"
                    value={donationForm.bloodGroup}
                    onChange={(e) => setDonationForm({ ...donationForm, bloodGroup: e.target.value })}
                    required
                  >
                    {BLOOD_GROUPS.map(g => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-units">Units Donated <span className="req-star">*</span></label>
                  <input
                    type="number"
                    id="don-units"
                    min="1"
                    max="5"
                    value={donationForm.unitsDonated}
                    onChange={(e) => setDonationForm({ ...donationForm, unitsDonated: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-date">Donation Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="don-date"
                    value={donationForm.donationDate}
                    onChange={(e) => setDonationForm({ ...donationForm, donationDate: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-type">Donation Type</label>
                  <select
                    id="don-type"
                    value={donationForm.donationType}
                    onChange={(e) => setDonationForm({ ...donationForm, donationType: e.target.value })}
                  >
                    {DONATION_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-status">Initial Status</label>
                  <select
                    id="don-status"
                    value={donationForm.status}
                    onChange={(e) => setDonationForm({ ...donationForm, status: e.target.value })}
                  >
                    {ALL_STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group-item" style={{ marginTop: '16px' }}>
                <label htmlFor="don-notes">Clinical Notes</label>
                <textarea
                  id="don-notes"
                  rows="2"
                  value={donationForm.notes}
                  onChange={(e) => setDonationForm({ ...donationForm, notes: e.target.value })}
                  placeholder="e.g. Screening passed, Hemoglobin: 14.2 g/dL"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: '1px solid #CBD5E1',
                    fontSize: '0.9rem'
                  }}
                ></textarea>
              </div>

              <div className="modal-footer-actions">
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => {
                    setIsAddingDonation(false);
                    setEditingDonation(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingDonation ? 'Save Changes' : 'Record Donation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Donation Record Modal --- */}
      {viewingDonation && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Donation Record</h3>
              <button className="modal-close-btn" onClick={() => setViewingDonation(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large">
                <span>{viewingDonation.bloodGroup}</span>
              </div>
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Donation Code</span>
                  <span className="detail-val font-semibold">{viewingDonation.id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Donor Name</span>
                  <span className="detail-val font-semibold">{viewingDonation.donorName}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Units</span>
                  <span className="detail-val font-semibold text-rose-red">{viewingDonation.unitsDonated || 1} Unit</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Donation Date</span>
                  <span className="detail-val">{viewingDonation.donationDate}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Donation Type</span>
                  <span className="detail-val">{viewingDonation.donationType}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Hospital / Center</span>
                  <span className="detail-val">{viewingDonation.hospital}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className="detail-val font-semibold">{viewingDonation.status}</span>
                </div>
              </div>
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingDonation(null)}>
                  Close Record
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete / Cancel Donation Modal --- */}
      {deletingDonationId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Cancellation</h3>
              <button className="modal-close-btn" onClick={() => setDeletingDonationId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <p>Are you sure you want to cancel donation <strong>{deletingDonationId}</strong>?</p>
              <p className="sub-warning">This donation will transition to CANCELLED and will no longer affect donor cooldown.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingDonationId(null)}>
                  Keep
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteDonationConfirm}>
                  Cancel Donation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
