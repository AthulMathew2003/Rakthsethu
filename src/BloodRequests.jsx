import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  Droplet,
  Heart,
  Phone,
  ShieldAlert,
  Calendar,
  Users,
  AlertTriangle
} from 'lucide-react';
import MatchingModal from './MatchingModal.jsx';
import { DISTRICTS, BLOOD_GROUPS, REQUEST_STATUSES, REQUEST_URGENCY } from './types.js';

const URGENCY_LEVELS = ['Normal', 'Urgent', 'Critical'];
const ALL_STATUSES = ['Pending', 'In Progress', 'Fulfilled', 'Rejected', 'Cancelled'];

// Helper to get allowed transitions from current status
function getAllowedStatuses(currentStatus) {
  const norm = (currentStatus || 'Pending').toLowerCase().replace('_', ' ');
  if (norm === 'pending') {
    return ['Pending', 'In Progress', 'Cancelled', 'Rejected'];
  }
  if (norm === 'in progress') {
    return ['In Progress', 'Fulfilled', 'Cancelled', 'Rejected'];
  }
  // Terminal states cannot transition
  return [currentStatus];
}

// Helper to get status class for inline styling / badge coloring
function getStatusStyles(status) {
  const norm = (status || '').toLowerCase().replace('_', ' ');
  switch (norm) {
    case 'pending':
      return { bg: '#FEF3C7', text: '#D97706', border: '#FCD34D' }; // amber
    case 'in progress':
      return { bg: '#F3E8FF', text: '#9333EA', border: '#E9D5FF' }; // purple
    case 'fulfilled':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // emerald
    case 'rejected':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    case 'cancelled':
      return { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1' }; // slate
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

export default function BloodRequestsPage({
  requests,
  onAddRequest,
  onEditRequest,
  onDeleteRequest,
  onStatusChange,
  hospitals = []
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [bloodGroupFilter, setBloodGroupFilter] = useState('All');
  const [urgencyFilter, setUrgencyFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal states
  const [isAddingRequest, setIsAddingRequest] = useState(false);
  const [viewingRequest, setViewingRequest] = useState(null);
  const [editingRequest, setEditingRequest] = useState(null);
  const [deletingRequestId, setDeletingRequestId] = useState(null);
  const [matchingRequest, setMatchingRequest] = useState(null);

  // Form State
  const [requestForm, setRequestForm] = useState({
    patientName: '',
    bloodGroup: 'O+',
    unitsRequired: 1,
    hospital: '',
    hospitalId: '',
    district: 'Kottayam',
    requiredDate: '',
    contactNumber: '',
    emergencyContact: '',
    urgency: 'Normal',
    notes: '',
    status: 'Pending'
  });

  const resetForm = () => {
    setRequestForm({
      patientName: '',
      bloodGroup: 'O+',
      unitsRequired: 1,
      hospital: hospitals[0]?.name || '',
      hospitalId: hospitals[0]?.dbId || hospitals[0]?.id || '',
      district: 'Kottayam',
      requiredDate: '',
      contactNumber: '',
      emergencyContact: '',
      urgency: 'Normal',
      notes: '',
      status: 'Pending'
    });
  };

  const handleOpenAddModal = () => {
    resetForm();
    setIsAddingRequest(true);
  };

  const handleOpenEditModal = (req) => {
    setRequestForm({
      patientName: req.patientName,
      bloodGroup: req.bloodGroup,
      unitsRequired: req.unitsRequired,
      hospital: req.hospital,
      hospitalId: req.hospitalId || '',
      district: req.district,
      requiredDate: req.requiredDate,
      contactNumber: req.contactNumber || '',
      emergencyContact: req.emergencyContact || '',
      urgency: req.urgency || 'Normal',
      notes: req.notes || '',
      status: req.status || 'Pending'
    });
    setEditingRequest(req);
  };

  const handleSaveRequestSubmit = (e) => {
    e.preventDefault();
    if (
      !requestForm.patientName ||
      !requestForm.bloodGroup ||
      !requestForm.unitsRequired ||
      !requestForm.district ||
      !requestForm.requiredDate
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const requestData = {
      patientName: requestForm.patientName,
      bloodGroup: requestForm.bloodGroup,
      unitsRequired: parseInt(requestForm.unitsRequired, 10),
      hospital: requestForm.hospital,
      hospitalId: requestForm.hospitalId,
      district: requestForm.district,
      requiredDate: requestForm.requiredDate,
      contactNumber: requestForm.contactNumber,
      emergencyContact: requestForm.emergencyContact,
      urgency: requestForm.urgency,
      notes: requestForm.notes,
      status: requestForm.status
    };

    if (editingRequest) {
      onEditRequest({
        ...requestData,
        id: editingRequest.id,
        dbId: editingRequest.dbId
      });
      setEditingRequest(null);
    } else {
      onAddRequest(requestData);
      setIsAddingRequest(false);
    }
    resetForm();
  };

  const handleDeleteRequestConfirm = () => {
    if (deletingRequestId) {
      onDeleteRequest(deletingRequestId);
      setDeletingRequestId(null);

      const filtered = filteredRequests();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // Client-side filtering logic
  const filteredRequests = () => {
    return requests.filter((req) => {
      const matchesSearch =
        (req.patientName || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (req.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (req.hospital || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (req.bloodGroup || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (req.district || '').toLowerCase().includes(searchQuery.toLowerCase());

      const matchesBloodGroup = bloodGroupFilter === 'All' || req.bloodGroup === bloodGroupFilter;
      const matchesUrgency = urgencyFilter === 'All' || (req.urgency || '').toLowerCase() === urgencyFilter.toLowerCase();
      const matchesStatus = statusFilter === 'All' || (req.status || '').toLowerCase().replace('_', ' ') === statusFilter.toLowerCase().replace('_', ' ');

      return matchesSearch && matchesBloodGroup && matchesUrgency && matchesStatus;
    });
  };

  const filteredList = filteredRequests();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // Page slice
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedRequests = filteredList.slice(startIndex, startIndex + itemsPerPage);

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
            placeholder="Search requests by name, ID, hospital, group, district..."
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
              value={urgencyFilter}
              onChange={(e) => {
                setUrgencyFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Urgency</option>
              {URGENCY_LEVELS.map(u => (
                <option key={u} value={u}>{u}</option>
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
            + Add Request
          </button>
        </div>
      </section>

      {/* Blood Requests Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Patient Name</th>
                <th>Blood Group</th>
                <th>Required Units</th>
                <th>Hospital</th>
                <th>District</th>
                <th>Required Date</th>
                <th>Urgency</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedRequests.length > 0 ? (
                paginatedRequests.map((req) => {
                  const statusColors = getStatusStyles(req.status);
                  const allowedTransitions = getAllowedStatuses(req.status);
                  const isTerminal = ['fulfilled', 'cancelled', 'rejected'].includes((req.status || '').toLowerCase().replace('_', ' '));

                  return (
                    <tr key={req.id}>
                      <td className="donor-id-cell font-semibold">{req.id}</td>
                      <td className="donor-name-cell">{req.patientName}</td>
                      <td>
                        <span className="blood-group-badge">{req.bloodGroup}</span>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>{req.unitsRequired}</td>
                      <td>{req.hospital || 'Hospital'}</td>
                      <td>{req.district}</td>
                      <td>{req.requiredDate}</td>
                      <td>
                        {req.urgency === 'Critical' || req.urgency === 'CRITICAL' ? (
                          <span style={{ color: '#e11d48', fontWeight: '700', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                              display: 'inline-block',
                              width: '8px',
                              height: '8px',
                              borderRadius: '50%',
                              backgroundColor: '#e11d48',
                              boxShadow: '0 0 8px #e11d48'
                            }}></span>
                            Critical
                          </span>
                        ) : req.urgency === 'Urgent' || req.urgency === 'URGENT' ? (
                          <span style={{ color: '#ea580c', fontWeight: '600' }}>Urgent</span>
                        ) : (
                          <span style={{ color: '#64748b' }}>Normal</span>
                        )}
                      </td>
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
                            {req.status}
                          </span>
                        ) : (
                          <select
                            value={req.status}
                            onChange={(e) => onStatusChange(req.id, e.target.value)}
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
                          {/* Find Matches Action */}
                          {!isTerminal && (
                            <button
                              className="action-icon-btn"
                              style={{ color: '#E11D48', backgroundColor: '#FFE4E6' }}
                              onClick={() => setMatchingRequest(req)}
                              title="Find Eligible Donors"
                            >
                              <Users size={16} />
                            </button>
                          )}
                          <button
                            className="action-icon-btn view"
                            onClick={() => setViewingRequest(req)}
                            title="View Details"
                          >
                            <Eye size={16} />
                          </button>
                          {!isTerminal && (
                            <button
                              className="action-icon-btn edit"
                              onClick={() => handleOpenEditModal(req)}
                              title="Edit Request"
                            >
                              <Edit2 size={16} />
                            </button>
                          )}
                          {!isTerminal && (
                            <button
                              className="action-icon-btn delete"
                              onClick={() => setDeletingRequestId(req.id)}
                              title="Cancel Request"
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
                  <td colSpan="10" className="no-records-cell">
                    No blood requests found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer / Pagination */}
        <div className="table-footer">
          <div className="footer-info-text">
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} requests
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

      {/* --- Matching Results Modal --- */}
      {matchingRequest && (
        <MatchingModal
          isOpen={!!matchingRequest}
          onClose={() => setMatchingRequest(null)}
          request={matchingRequest}
        />
      )}

      {/* --- Add / Edit Blood Request Modal --- */}
      {(isAddingRequest || editingRequest) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingRequest ? 'Edit Request Details' : 'Create Blood Request'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingRequest(false);
                  setEditingRequest(null);
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveRequestSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="req-patient-name">Patient Name / Ref <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="req-patient-name"
                    value={requestForm.patientName}
                    onChange={(e) => setRequestForm({ ...requestForm, patientName: e.target.value })}
                    required
                    placeholder="e.g. John Doe / ICU Bed 4"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-blood-group">Blood Group Needed <span className="req-star">*</span></label>
                  <select
                    id="req-blood-group"
                    value={requestForm.bloodGroup}
                    onChange={(e) => setRequestForm({ ...requestForm, bloodGroup: e.target.value })}
                    required
                  >
                    {BLOOD_GROUPS.map(g => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-units">Units Required <span className="req-star">*</span></label>
                  <input
                    type="number"
                    id="req-units"
                    min="1"
                    max="50"
                    value={requestForm.unitsRequired}
                    onChange={(e) => setRequestForm({ ...requestForm, unitsRequired: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-district">Target District <span className="req-star">*</span></label>
                  <select
                    id="req-district"
                    value={requestForm.district}
                    onChange={(e) => setRequestForm({ ...requestForm, district: e.target.value })}
                    required
                  >
                    {DISTRICTS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-required-date">Fulfillment Target Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="req-required-date"
                    value={requestForm.requiredDate}
                    onChange={(e) => setRequestForm({ ...requestForm, requiredDate: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-contact">Contact Phone <span className="req-star">*</span></label>
                  <input
                    type="tel"
                    id="req-contact"
                    value={requestForm.contactNumber}
                    onChange={(e) => setRequestForm({ ...requestForm, contactNumber: e.target.value })}
                    required
                    placeholder="+91 XXXXX XXXXX"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-urgency">Clinical Urgency</label>
                  <select
                    id="req-urgency"
                    value={requestForm.urgency}
                    onChange={(e) => setRequestForm({ ...requestForm, urgency: e.target.value })}
                  >
                    {URGENCY_LEVELS.map(u => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-status">Workflow Status</label>
                  <select
                    id="req-status"
                    value={requestForm.status}
                    onChange={(e) => setRequestForm({ ...requestForm, status: e.target.value })}
                  >
                    {ALL_STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group-item" style={{ marginTop: '16px' }}>
                <label htmlFor="req-notes">Clinical Notes / Special Requirements</label>
                <textarea
                  id="req-notes"
                  rows="3"
                  value={requestForm.notes}
                  onChange={(e) => setRequestForm({ ...requestForm, notes: e.target.value })}
                  placeholder="e.g. Platelet pheresis preferred, crossmatch required immediately"
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
                    setIsAddingRequest(false);
                    setEditingRequest(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingRequest ? 'Save Changes' : 'Submit Blood Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Blood Request Details Modal --- */}
      {viewingRequest && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Blood Request Record</h3>
              <button className="modal-close-btn" onClick={() => setViewingRequest(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large">
                <span>{viewingRequest.bloodGroup}</span>
              </div>
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Request Code</span>
                  <span className="detail-val font-semibold">{viewingRequest.id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Patient / Ref</span>
                  <span className="detail-val font-semibold">{viewingRequest.patientName}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Units Requested</span>
                  <span className="detail-val font-semibold text-rose-red">{viewingRequest.unitsRequired} Units</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Hospital</span>
                  <span className="detail-val">{viewingRequest.hospital || 'Hospital'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">District</span>
                  <span className="detail-val">{viewingRequest.district}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Target Date</span>
                  <span className="detail-val">{viewingRequest.requiredDate}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Contact Phone</span>
                  <span className="detail-val">{viewingRequest.contactNumber}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Clinical Urgency</span>
                  <span className="detail-val">{viewingRequest.urgency}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className="detail-val font-semibold">{viewingRequest.status}</span>
                </div>
              </div>
              <div className="modal-footer-actions justify-center" style={{ gap: '12px' }}>
                <button
                  className="modal-primary-btn"
                  onClick={() => {
                    const req = viewingRequest;
                    setViewingRequest(null);
                    setMatchingRequest(req);
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                >
                  <Users size={16} /> Find Eligible Donors
                </button>
                <button className="modal-secondary-btn" onClick={() => setViewingRequest(null)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete / Cancel Blood Request Confirmation Modal --- */}
      {deletingRequestId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Request Cancellation</h3>
              <button className="modal-close-btn" onClick={() => setDeletingRequestId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <p>Are you sure you want to cancel request <strong>{deletingRequestId}</strong>?</p>
              <p className="sub-warning">This request will transition to CANCELLED and can no longer be matched or fulfilled.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingRequestId(null)}>
                  Keep Active
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteRequestConfirm}>
                  Cancel Request
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
