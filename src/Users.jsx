import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  User,
  ShieldAlert,
  Calendar,
  Phone,
  Mail,
  MapPin,
  Users as UsersIcon,
  Activity,
  CheckCircle,
  AlertTriangle
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

const ROLES = ['Citizen', 'Panchayat Admin', 'Department Admin', 'Staff', 'Super Admin'];
const STATUSES = ['Active', 'Inactive', 'Suspended'];

function getStatusStyles(status) {
  switch (status) {
    case 'Active':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // green
    case 'Inactive':
      return { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1' }; // slate
    case 'Suspended':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

function getRoleColor(role) {
  switch (role) {
    case 'Super Admin':
      return '#e11d48'; // red
    case 'Department Admin':
      return '#2563eb'; // blue
    case 'Panchayat Admin':
      return '#9333ea'; // purple
    case 'Staff':
      return '#d97706'; // amber
    case 'Citizen':
      return '#059669'; // emerald
    default:
      return '#64748b';
  }
}

export default function UsersPage({
  users,
  onAddUser,
  onEditUser,
  onDeleteUser,
  onStatusChange
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [districtFilter, setDistrictFilter] = useState('All');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal states
  const [isAddingUser, setIsAddingUser] = useState(false);
  const [viewingUser, setViewingUser] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [deletingUserId, setDeletingUserId] = useState(null);

  // Form State
  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    phone: '',
    role: 'Citizen',
    district: 'Kottayam',
    panchayat: '',
    status: 'Active'
  });

  const resetForm = () => {
    setUserForm({
      name: '',
      email: '',
      phone: '',
      role: 'Citizen',
      district: 'Kottayam',
      panchayat: '',
      status: 'Active'
    });
  };

  const handleOpenAddModal = () => {
    resetForm();
    setIsAddingUser(true);
  };

  const handleOpenEditModal = (usr) => {
    setUserForm({
      name: usr.name,
      email: usr.email,
      phone: usr.phone || '',
      role: usr.role || 'Citizen',
      district: usr.district || 'Kottayam',
      panchayat: usr.panchayat || '',
      status: usr.status || 'Active'
    });
    setEditingUser(usr);
  };

  const handleSaveUserSubmit = (e) => {
    e.preventDefault();
    if (
      !userForm.name ||
      !userForm.email ||
      !userForm.role ||
      !userForm.district ||
      !userForm.status
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const userData = {
      name: userForm.name,
      email: userForm.email,
      phone: userForm.phone,
      role: userForm.role,
      district: userForm.district,
      panchayat: userForm.panchayat,
      status: userForm.status,
      registeredDate: editingUser ? editingUser.registeredDate : '2026-08-22',
      lastActive: editingUser ? editingUser.lastActive : '2026-08-22'
    };

    if (editingUser) {
      onEditUser({
        ...userData,
        id: editingUser.id,
        dbId: editingUser.dbId
      });
      setEditingUser(null);
    } else {
      onAddUser(userData);
      setIsAddingUser(false);
    }
    resetForm();
  };

  const handleDeleteUserConfirm = () => {
    if (deletingUserId) {
      onDeleteUser(deletingUserId);
      setDeletingUserId(null);

      const filtered = filteredUsers();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // Client-side filtering logic
  const filteredUsers = () => {
    return users.filter((usr) => {
      const matchesSearch =
        usr.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        usr.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        usr.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        usr.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
        usr.phone.includes(searchQuery);

      const matchesRole = roleFilter === 'All' || usr.role === roleFilter;
      const matchesStatus = statusFilter === 'All' || usr.status === statusFilter;
      const matchesDistrict = districtFilter === 'All' || usr.district === districtFilter;

      return matchesSearch && matchesRole && matchesStatus && matchesDistrict;
    });
  };

  const filteredList = filteredUsers();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // Page slice
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedUsers = filteredList.slice(startIndex, startIndex + itemsPerPage);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Statistical calculations
  const totalUsers = users.length;
  const activeUsers = users.filter(u => u.status === 'Active').length;
  const inactiveUsers = users.filter(u => u.status === 'Inactive').length;
  // A user is marked "New" if registeredDate >= 2026-08-15
  const newUsers = users.filter(u => new Date(u.registeredDate) >= new Date('2026-08-15')).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', width: '100%' }}>
      
      {/* User Stats Grid */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-donors">
              <UsersIcon size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Total Users</span>
            <h3 className="stat-card-value">{totalUsers}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-inventory">
              <CheckCircle size={20} className="stat-icon-svg" style={{ color: '#059669' }} />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Active Users</span>
            <h3 className="stat-card-value" style={{ color: '#059669' }}>{activeUsers}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-requests">
              <AlertTriangle size={20} className="stat-icon-svg" style={{ color: '#64748b' }} />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Inactive Users</span>
            <h3 className="stat-card-value" style={{ color: '#64748b' }}>{inactiveUsers}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-units">
              <Activity size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">New Users (Last 7 Days)</span>
            <h3 className="stat-card-value" style={{ color: 'var(--primary-rose)' }}>{newUsers}</h3>
          </div>
        </div>
      </section>

      {/* Search & Filter Toolbar */}
      <section className="filters-toolbar">
        <div className="search-box-wrapper">
          <Search size={18} className="search-icon-input" />
          <input
            type="text"
            placeholder="Search users by name, email, phone, ID, district..."
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
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Roles</option>
              {ROLES.map(r => (
                <option key={r} value={r}>{r}</option>
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

          <button className="add-donor-btn" onClick={handleOpenAddModal}>
            + Add User
          </button>
        </div>
      </section>

      {/* Users Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>User ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Role</th>
                <th>District</th>
                <th>Registered Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedUsers.length > 0 ? (
                paginatedUsers.map((usr) => {
                  const statusColors = getStatusStyles(usr.status);
                  return (
                    <tr key={usr.id}>
                      <td className="donor-id-cell font-semibold">{usr.id}</td>
                      <td className="donor-name-cell font-semibold">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {/* Circular small avatar */}
                          <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            backgroundColor: '#e2e8f0',
                            color: '#475569',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.8rem',
                            fontWeight: '700'
                          }}>
                            {usr.name[0]}
                          </div>
                          <span>{usr.name}</span>
                        </div>
                      </td>
                      <td>{usr.email}</td>
                      <td>{usr.phone || 'N/A'}</td>
                      <td>
                        <span style={{
                          color: getRoleColor(usr.role),
                          fontWeight: '700',
                          fontSize: '0.85rem'
                        }}>
                          {usr.role}
                        </span>
                      </td>
                      <td>{usr.district}</td>
                      <td>{usr.registeredDate}</td>
                      <td>
                        {/* Interactive Status Changer dropdown badge */}
                        <select
                          value={usr.status}
                          onChange={(e) => onStatusChange(usr.id, e.target.value)}
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
                            onClick={() => setViewingUser(usr)}
                            title="View Profile"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            className="action-icon-btn edit"
                            onClick={() => handleOpenEditModal(usr)}
                            title="Edit Account"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            className="action-icon-btn delete"
                            onClick={() => setDeletingUserId(usr.id)}
                            title="Delete User"
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
                  <td colSpan="9" className="no-records-cell">
                    No users found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer / Pagination */}
        <div className="table-footer">
          <div className="footer-info-text">
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} accounts
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

      {/* --- Add / Edit User Modal --- */}
      {(isAddingUser || editingUser) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingUser ? 'Edit User Information' : 'Add New Account'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingUser(false);
                  setEditingUser(null);
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveUserSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="usr-name">Full Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="usr-name"
                    value={userForm.name}
                    onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                    required
                    placeholder="Enter full name"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-email">Email Address <span className="req-star">*</span></label>
                  <input
                    type="email"
                    id="usr-email"
                    value={userForm.email}
                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                    required
                    placeholder="example@gmail.com"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-phone">Phone Number</label>
                  <input
                    type="tel"
                    id="usr-phone"
                    value={userForm.phone}
                    onChange={(e) => setUserForm({ ...userForm, phone: e.target.value })}
                    placeholder="Enter phone number"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-role">User Role <span className="req-star">*</span></label>
                  <select
                    id="usr-role"
                    value={userForm.role}
                    onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                    required
                  >
                    {ROLES.map(r => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-district">District <span className="req-star">*</span></label>
                  <select
                    id="usr-district"
                    value={userForm.district}
                    onChange={(e) => setUserForm({ ...userForm, district: e.target.value })}
                    required
                  >
                    {DISTRICTS.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-panchayat">Panchayat / Local Body</label>
                  <input
                    type="text"
                    id="usr-panchayat"
                    value={userForm.panchayat}
                    onChange={(e) => setUserForm({ ...userForm, panchayat: e.target.value })}
                    placeholder="e.g. Kanjirappally"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="usr-status">Account Status <span className="req-star">*</span></label>
                  <select
                    id="usr-status"
                    value={userForm.status}
                    onChange={(e) => setUserForm({ ...userForm, status: e.target.value })}
                    required
                  >
                    {STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="modal-footer-actions" style={{ marginTop: '24px' }}>
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => {
                    setIsAddingUser(false);
                    setEditingUser(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingUser ? 'Save Changes' : 'Add User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View User Profile Details Modal --- */}
      {viewingUser && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3>User Account Profile</h3>
              <button className="modal-close-btn" onClick={() => setViewingUser(null)}>
                <X size={20} />
              </button>
            </div>
            
            {/* User Profile Card Layout */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center', padding: '10px 0' }}>
              
              {/* Circular Big Profile Avatar */}
              <div style={{
                width: '72px',
                height: '72px',
                borderRadius: '50%',
                backgroundColor: 'var(--primary-rose)',
                color: 'var(--white)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '2rem',
                fontWeight: '800',
                boxShadow: '0 4px 10px rgba(244, 63, 94, 0.2)'
              }}>
                {viewingUser.name[0]}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                <h4 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, color: 'var(--dark-text)' }}>
                  {viewingUser.name}
                </h4>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: getRoleColor(viewingUser.role),
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: `${getRoleColor(viewingUser.role)}15`
                  }}>
                    {viewingUser.role}
                  </span>
                  <span style={{
                    backgroundColor: getStatusStyles(viewingUser.status).bg,
                    color: getStatusStyles(viewingUser.status).text,
                    border: `1px solid ${getStatusStyles(viewingUser.status).border}`,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700
                  }}>
                    {viewingUser.status}
                  </span>
                </div>
              </div>

              <div style={{ width: '100%', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem', color: '#475569' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Mail size={16} style={{ color: '#2563eb' }} />
                    <span>{viewingUser.email}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Phone size={16} style={{ color: '#d97706' }} />
                    <span>{viewingUser.phone || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <MapPin size={16} style={{ color: '#059669' }} />
                    <span>{viewingUser.district} {viewingUser.panchayat ? `(${viewingUser.panchayat} Panchayat)` : ''}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Calendar size={16} style={{ color: '#7c3aed' }} />
                    <span>Registered Date: <strong>{viewingUser.registeredDate}</strong></span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Activity size={16} style={{ color: '#0891b2' }} />
                    <span>Last Active: <strong>{viewingUser.lastActive || 'N/A'}</strong></span>
                  </div>
                </div>
              </div>

              <div className="modal-footer-actions justify-center" style={{ width: '100%', marginTop: '16px' }}>
                <button className="modal-primary-btn" onClick={() => setViewingUser(null)} style={{ width: '100%' }}>
                  Close Profile
                </button>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingUserId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingUserId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Delete User Account</strong>
              </div>
              <p>Are you sure you want to delete user account <strong>{deletingUserId}</strong>? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingUserId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteUserConfirm}>
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
