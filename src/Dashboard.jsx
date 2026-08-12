import React, { useState } from 'react';
import { 
  Users, 
  Heart, 
  AlertCircle, 
  CheckCircle2, 
  LogOut, 
  Plus, 
  Search, 
  Droplets, 
  PhoneCall,
  UserPlus,
  KeyRound,
  UserCheck,
  UserCog,
  Loader2
} from 'lucide-react';
import './Dashboard.css';

export default function Dashboard({ user, onLogout }) {
  const [activeUser, setActiveUser] = useState(user || {
    full_name: 'Rajesh Kumar',
    email: 'donor@rakthasethu.org',
    phone_number: '+91 9876543210'
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [bloodFilter, setBloodFilter] = useState('ALL');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);

  // Profile Edit State
  const [profileData, setProfileData] = useState({
    full_name: activeUser.full_name || '',
    email: activeUser.email || '',
    phone_number: activeUser.phone_number || ''
  });
  const [profileStatus, setProfileStatus] = useState({ loading: false, error: '', success: '' });

  // Change Password state
  const [pwdData, setPwdData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [pwdStatus, setPwdStatus] = useState({ loading: false, error: '', success: '' });

  // Mock initial blood requests
  const [requests, setRequests] = useState([
    { id: 'REQ-101', patient: 'Ananya Sharma', group: 'O+', units: 2, hospital: 'City General Hospital', urgency: 'Critical', status: 'Pending', phone: '+91 9811223344' },
    { id: 'REQ-102', patient: 'Vikram Patel', group: 'A-', units: 1, hospital: 'Apollo Emergency Care', urgency: 'Urgent', status: 'Approved', phone: '+91 9722334455' },
    { id: 'REQ-103', patient: 'Siddharth Nair', group: 'B+', units: 3, hospital: 'St. Marys Medical Centre', urgency: 'Normal', status: 'Fulfilled', phone: '+91 9633445566' },
    { id: 'REQ-104', patient: 'Priya Verma', group: 'AB+', units: 1, hospital: 'Max Super Specialty', urgency: 'Critical', status: 'Pending', phone: '+91 9544556677' },
  ]);

  // Registered Donors Quick View
  const [donors] = useState([
    { id: 'DON-01', name: 'Rajesh Kumar', group: 'O+', phone: '+91 9876543210', location: 'Bengaluru', status: 'Available' },
    { id: 'DON-02', name: 'Meera Deshmukh', group: 'B+', phone: '+91 9822114433', location: 'Mumbai', status: 'Available' },
    { id: 'DON-03', name: 'Arjun Reddy', group: 'AB-', phone: '+91 9900112233', location: 'Hyderabad', status: 'Donated Recently' },
  ]);

  // Handle status update
  const handleFulfillRequest = (id) => {
    setRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'Fulfilled' } : req));
  };

  const handleApproveRequest = (id) => {
    setRequests(prev => prev.map(req => req.id === id ? { ...req, status: 'Approved' } : req));
  };

  // Handle profile details update
  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileStatus({ loading: true, error: '', success: '' });

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(profileData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update profile details');
      }

      // Update active user state and localStorage
      const updatedUser = { ...activeUser, ...data };
      setActiveUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));

      setProfileStatus({ loading: false, error: '', success: 'Profile details updated successfully!' });
      setTimeout(() => {
        setShowProfileModal(false);
        setProfileStatus({ loading: false, error: '', success: '' });
      }, 1500);

    } catch (err) {
      setProfileStatus({ loading: false, error: err.message, success: '' });
    }
  };

  // Handle password change request
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwdStatus({ loading: true, error: '', success: '' });

    if (pwdData.new_password !== pwdData.confirm_password) {
      setPwdStatus({ loading: false, error: 'New passwords do not match!', success: '' });
      return;
    }

    if (pwdData.new_password.length < 6) {
      setPwdStatus({ loading: false, error: 'Password must be at least 6 characters.', success: '' });
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: pwdData.old_password,
          new_password: pwdData.new_password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to change password');
      }

      setPwdStatus({ loading: false, error: '', success: 'Password updated successfully!' });
      setPwdData({ old_password: '', new_password: '', confirm_password: '' });
      setTimeout(() => {
        setShowPasswordModal(false);
        setPwdStatus({ loading: false, error: '', success: '' });
      }, 1500);

    } catch (err) {
      setPwdStatus({ loading: false, error: err.message, success: '' });
    }
  };

  // Filter logic
  const filteredRequests = requests.filter(req => {
    const matchesSearch = req.patient.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          req.hospital.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGroup = bloodFilter === 'ALL' || req.group === bloodFilter;
    return matchesSearch && matchesGroup;
  });

  return (
    <div className="dashboard-wrapper">
      {/* Top Navbar */}
      <header className="dashboard-navbar">
        <div className="nav-brand">
          <div className="nav-logo-icon">
            <Droplets size={20} color="white" />
          </div>
          <span className="nav-brand-text">Rakthasedu Admin</span>
        </div>

        <div className="nav-admin-profile">
          <div className="user-badge">
            <div className="user-avatar">
              {activeUser.full_name ? activeUser.full_name.charAt(0) : 'A'}
            </div>
            <div className="user-details">
              <span className="user-name">{activeUser.full_name}</span>
              <span className="user-role">{activeUser.email}</span>
            </div>
          </div>

          <button 
            onClick={() => {
              setProfileData({
                full_name: activeUser.full_name || '',
                email: activeUser.email || '',
                phone_number: activeUser.phone_number || ''
              });
              setProfileStatus({ loading: false, error: '', success: '' });
              setShowProfileModal(true);
            }} 
            className="table-action-btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.5rem 0.85rem' }}
            title="Edit Admin Details"
          >
            <UserCog size={15} />
            <span>Edit Details</span>
          </button>

          <button 
            onClick={() => {
              setShowPasswordModal(true);
              setPwdStatus({ loading: false, error: '', success: '' });
            }} 
            className="table-action-btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.5rem 0.85rem' }}
          >
            <KeyRound size={15} />
            <span>Password</span>
          </button>

          <button onClick={onLogout} className="logout-btn" title="Sign Out">
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="dashboard-container">
        {/* Hero Welcome */}
        <section className="dashboard-hero">
          <h1 className="hero-title">Welcome back, {activeUser.full_name} 👋</h1>
          <p className="hero-subtitle">Intelligent Blood Donor & Emergency Request Management Overview</p>
        </section>

        {/* Quick Stats Grid */}
        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-info">
              <p>Total Donors</p>
              <div className="stat-number">154</div>
            </div>
            <div className="stat-icon-wrapper icon-red">
              <Users size={24} />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-info">
              <p>Active Requests</p>
              <div className="stat-number">12</div>
            </div>
            <div className="stat-icon-wrapper icon-amber">
              <AlertCircle size={24} />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-info">
              <p>Units Available</p>
              <div className="stat-number">45</div>
            </div>
            <div className="stat-icon-wrapper icon-blue">
              <Droplets size={24} />
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-info">
              <p>Lives Saved</p>
              <div className="stat-number">89</div>
            </div>
            <div className="stat-icon-wrapper icon-green">
              <Heart size={24} />
            </div>
          </div>
        </section>

        {/* Requests Management Section */}
        <section className="content-section">
          <div className="section-header">
            <div className="section-title">
              <Droplets size={20} color="#f43f5e" />
              <span>Blood Requests Management</span>
            </div>

            <div className="filter-actions">
              <input 
                type="text"
                placeholder="Search patient or hospital..."
                className="search-input"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />

              <select 
                className="search-input"
                value={bloodFilter}
                onChange={(e) => setBloodFilter(e.target.value)}
              >
                <option value="ALL">All Blood Groups</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
              </select>

              <button className="action-btn-primary" onClick={() => setShowAddModal(true)}>
                <Plus size={16} />
                <span>New Request</span>
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Patient Name</th>
                  <th>Blood Group</th>
                  <th>Units</th>
                  <th>Hospital</th>
                  <th>Urgency</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRequests.length > 0 ? (
                  filteredRequests.map(req => (
                    <tr key={req.id}>
                      <td><code style={{ color: '#94a3b8' }}>{req.id}</code></td>
                      <td style={{ fontWeight: 600 }}>{req.patient}</td>
                      <td><span className="blood-tag">{req.group}</span></td>
                      <td>{req.units} Units</td>
                      <td>{req.hospital}</td>
                      <td>
                        <span className={`urgency-badge ${
                          req.urgency === 'Critical' ? 'urgency-critical' :
                          req.urgency === 'Urgent' ? 'urgency-urgent' : 'urgency-normal'
                        }`}>
                          {req.urgency}
                        </span>
                      </td>
                      <td>
                        <span style={{ 
                          color: req.status === 'Fulfilled' ? '#34d399' : req.status === 'Approved' ? '#60a5fa' : '#fbbf24',
                          fontWeight: 600
                        }}>
                          {req.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          {req.status === 'Pending' && (
                            <button className="table-action-btn" onClick={() => handleApproveRequest(req.id)}>
                              Approve
                            </button>
                          )}
                          {req.status !== 'Fulfilled' && (
                            <button className="table-action-btn" onClick={() => handleFulfillRequest(req.id)}>
                              Fulfill
                            </button>
                          )}
                          <a href={`tel:${req.phone}`} className="table-action-btn" style={{ textDecoration: 'none' }}>
                            <PhoneCall size={12} style={{ marginRight: '4px' }} /> Call
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                      No matching blood requests found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Registered Donors List */}
        <section className="content-section">
          <div className="section-header">
            <div className="section-title">
              <UserPlus size={20} color="#60a5fa" />
              <span>Available Donors Directory</span>
            </div>
          </div>

          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Donor ID</th>
                  <th>Name</th>
                  <th>Blood Group</th>
                  <th>Location</th>
                  <th>Contact</th>
                  <th>Availability</th>
                </tr>
              </thead>
              <tbody>
                {donors.map(d => (
                  <tr key={d.id}>
                    <td><code>{d.id}</code></td>
                    <td style={{ fontWeight: 600 }}>{d.name}</td>
                    <td><span className="blood-tag">{d.group}</span></td>
                    <td>{d.location}</td>
                    <td>{d.phone}</td>
                    <td>
                      <span style={{ color: d.status === 'Available' ? '#34d399' : '#94a3b8', fontWeight: 600 }}>
                        {d.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {/* Edit Profile Modal */}
      {showProfileModal && (
        <div className="modal-overlay" onClick={() => setShowProfileModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserCog size={18} color="#60a5fa" />
                <span>Edit Admin Profile Details</span>
              </h3>
              <button className="modal-close-btn" onClick={() => setShowProfileModal(false)}>✕</button>
            </div>

            {profileStatus.error && (
              <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', color: '#fb7185', padding: '0.65rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                {profileStatus.error}
              </div>
            )}

            {profileStatus.success && (
              <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', padding: '0.65rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                {profileStatus.success}
              </div>
            )}

            <form onSubmit={handleUpdateProfile}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Full Name</label>
                <input 
                  type="text" 
                  required 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="Enter full name"
                  value={profileData.full_name}
                  onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Email Address</label>
                <input 
                  type="email" 
                  required 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="Enter email address"
                  value={profileData.email}
                  onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Phone Number</label>
                <input 
                  type="text" 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="+91 9876543210"
                  value={profileData.phone_number}
                  onChange={(e) => setProfileData({ ...profileData, phone_number: e.target.value })}
                />
              </div>

              <button 
                type="submit" 
                className="action-btn-primary" 
                style={{ width: '100%', justifyContent: 'center' }}
                disabled={profileStatus.loading}
              >
                {profileStatus.loading ? 'Saving Profile...' : 'Save Profile Changes'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <KeyRound size={18} color="#f43f5e" />
                <span>Change Account Password</span>
              </h3>
              <button className="modal-close-btn" onClick={() => setShowPasswordModal(false)}>✕</button>
            </div>

            {pwdStatus.error && (
              <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', color: '#fb7185', padding: '0.65rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                {pwdStatus.error}
              </div>
            )}

            {pwdStatus.success && (
              <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', padding: '0.65rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
                {pwdStatus.success}
              </div>
            )}

            <form onSubmit={handleChangePassword}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Current Password</label>
                <input 
                  type="password" 
                  required 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="Enter current password"
                  value={pwdData.old_password}
                  onChange={(e) => setPwdData({ ...pwdData, old_password: e.target.value })}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>New Password</label>
                <input 
                  type="password" 
                  required 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="Enter new password"
                  value={pwdData.new_password}
                  onChange={(e) => setPwdData({ ...pwdData, new_password: e.target.value })}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Confirm New Password</label>
                <input 
                  type="password" 
                  required 
                  className="search-input" 
                  style={{ width: '100%' }} 
                  placeholder="Confirm new password"
                  value={pwdData.confirm_password}
                  onChange={(e) => setPwdData({ ...pwdData, confirm_password: e.target.value })}
                />
              </div>

              <button 
                type="submit" 
                className="action-btn-primary" 
                style={{ width: '100%', justifyContent: 'center' }}
                disabled={pwdStatus.loading}
              >
                {pwdStatus.loading ? 'Updating Password...' : 'Update Password'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Add Request Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Emergency Blood Request</h3>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>✕</button>
            </div>
            <form onSubmit={(e) => {
              e.preventDefault();
              const form = e.target;
              const newReq = {
                id: `REQ-${Math.floor(100 + Math.random() * 900)}`,
                patient: form.patient.value,
                group: form.group.value,
                units: Number(form.units.value),
                hospital: form.hospital.value,
                urgency: form.urgency.value,
                status: 'Pending',
                phone: form.phone.value || '+91 9999988888'
              };
              setRequests([newReq, ...requests]);
              setShowAddModal(false);
            }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Patient Name</label>
                <input required name="patient" className="search-input" style={{ width: '100%' }} placeholder="Enter patient name" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Blood Group</label>
                  <select name="group" className="search-input" style={{ width: '100%' }}>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Units Needed</label>
                  <input required name="units" type="number" min="1" defaultValue="1" className="search-input" style={{ width: '100%' }} />
                </div>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Hospital / Location</label>
                <input required name="hospital" className="search-input" style={{ width: '100%' }} placeholder="Hospital name" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Urgency Level</label>
                  <select name="urgency" className="search-input" style={{ width: '100%' }}>
                    <option value="Critical">Critical</option>
                    <option value="Urgent">Urgent</option>
                    <option value="Normal">Normal</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.35rem' }}>Contact Phone</label>
                  <input required name="phone" className="search-input" style={{ width: '100%' }} placeholder="+91 9876543210" />
                </div>
              </div>
              <button type="submit" className="action-btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                Submit Blood Request
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
