import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  MapPin,
  Phone,
  ShieldAlert
} from 'lucide-react';

// list of Kerala districts
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

export default function HospitalsPage({
  hospitals,
  onAddHospital,
  onEditHospital,
  onDeleteHospital
}) {
  // search & filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [districtFilter, setDistrictFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // modal states
  const [isAddingHospital, setIsAddingHospital] = useState(false);
  const [viewingHospital, setViewingHospital] = useState(null);
  const [editingHospital, setEditingHospital] = useState(null);
  const [deletingHospitalId, setDeletingHospitalId] = useState(null);

  // form state for add/edit
  const [hospitalForm, setHospitalForm] = useState({
    name: '',
    type: 'Government',
    district: 'Kottayam',
    panchayat: '',
    address: '',
    phone: '',
    email: '',
    emergencyNumber: '108',
    latitude: '',
    longitude: '',
    servicesInput: '',
    status: 'Active'
  });

  // reset form helper
  const resetForm = () => {
    setHospitalForm({
      name: '',
      type: 'Government',
      district: 'Kottayam',
      panchayat: '',
      address: '',
      phone: '',
      email: '',
      emergencyNumber: '108',
      latitude: '',
      longitude: '',
      servicesInput: '',
      status: 'Active'
    });
  };

  // handlers
  const handleOpenAddModal = () => {
    resetForm();
    setIsAddingHospital(true);
  };

  const handleOpenEditModal = (hosp) => {
    setHospitalForm({
      name: hosp.name,
      type: hosp.type,
      district: hosp.district,
      panchayat: hosp.panchayat || '',
      address: hosp.address,
      phone: hosp.phone || '',
      email: hosp.email || '',
      emergencyNumber: hosp.emergencyNumber || '108',
      latitude: hosp.latitude || '',
      longitude: hosp.longitude || '',
      servicesInput: hosp.services ? hosp.services.join(', ') : '',
      status: hosp.status || 'Active'
    });
    setEditingHospital(hosp);
  };

  const handleSaveHospitalSubmit = (e) => {
    e.preventDefault();
    if (!hospitalForm.name || !hospitalForm.type || !hospitalForm.district || !hospitalForm.address) {
      alert('Please fill in all required fields.');
      return;
    }

    const services = hospitalForm.servicesInput
      ? hospitalForm.servicesInput.split(',').map(s => s.trim()).filter(Boolean)
      : [];

    const hospitalData = {
      name: hospitalForm.name,
      type: hospitalForm.type,
      district: hospitalForm.district,
      panchayat: hospitalForm.panchayat,
      address: hospitalForm.address,
      phone: hospitalForm.phone,
      email: hospitalForm.email,
      emergencyNumber: hospitalForm.emergencyNumber,
      latitude: hospitalForm.latitude ? parseFloat(hospitalForm.latitude) : null,
      longitude: hospitalForm.longitude ? parseFloat(hospitalForm.longitude) : null,
      services,
      status: hospitalForm.status
    };

    if (editingHospital) {
      onEditHospital({
        ...hospitalData,
        id: editingHospital.id,
        dbId: editingHospital.dbId
      });
      setEditingHospital(null);
    } else {
      onAddHospital(hospitalData);
      setIsAddingHospital(false);
    }
    resetForm();
  };

  const handleDeleteHospitalConfirm = () => {
    if (deletingHospitalId) {
      onDeleteHospital(deletingHospitalId);
      setDeletingHospitalId(null);
      
      // adjust page if final item on page was deleted
      const filtered = filteredHospitals();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // client-side filtering logic
  const filteredHospitals = () => {
    return hospitals.filter((hosp) => {
      const matchesSearch =
        hosp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        hosp.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (hosp.panchayat && hosp.panchayat.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (hosp.phone && hosp.phone.includes(searchQuery)) ||
        (hosp.email && hosp.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (hosp.services && hosp.services.some(s => s.toLowerCase().includes(searchQuery.toLowerCase())));

      const matchesDistrict = districtFilter === 'All' || hosp.district === districtFilter;
      const matchesType = typeFilter === 'All' || hosp.type === typeFilter;
      const matchesStatus = statusFilter === 'All' || hosp.status === statusFilter;

      return matchesSearch && matchesDistrict && matchesType && matchesStatus;
    });
  };

  const filteredList = filteredHospitals();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // page slice
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedHospitals = filteredList.slice(startIndex, startIndex + itemsPerPage);

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
            placeholder="Search hospitals by name, body, service, phone..."
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
              value={districtFilter}
              onChange={(e) => {
                setDistrictFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Districts</option>
              {DISTRICTS.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="filter-select-wrapper">
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Types</option>
              <option value="Government">Government</option>
              <option value="Private">Private</option>
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
              <option value="All">All Status</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>

          <button className="add-donor-btn" onClick={handleOpenAddModal}>
            + Add Hospital
          </button>
        </div>
      </section>

      {/* Hospitals Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>Hospital Name</th>
                <th>Hospital Type</th>
                <th>District</th>
                <th>Local Body / Panchayat</th>
                <th>Phone</th>
                <th>Emergency Number</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedHospitals.length > 0 ? (
                paginatedHospitals.map((hosp) => (
                  <tr key={hosp.id}>
                    <td className="donor-name-cell font-semibold">{hosp.name}</td>
                    <td>{hosp.type}</td>
                    <td>{hosp.district}</td>
                    <td>{hosp.panchayat || 'N/A'}</td>
                    <td className="donor-phone-cell">{hosp.phone || 'N/A'}</td>
                    <td>{hosp.emergencyNumber || 'N/A'}</td>
                    <td>
                      <span className={`status-pill-badge ${hosp.status === 'Active' ? 'active-badge' : 'inactive-badge'}`}>
                        {hosp.status}
                      </span>
                    </td>
                    <td>
                      <div className="actions-cell-wrapper">
                        <button
                          className="action-icon-btn view"
                          onClick={() => setViewingHospital(hosp)}
                          title="View Details"
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          className="action-icon-btn edit"
                          onClick={() => handleOpenEditModal(hosp)}
                          title="Edit Hospital"
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          className="action-icon-btn delete"
                          onClick={() => setDeletingHospitalId(hosp.id)}
                          title="Delete Hospital"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="8" className="no-records-cell">
                    No hospitals found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer / Pagination */}
        <div className="table-footer">
          <div className="footer-info-text">
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} hospitals
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

      {/* --- Add / Edit Hospital Modal --- */}
      {(isAddingHospital || editingHospital) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingHospital ? 'Edit Hospital Details' : 'Add New Hospital'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingHospital(false);
                  setEditingHospital(null);
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveHospitalSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="hosp-name">Hospital Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="hosp-name"
                    value={hospitalForm.name}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, name: e.target.value })}
                    required
                    placeholder="Enter hospital name"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-type">Hospital Type <span className="req-star">*</span></label>
                  <select
                    id="hosp-type"
                    value={hospitalForm.type}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, type: e.target.value })}
                    required
                  >
                    <option value="Government">Government</option>
                    <option value="Private">Private</option>
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-district">District <span className="req-star">*</span></label>
                  <select
                    id="hosp-district"
                    value={hospitalForm.district}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, district: e.target.value })}
                    required
                  >
                    {DISTRICTS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-panchayat">Local Body / Panchayat</label>
                  <input
                    type="text"
                    id="hosp-panchayat"
                    value={hospitalForm.panchayat}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, panchayat: e.target.value })}
                    placeholder="e.g. Kumarakom"
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="hosp-address">Full Address <span className="req-star">*</span></label>
                  <textarea
                    id="hosp-address"
                    value={hospitalForm.address}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, address: e.target.value })}
                    required
                    placeholder="Enter full physical address"
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

                <div className="form-group-item">
                  <label htmlFor="hosp-phone">Phone Number</label>
                  <input
                    type="tel"
                    id="hosp-phone"
                    value={hospitalForm.phone}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, phone: e.target.value })}
                    placeholder="e.g. 04812597311"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-email">Email Address</label>
                  <input
                    type="email"
                    id="hosp-email"
                    value={hospitalForm.email}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, email: e.target.value })}
                    placeholder="hospital@example.com"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-emergency">Emergency Number</label>
                  <input
                    type="text"
                    id="hosp-emergency"
                    value={hospitalForm.emergencyNumber}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, emergencyNumber: e.target.value })}
                    placeholder="e.g. 108"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-status">Status</label>
                  <select
                    id="hosp-status"
                    value={hospitalForm.status}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, status: e.target.value })}
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-lat">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    id="hosp-lat"
                    value={hospitalForm.latitude}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, latitude: e.target.value })}
                    placeholder="e.g. 9.5916"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="hosp-lng">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    id="hosp-lng"
                    value={hospitalForm.longitude}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, longitude: e.target.value })}
                    placeholder="e.g. 76.5222"
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="hosp-services">Services / Departments (comma separated)</label>
                  <input
                    type="text"
                    id="hosp-services"
                    value={hospitalForm.servicesInput}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, servicesInput: e.target.value })}
                    placeholder="Emergency, Cardiology, Orthopaedics, Pediatrics"
                  />
                </div>
              </div>

              <div className="modal-footer-actions">
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => {
                    setIsAddingHospital(false);
                    setEditingHospital(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingHospital ? 'Save Changes' : 'Add Hospital'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Hospital Modal --- */}
      {viewingHospital && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Hospital Information File</h3>
              <button className="modal-close-btn" onClick={() => setViewingHospital(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large" style={{ backgroundColor: 'var(--blue-bg)', color: 'var(--blue-progress)' }}>
                <MapPin size={24} />
              </div>
              <h4 style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 20px 0', color: 'var(--dark-text)' }}>
                {viewingHospital.name}
              </h4>
              
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Hospital Type</span>
                  <span className="detail-val font-semibold">{viewingHospital.type}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">District</span>
                  <span className="detail-val font-semibold">{viewingHospital.district}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Panchayat / Local Body</span>
                  <span className="detail-val">{viewingHospital.panchayat || 'N/A'}</span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Full Address</span>
                  <span className="detail-val">{viewingHospital.address}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Phone Number</span>
                  <span className="detail-val">{viewingHospital.phone || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Email Address</span>
                  <span className="detail-val">{viewingHospital.email || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Emergency Number</span>
                  <span className="detail-val" style={{ color: 'var(--primary-rose)', fontWeight: 600 }}>
                    {viewingHospital.emergencyNumber || 'N/A'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Coordinates</span>
                  <span className="detail-val">
                    {viewingHospital.latitude && viewingHospital.longitude
                      ? `${viewingHospital.latitude}, ${viewingHospital.longitude}`
                      : 'N/A'}
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Services & Departments</span>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                    {viewingHospital.services && viewingHospital.services.length > 0 ? (
                      viewingHospital.services.map((serv, index) => (
                        <span
                          key={index}
                          style={{
                            padding: '4px 10px',
                            backgroundColor: '#f1f5f9',
                            borderRadius: '20px',
                            fontSize: '0.8rem',
                            color: '#475569',
                            fontWeight: 500
                          }}
                        >
                          {serv}
                        </span>
                      ))
                    ) : (
                      <span className="detail-val">None Specified</span>
                    )}
                  </div>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className={`status-pill-badge ${viewingHospital.status === 'Active' ? 'active-badge' : 'inactive-badge'}`}>
                    {viewingHospital.status}
                  </span>
                </div>
              </div>
              
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingHospital(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingHospitalId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingHospitalId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Permanently Delete Record</strong>
              </div>
              <p>Are you sure you want to delete this hospital? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingHospitalId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteHospitalConfirm}>
                  Delete Hospital
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
