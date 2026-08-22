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
  Calendar
} from 'lucide-react';

const DISTRICTS = [
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

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const URGENCY_LEVELS = ['Normal', 'Urgent', 'Critical'];
const STATUSES = ['Pending', 'Approved', 'In Progress', 'Fulfilled', 'Rejected', 'Cancelled'];

// Helper to get status class for inline styling / badge coloring
function getStatusStyles(status) {
  switch (status) {
    case 'Pending':
      return { bg: '#FEF3C7', text: '#D97706', border: '#FCD34D' }; // amber
    case 'Approved':
      return { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' }; // blue
    case 'In Progress':
      return { bg: '#F3E8FF', text: '#9333EA', border: '#E9D5FF' }; // purple
    case 'Fulfilled':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // emerald
    case 'Rejected':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    case 'Cancelled':
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
  onStatusChange
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

  // Form State
  const [requestForm, setRequestForm] = useState({
    patientName: '',
    bloodGroup: 'O+',
    unitsRequired: 1,
    hospital: '',
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
      hospital: '',
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
      !requestForm.hospital ||
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
        id: editingRequest.id
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
        req.patientName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.hospital.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.bloodGroup.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.district.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesBloodGroup = bloodGroupFilter === 'All' || req.bloodGroup === bloodGroupFilter;
      const matchesUrgency = urgencyFilter === 'All' || req.urgency === urgencyFilter;
      const matchesStatus = statusFilter === 'All' || req.status === statusFilter;

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
              {STATUSES.map(s => (
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
                  return (
                    <tr key={req.id}>
                      <td className="donor-id-cell font-semibold">{req.id}</td>
                      <td className="donor-name-cell">{req.patientName}</td>
                      <td>
                        <span className="blood-group-badge">{req.bloodGroup}</span>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>{req.unitsRequired}</td>
                      <td>{req.hospital}</td>
                      <td>{req.district}</td>
                      <td>{req.requiredDate}</td>
                      <td>
                        {req.urgency === 'Critical' ? (
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
                        ) : req.urgency === 'Urgent' ? (
                          <span style={{ color: '#ea580c', fontWeight: '600' }}>Urgent</span>
                        ) : (
                          <span style={{ color: '#64748b' }}>Normal</span>
                        )}
                      </td>
                      <td>
                        {/* Interactive Status Dropdown styled as a badge */}
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
                          {STATUSES.map(s => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <div className="actions-cell-wrapper">
                          <button
                            className="action-icon-btn view"
                            onClick={() => setViewingRequest(req)}
                            title="View Details"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            className="action-icon-btn edit"
                            onClick={() => handleOpenEditModal(req)}
                            title="Edit Request"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            className="action-icon-btn delete"
                            onClick={() => setDeletingRequestId(req.id)}
                            title="Delete Request"
                          >
                            <Trash2 size={16} />
                          </button>
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
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveRequestSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="req-patient">Patient Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="req-patient"
                    value={requestForm.patientName}
                    onChange={(e) => setRequestForm({ ...requestForm, patientName: e.target.value })}
                    required
                    placeholder="Enter patient name"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-group">Blood Group <span className="req-star">*</span></label>
                  <select
                    id="req-group"
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
                    min="1"
                    id="req-units"
                    value={requestForm.unitsRequired}
                    onChange={(e) => setRequestForm({ ...requestForm, unitsRequired: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-hospital">Hospital Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="req-hospital"
                    value={requestForm.hospital}
                    onChange={(e) => setRequestForm({ ...requestForm, hospital: e.target.value })}
                    required
                    placeholder="e.g. Government Medical College"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-district">District <span className="req-star">*</span></label>
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
                  <label htmlFor="req-date">Required Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="req-date"
                    value={requestForm.requiredDate}
                    onChange={(e) => setRequestForm({ ...requestForm, requiredDate: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-phone">Contact Number</label>
                  <input
                    type="tel"
                    id="req-phone"
                    value={requestForm.contactNumber}
                    onChange={(e) => setRequestForm({ ...requestForm, contactNumber: e.target.value })}
                    placeholder="Enter phone number"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-emergency">Emergency Contact</label>
                  <input
                    type="tel"
                    id="req-emergency"
                    value={requestForm.emergencyContact}
                    onChange={(e) => setRequestForm({ ...requestForm, emergencyContact: e.target.value })}
                    placeholder="Emergency number"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-urgency">Urgency Level <span className="req-star">*</span></label>
                  <select
                    id="req-urgency"
                    value={requestForm.urgency}
                    onChange={(e) => setRequestForm({ ...requestForm, urgency: e.target.value })}
                    required
                  >
                    {URGENCY_LEVELS.map(u => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="req-status">Status</label>
                  <select
                    id="req-status"
                    value={requestForm.status}
                    onChange={(e) => setRequestForm({ ...requestForm, status: e.target.value })}
                  >
                    {STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="req-notes">Additional Notes</label>
                  <textarea
                    id="req-notes"
                    value={requestForm.notes}
                    onChange={(e) => setRequestForm({ ...requestForm, notes: e.target.value })}
                    placeholder="Explain patient's clinical state or urgent requirements..."
                    rows="2"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      fontFamily: 'inherit',
                      resize: 'vertical',
                      backgroundColor: 'var(--white)'
                    }}
                  />
                </div>
              </div>

              <div className="modal-footer-actions">
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => {
                    setIsAddingRequest(false);
                    setEditingRequest(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingRequest ? 'Save Changes' : 'Create Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Request Details Modal --- */}
      {viewingRequest && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Blood Request Profile</h3>
              <button className="modal-close-btn" onClick={() => setViewingRequest(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large" style={{ backgroundColor: '#FFF5F5', color: 'var(--primary-rose)' }}>
                <Droplet size={24} fill="currentColor" />
              </div>
              <h4 style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 20px 0', color: 'var(--dark-text)' }}>
                Request {viewingRequest.id}
              </h4>
              
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Patient Name</span>
                  <span className="detail-val font-semibold">{viewingRequest.patientName}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Blood Group</span>
                  <span className="detail-val font-semibold" style={{ color: 'var(--primary-rose)' }}>
                    {viewingRequest.bloodGroup}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Units Required</span>
                  <span className="detail-val font-semibold">{viewingRequest.unitsRequired} Units</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Required Date</span>
                  <span className="detail-val font-semibold" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Calendar size={14} /> {viewingRequest.requiredDate}
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Hospital / Venue</span>
                  <span className="detail-val">{viewingRequest.hospital}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">District</span>
                  <span className="detail-val">{viewingRequest.district}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Urgency Level</span>
                  <span className="detail-val font-semibold">
                    {viewingRequest.urgency === 'Critical' ? (
                      <span style={{ color: '#e11d48' }}>🔴 Critical</span>
                    ) : viewingRequest.urgency === 'Urgent' ? (
                      <span style={{ color: '#ea580c' }}>🟠 Urgent</span>
                    ) : (
                      'Normal'
                    )}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Contact Number</span>
                  <span className="detail-val">{viewingRequest.contactNumber || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Emergency Contact</span>
                  <span className="detail-val">{viewingRequest.emergencyContact || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className="detail-val">
                    <span style={{
                      backgroundColor: getStatusStyles(viewingRequest.status).bg,
                      color: getStatusStyles(viewingRequest.status).text,
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {viewingRequest.status}
                    </span>
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Additional Notes</span>
                  <span className="detail-val" style={{ whiteSpace: 'pre-wrap', fontStyle: viewingRequest.notes ? 'normal' : 'italic' }}>
                    {viewingRequest.notes || 'No additional notes provided.'}
                  </span>
                </div>
              </div>
              
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingRequest(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingRequestId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingRequestId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Delete Request</strong>
              </div>
              <p>Are you sure you want to delete blood request <strong>{deletingRequestId}</strong>? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingRequestId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteRequestConfirm}>
                  Delete Request
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
