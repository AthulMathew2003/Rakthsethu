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
  FileText
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
const DONATION_TYPES = ['Voluntary', 'Replacement', 'Camp Donation', 'Directed Donation'];
const STATUSES = ['Scheduled', 'Completed', 'Cancelled', 'Rejected'];

// Helper to get status class for badge styling
function getStatusStyles(status) {
  switch (status) {
    case 'Scheduled':
      return { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' }; // blue
    case 'Completed':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // green
    case 'Cancelled':
      return { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1' }; // slate
    case 'Rejected':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

export default function BloodDonationsPage({
  donations,
  onAddDonation,
  onEditDonation,
  onDeleteDonation
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
    donorName: '',
    bloodGroup: 'O+',
    phone: '',
    email: '',
    district: 'Kottayam',
    address: '',
    donationDate: '',
    donationType: 'Voluntary',
    unitsDonated: 1,
    hospital: '',
    status: 'Completed',
    notes: ''
  });

  const resetForm = () => {
    setDonationForm({
      donorName: '',
      bloodGroup: 'O+',
      phone: '',
      email: '',
      district: 'Kottayam',
      address: '',
      donationDate: '',
      donationType: 'Voluntary',
      unitsDonated: 1,
      hospital: '',
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
      donorName: don.donorName,
      bloodGroup: don.bloodGroup,
      phone: don.phone,
      email: don.email || '',
      district: don.district,
      address: don.address || '',
      donationDate: don.donationDate,
      donationType: don.donationType || 'Voluntary',
      unitsDonated: don.unitsDonated || 1,
      hospital: don.hospital || '',
      status: don.status || 'Completed',
      notes: don.notes || ''
    });
    setEditingDonation(don);
  };

  const handleSaveDonationSubmit = (e) => {
    e.preventDefault();
    if (
      !donationForm.donorName ||
      !donationForm.bloodGroup ||
      !donationForm.phone ||
      !donationForm.district ||
      !donationForm.donationDate ||
      !donationForm.donationType ||
      !donationForm.unitsDonated
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const donationData = {
      donorName: donationForm.donorName,
      bloodGroup: donationForm.bloodGroup,
      phone: donationForm.phone,
      email: donationForm.email,
      district: donationForm.district,
      address: donationForm.address,
      donationDate: donationForm.donationDate,
      donationType: donationForm.donationType,
      unitsDonated: parseInt(donationForm.unitsDonated, 10),
      hospital: donationForm.hospital,
      status: donationForm.status,
      notes: donationForm.notes
    };

    if (editingDonation) {
      onEditDonation({
        ...donationData,
        id: editingDonation.id
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
        don.donorName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        don.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        don.bloodGroup.toLowerCase().includes(searchQuery.toLowerCase()) ||
        don.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
        don.phone.includes(searchQuery);

      const matchesBloodGroup = bloodGroupFilter === 'All' || don.bloodGroup === bloodGroupFilter;
      const matchesType = donationTypeFilter === 'All' || don.donationType === donationTypeFilter;
      const matchesStatus = statusFilter === 'All' || don.status === statusFilter;

      return matchesSearch && matchesBloodGroup && matchesType && matchesStatus;
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
      
      {/* Blood Group Summary Section */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--muted-text)', margin: '0' }}>Blood Group Donations Summary</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '16px' }}>
          {BLOOD_GROUPS.map(group => {
            const count = donations
              .filter(d => d.bloodGroup === group && d.status === 'Completed')
              .reduce((sum, d) => sum + (d.unitsDonated || 1), 0);
            return (
              <div key={group} style={{
                backgroundColor: 'var(--white)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: 'var(--card-shadow)'
              }}>
                <span style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--dark-text)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--primary-rose)' }}></span>
                  {group}
                </span>
                <span style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--primary-red)' }}>{count} U</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Search & Filter Toolbar */}
      <section className="filters-toolbar">
        <div className="search-box-wrapper">
          <Search size={18} className="search-icon-input" />
          <input
            type="text"
            placeholder="Search donations by name, ID, group, district, phone..."
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
              <option value="All">All Types</option>
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
              {STATUSES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <button className="add-donor-btn" onClick={handleOpenAddModal}>
            + Add Donation
          </button>
        </div>
      </section>

      {/* Donations Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>Donation ID</th>
                <th>Donor Name</th>
                <th>Blood Group</th>
                <th>Phone Number</th>
                <th>District</th>
                <th>Donation Date</th>
                <th>Donation Type</th>
                <th>Units Donated</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedDonations.length > 0 ? (
                paginatedDonations.map((don) => {
                  const statusColors = getStatusStyles(don.status);
                  return (
                    <tr key={don.id}>
                      <td className="donor-id-cell font-semibold">{don.id}</td>
                      <td className="donor-name-cell font-semibold">{don.donorName}</td>
                      <td>
                        <span className="blood-group-badge">{don.bloodGroup}</span>
                      </td>
                      <td className="donor-phone-cell">{don.phone}</td>
                      <td>{don.district}</td>
                      <td>{don.donationDate}</td>
                      <td>{don.donationType}</td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>{don.unitsDonated} U</td>
                      <td>
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
                          <button
                            className="action-icon-btn edit"
                            onClick={() => handleOpenEditModal(don)}
                            title="Edit Record"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            className="action-icon-btn delete"
                            onClick={() => setDeletingDonationId(don.id)}
                            title="Delete Record"
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
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} records
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

      {/* --- Add / Edit Donation Modal --- */}
      {(isAddingDonation || editingDonation) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingDonation ? 'Edit Donation Record' : 'Add Blood Donation'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingDonation(false);
                  setEditingDonation(null);
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveDonationSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="don-name">Donor Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="don-name"
                    value={donationForm.donorName}
                    onChange={(e) => setDonationForm({ ...donationForm, donorName: e.target.value })}
                    required
                    placeholder="Enter donor name"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-group">Blood Group <span className="req-star">*</span></label>
                  <select
                    id="don-group"
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
                  <label htmlFor="don-phone">Phone Number <span className="req-star">*</span></label>
                  <input
                    type="tel"
                    id="don-phone"
                    value={donationForm.phone}
                    onChange={(e) => setDonationForm({ ...donationForm, phone: e.target.value })}
                    required
                    placeholder="Enter phone number"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-email">Email Address</label>
                  <input
                    type="email"
                    id="don-email"
                    value={donationForm.email}
                    onChange={(e) => setDonationForm({ ...donationForm, email: e.target.value })}
                    placeholder="example@gmail.com"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-district">District <span className="req-star">*</span></label>
                  <select
                    id="don-district"
                    value={donationForm.district}
                    onChange={(e) => setDonationForm({ ...donationForm, district: e.target.value })}
                    required
                  >
                    {DISTRICTS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
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
                  <label htmlFor="don-type">Donation Type <span className="req-star">*</span></label>
                  <select
                    id="don-type"
                    value={donationForm.donationType}
                    onChange={(e) => setDonationForm({ ...donationForm, donationType: e.target.value })}
                    required
                  >
                    {DONATION_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-units">Units Donated <span className="req-star">*</span></label>
                  <input
                    type="number"
                    min="1"
                    id="don-units"
                    value={donationForm.unitsDonated}
                    onChange={(e) => setDonationForm({ ...donationForm, unitsDonated: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-hospital">Hospital / Donation Centre</label>
                  <input
                    type="text"
                    id="don-hospital"
                    value={donationForm.hospital}
                    onChange={(e) => setDonationForm({ ...donationForm, hospital: e.target.value })}
                    placeholder="e.g. Kozhikode Medical Bank"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="don-status">Status <span className="req-star">*</span></label>
                  <select
                    id="don-status"
                    value={donationForm.status}
                    onChange={(e) => setDonationForm({ ...donationForm, status: e.target.value })}
                    required
                  >
                    {STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="don-address">Full Address</label>
                  <input
                    type="text"
                    id="don-address"
                    value={donationForm.address}
                    onChange={(e) => setDonationForm({ ...donationForm, address: e.target.value })}
                    placeholder="Enter physical address"
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="don-notes">Additional Notes</label>
                  <textarea
                    id="don-notes"
                    value={donationForm.notes}
                    onChange={(e) => setDonationForm({ ...donationForm, notes: e.target.value })}
                    placeholder="Any observations, donor health remarks..."
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
                    setIsAddingDonation(false);
                    setEditingDonation(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingDonation ? 'Save Changes' : 'Add Donation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Donation Modal --- */}
      {viewingDonation && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Donation Receipt Record</h3>
              <button className="modal-close-btn" onClick={() => setViewingDonation(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large" style={{ backgroundColor: '#ECFDF5', color: '#059669' }}>
                <FileText size={24} />
              </div>
              <h4 style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 20px 0', color: 'var(--dark-text)' }}>
                Donation {viewingDonation.id}
              </h4>
              
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Donor Name</span>
                  <span className="detail-val font-semibold">{viewingDonation.donorName}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Blood Group</span>
                  <span className="detail-val font-semibold" style={{ color: 'var(--primary-rose)' }}>
                    {viewingDonation.bloodGroup}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Phone Number</span>
                  <span className="detail-val">{viewingDonation.phone}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Email Address</span>
                  <span className="detail-val">{viewingDonation.email || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">District</span>
                  <span className="detail-val">{viewingDonation.district}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Donation Date</span>
                  <span className="detail-val font-semibold" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Calendar size={14} /> {viewingDonation.donationDate}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Donation Type</span>
                  <span className="detail-val">{viewingDonation.donationType}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Units Donated</span>
                  <span className="detail-val font-semibold">{viewingDonation.unitsDonated} Units</span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Hospital / Centre</span>
                  <span className="detail-val">{viewingDonation.hospital || 'N/A'}</span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Address</span>
                  <span className="detail-val">{viewingDonation.address || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className="detail-val">
                    <span style={{
                      backgroundColor: getStatusStyles(viewingDonation.status).bg,
                      color: getStatusStyles(viewingDonation.status).text,
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {viewingDonation.status}
                    </span>
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Notes & Remarks</span>
                  <span className="detail-val" style={{ whiteSpace: 'pre-wrap', fontStyle: viewingDonation.notes ? 'normal' : 'italic' }}>
                    {viewingDonation.notes || 'No remarks captured.'}
                  </span>
                </div>
              </div>
              
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingDonation(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingDonationId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingDonationId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Delete Donation Record</strong>
              </div>
              <p>Are you sure you want to delete donation record <strong>{deletingDonationId}</strong>? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingDonationId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteDonationConfirm}>
                  Delete Record
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
