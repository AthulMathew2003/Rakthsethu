import React, { useState, useEffect, useCallback } from 'react';
import {
  Menu,
  Bell,
  ChevronDown,
  Calendar,
  Users,
  ClipboardList,
  Droplet,
  Package,
  Activity,
  User,
  BarChart2,
  Settings,
  LogOut,
  Search,
  Filter,
  Eye,
  Edit2,
  Trash2,
  X,
  Loader2
} from 'lucide-react';
import {
  fetchDashboardStats,
  fetchDonors,
  createDonor,
  updateDonor,
  deleteDonorApi,
  logoutUser
} from './api.js';
import './Dashboard.css';

// Map iconType strings from API to actual Lucide components
const ICON_MAP = {
  Users: Users,
  ClipboardList: ClipboardList,
  Droplet: Droplet,
  Package: Package,
  User: User,
  Activity: Activity,
  BarChart2: BarChart2,
};

function getIconComponent(iconType) {
  const IconComp = ICON_MAP[iconType];
  return IconComp ? <IconComp size={20} className="stat-icon-svg" /> : <Package size={20} className="stat-icon-svg" />;
}

export default function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [inventoryPeriod, setInventoryPeriod] = useState('This Month');

  // ─── Dashboard Stats State (from API) ─────────────────────
  const [stats, setStats] = useState([]);
  const [donorStats, setDonorStats] = useState([]);
  const [inventoryData, setInventoryData] = useState([]);
  const [recentRequests, setRecentRequests] = useState([]);
  const [upcomingCamp, setUpcomingCamp] = useState(null);
  const [notificationCount, setNotificationCount] = useState(0);
  const [totalDonorsCount, setTotalDonorsCount] = useState(0);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState(null);

  // ─── Donors State (from API) ──────────────────────────────
  const [donorsList, setDonorsList] = useState([]);
  const [donorsLoading, setDonorsLoading] = useState(false);
  const [donorsError, setDonorsError] = useState(null);
  const [donorsTotalCount, setDonorsTotalCount] = useState(0);
  const [donorsTotalPages, setDonorsTotalPages] = useState(1);
  const [locations, setLocations] = useState(['All']);
  const [bloodGroups, setBloodGroups] = useState(['All', 'A+', 'A−', 'B+', 'B−', 'O+', 'O−', 'AB+', 'AB−']);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [groupFilter, setGroupFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [locationFilter, setLocationFilter] = useState('All');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal States
  const [isAddingDonor, setIsAddingDonor] = useState(false);
  const [viewingDonor, setViewingDonor] = useState(null);
  const [editingDonor, setEditingDonor] = useState(null);
  const [deletingDonorId, setDeletingDonorId] = useState(null);
  const [savingDonor, setSavingDonor] = useState(false);

  // Form State for Add/Edit
  const [donorForm, setDonorForm] = useState({
    name: '',
    group: 'O+',
    phone: '',
    email: '',
    location: '',
    lastDonation: '',
    status: 'Active'
  });

  const menuItems = [
    { name: 'Dashboard', icon: <ClipboardList size={18} /> },
    { name: 'Donors', icon: <Users size={18} /> },
    { name: 'Blood Requests', icon: <ClipboardList size={18} /> },
    { name: 'Donations', icon: <Droplet size={18} /> },
    { name: 'Blood Inventory', icon: <Package size={18} /> },
    { name: 'Camps / Events', icon: <Activity size={18} /> },
    { name: 'Users', icon: <User size={18} /> },
    { name: 'Reports', icon: <BarChart2 size={18} /> },
    { name: 'Settings', icon: <Settings size={18} /> }
  ];

  // ─── Fetch Dashboard Stats from API ───────────────────────
  const loadDashboardStats = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      const data = await fetchDashboardStats(inventoryPeriod);

      // Map stats cards with icons
      setStats(data.stats.map((s) => ({
        ...s,
        icon: getIconComponent(s.iconType),
      })));

      setDonorStats(data.donorStats.map((s) => ({
        ...s,
        icon: getIconComponent(s.iconType),
      })));

      setInventoryData(data.inventoryData);
      setRecentRequests(data.recentRequests);
      setUpcomingCamp(data.upcomingCamp);
      setTotalDonorsCount(data.totalDonorsCount);
      setNotificationCount(3); // Could come from a notifications endpoint
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
      setDashboardError(err.message);
    } finally {
      setDashboardLoading(false);
    }
  }, [inventoryPeriod]);

  useEffect(() => {
    loadDashboardStats();
  }, [loadDashboardStats]);

  // ─── Fetch Donors from API ────────────────────────────────
  const loadDonors = useCallback(async () => {
    setDonorsLoading(true);
    setDonorsError(null);
    try {
      const data = await fetchDonors({
        search: searchQuery,
        group: groupFilter,
        status: statusFilter,
        location: locationFilter,
        page: currentPage,
        limit: itemsPerPage,
      });

      // Map API donor fields to the shape used in the UI
      const mapped = data.items.map((d) => ({
        id: d.donor_code,
        dbId: d.id,
        name: d.name,
        group: d.blood_group,
        phone: d.phone,
        email: d.email,
        location: d.location,
        lastDonation: d.last_donation,
        status: d.status,
      }));

      setDonorsList(mapped);
      setDonorsTotalCount(data.total);
      setDonorsTotalPages(data.pages);
      if (data.locations && data.locations.length > 0) {
        setLocations(data.locations);
      }
      if (data.blood_groups && data.blood_groups.length > 0) {
        setBloodGroups(data.blood_groups);
      }
    } catch (err) {
      console.error('Failed to load donors:', err);
      setDonorsError(err.message);
    } finally {
      setDonorsLoading(false);
    }
  }, [searchQuery, groupFilter, statusFilter, locationFilter, currentPage, itemsPerPage]);

  useEffect(() => {
    if (activeTab === 'Donors') {
      loadDonors();
    }
  }, [activeTab, loadDonors]);

  // ─── Pagination ───────────────────────────────────────────
  const handlePageChange = (pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= donorsTotalPages) {
      setCurrentPage(pageNumber);
    }
  };

  // ─── Add / Edit submission handlers ───────────────────────
  const handleOpenAddModal = () => {
    setDonorForm({
      name: '',
      group: 'O+',
      phone: '',
      email: '',
      location: '',
      lastDonation: '',
      status: 'Active'
    });
    setIsAddingDonor(true);
  };

  const handleOpenEditModal = (donor) => {
    setDonorForm({
      name: donor.name,
      group: donor.group,
      phone: donor.phone,
      email: donor.email,
      location: donor.location,
      lastDonation: donor.lastDonation,
      status: donor.status,
    });
    setEditingDonor(donor);
  };

  const handleSaveDonor = async (e) => {
    e.preventDefault();
    if (!donorForm.name || !donorForm.phone || !donorForm.email || !donorForm.location) {
      alert('Please fill in all required fields.');
      return;
    }

    setSavingDonor(true);
    try {
      const apiPayload = {
        name: donorForm.name,
        blood_group: donorForm.group,
        phone: donorForm.phone,
        email: donorForm.email,
        location: donorForm.location,
        last_donation: donorForm.lastDonation || 'Never',
        status: donorForm.status || 'Active',
      };

      if (editingDonor) {
        await updateDonor(editingDonor.dbId, apiPayload);
        setEditingDonor(null);
      } else {
        await createDonor(apiPayload);
        setIsAddingDonor(false);
      }

      // Refresh donors list and dashboard stats
      await loadDonors();
      loadDashboardStats();
    } catch (err) {
      console.error('Failed to save donor:', err);
      alert(`Error saving donor: ${err.message}`);
    } finally {
      setSavingDonor(false);
    }
  };

  const handleDeleteDonor = async () => {
    const donor = donorsList.find((d) => d.id === deletingDonorId);
    if (!donor) {
      setDeletingDonorId(null);
      return;
    }

    try {
      await deleteDonorApi(donor.dbId);
      setDeletingDonorId(null);

      // Adjust current page if needed
      if (currentPage > 1 && donorsList.length === 1) {
        setCurrentPage((prev) => prev - 1);
      } else {
        await loadDonors();
      }
      loadDashboardStats();
    } catch (err) {
      console.error('Failed to delete donor:', err);
      alert(`Error deleting donor: ${err.message}`);
      setDeletingDonorId(null);
    }
  };

  const handleLogout = () => {
    logoutUser();
    onLogout();
  };

  // ─── Format today's date ──────────────────────────────────
  const todayFormatted = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="dashboard-wrapper">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo-container">
            <svg width="24" height="28" viewBox="0 0 28 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="brand-logo-svg">
              <defs>
                <linearGradient id="sidebar-logo-grad" x1="14" y1="1" x2="14" y2="31" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#FF3358" />
                  <stop offset="100%" stopColor="#C41230" />
                </linearGradient>
              </defs>
              <path d="M14 1C14 1 2 13 2 21C2 27.075 7.373 31 14 31C20.627 31 26 27.075 26 21C26 13 14 1 14 1Z" fill="url(#sidebar-logo-grad)" />
              <path d="M8 18C8 14 11 10 13.5 8" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.35" />
            </svg>
          </div>
          <div className="brand-text">
            <h2>Rakthasedu</h2>
            <p>Admin Dashboard</p>
          </div>
        </div>

        <nav className="sidebar-menu">
          {menuItems.map((item) => (
            <button
              key={item.name}
              className={`menu-btn ${activeTab === item.name ? 'active' : ''}`}
              onClick={() => {
                if (item.name === 'Dashboard' || item.name === 'Donors') {
                  setActiveTab(item.name);
                }
              }}
            >
              <span className="menu-icon">{item.icon}</span>
              <span className="menu-text">{item.name}</span>
            </button>
          ))}
          <button className="menu-btn logout-btn" onClick={handleLogout}>
            <span className="menu-icon"><LogOut size={18} /></span>
            <span className="menu-text">Log Out</span>
          </button>
        </nav>

        {/* Decorative Sidebar Bottom Graphic */}
        <div className="sidebar-footer-graphic">
          <div className="pulse-heart-container">
            <svg viewBox="0 0 100 80" className="heart-pulse-svg">
              <path d="M50,75 C50,75 85,45 85,25 C85,11.1928813 73.8071187,0 60,0 C52.5273766,0 45.8239019,3.27503732 41.2561917,8.44390558 C41.2561917,8.44390558 35,-5 20,-5 C8,-5 0,3 0,15 C0,30 35,60 50,75 Z" fill="#F43F5E" opacity="0.15" transform="scale(0.85) translate(8, 10)" />
              <path d="M12,40 C15,45 25,55 50,65 C75,55 85,45 88,40 C92,30 85,25 80,25 C75,25 70,30 50,42 C30,30 25,25 20,25 C15,25 8,30 12,40 Z" fill="#FFF" opacity="0.1" />
              <path d="M10,40 L30,40 L35,30 L40,55 L45,25 L50,45 L53,38 L58,40 L90,40" stroke="#FDA4AF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
          </div>
          <p className="footer-title">Every Drop Counts</p>
          <p className="footer-subtitle">Save a Life</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Header Section */}
        <header className="main-header">
          <div className="header-left">
            <button className="menu-toggle-btn" aria-label="Toggle Menu">
              <Menu size={22} />
            </button>
            <div className="header-greeting">
              {activeTab === 'Dashboard' ? (
                <>
                  <h1>Welcome back, {user?.name || 'Admin'} 🩸</h1>
                  <p>Here's what's happening with Rakthasedu today.</p>
                </>
              ) : (
                <>
                  <h1>Donors</h1>
                  <p>Manage and view all registered donors.</p>
                </>
              )}
            </div>
          </div>

          <div className="header-right">
            {/* Notification Bell */}
            <div className="notification-wrapper">
              <button className="icon-btn" aria-label="Notifications">
                <Bell size={20} />
                {notificationCount > 0 && (
                  <span className="notification-badge">{notificationCount}</span>
                )}
              </button>
            </div>

            {/* Profile Dropdown */}
            <div className="profile-dropdown">
              <div className="avatar-circle">
                <span>{(user?.name || 'A')[0]}</span>
              </div>
              <div className="profile-info">
                <span className="profile-name">{user?.name || 'Admin'}</span>
                <span className="profile-role">{user?.role || 'Admin'}</span>
              </div>
              <ChevronDown size={16} className="dropdown-arrow" />
            </div>

            {/* Date Selector */}
            <div className="date-picker-pill">
              <Calendar size={16} className="calendar-icon" />
              <span>{todayFormatted}</span>
            </div>
          </div>
        </header>

        {/* Tab-dependent Views */}
        {activeTab === 'Dashboard' ? (
          <>
            {/* Loading / Error States */}
            {dashboardLoading && (
              <div className="loading-overlay">
                <Loader2 size={32} className="spinner" />
                <span>Loading dashboard data...</span>
              </div>
            )}

            {dashboardError && (
              <div className="error-banner">
                <span>⚠️ Failed to load dashboard: {dashboardError}</span>
                <button onClick={loadDashboardStats} className="retry-btn">Retry</button>
              </div>
            )}

            {!dashboardLoading && !dashboardError && (
              <>
                {/* Dashboard Summary Stats Grid */}
                <section className="stats-grid">
                  {stats.map((stat, idx) => (
                    <div key={idx} className="stat-card">
                      <div className="stat-card-left">
                        <div className={`stat-icon-wrapper ${stat.colorClass}`}>
                          {stat.icon}
                        </div>
                      </div>
                      <div className="stat-card-right">
                        <span className="stat-card-title">{stat.title}</span>
                        <h3 className="stat-card-value">{stat.value}</h3>
                        {stat.growth && (
                          <span className="stat-card-growth growth-positive">{stat.growth}</span>
                        )}
                        {stat.status && (
                          <span className="stat-card-status status-sufficient">{stat.status}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </section>

                {/* Dashboard Visual Grid */}
                <div className="dashboard-grid">
                  {/* Left Column - Inventory and Upcoming Camps */}
                  <div className="grid-column-left">
                    {/* Blood Inventory Overview */}
                    <div className="content-card inventory-card">
                      <div className="card-header">
                        <div className="header-title-group">
                          <div className="card-icon-indicator indicator-red">
                            <Droplet size={16} fill="currentColor" />
                          </div>
                          <h3>Blood Inventory Overview</h3>
                        </div>
                        <div className="period-selector">
                          <select
                            value={inventoryPeriod}
                            onChange={(e) => setInventoryPeriod(e.target.value)}
                            className="period-dropdown"
                          >
                            <option value="This Month">This Month</option>
                            <option value="Last Month">Last Month</option>
                          </select>
                        </div>
                      </div>

                      <div className="card-body chart-body">
                        <div className="y-axis-label">Units</div>
                        <div className="chart-container">
                          <div className="chart-grid-lines">
                            <div className="grid-line" data-value="100"></div>
                            <div className="grid-line" data-value="80"></div>
                            <div className="grid-line" data-value="60"></div>
                            <div className="grid-line" data-value="40"></div>
                            <div className="grid-line" data-value="20"></div>
                            <div className="grid-line" data-value="0"></div>
                          </div>

                          <div className="chart-bars">
                            {inventoryData.map((data, index) => (
                              <div key={index} className="chart-bar-wrapper">
                                <div className="chart-bar-value-tooltip">{data.value}</div>
                                <div
                                  className="chart-bar"
                                  style={{ '--bar-height': `${data.value}%` }}
                                ></div>
                                <div className="chart-bar-label">{data.group}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="x-axis-label">Blood Groups</div>
                      </div>
                    </div>

                    {/* Upcoming Camp */}
                    <div className="content-card camp-card">
                      <div className="camp-card-content">
                        <div className="camp-icon-wrapper">
                          <Calendar size={20} className="camp-icon" />
                        </div>
                        <div className="camp-details">
                          <span className="camp-badge">Upcoming Camp</span>
                          <h4>{upcomingCamp?.title || 'No upcoming camps'}</h4>
                          <p>{upcomingCamp ? `${upcomingCamp.event_date} | ${upcomingCamp.time_slot}` : ''}</p>
                        </div>
                        <button className="view-details-btn">View Details</button>
                      </div>
                    </div>
                  </div>

                  {/* Right Column - Recent Blood Requests */}
                  <div className="grid-column-right">
                    <div className="content-card requests-card">
                      <div className="card-header">
                        <div className="header-title-group">
                          <div className="card-icon-indicator indicator-orange">
                            <ClipboardList size={16} />
                          </div>
                          <h3>Recent Blood Requests</h3>
                        </div>
                        <a href="#view-all" className="view-all-link" onClick={(e) => e.preventDefault()}>
                          View All
                        </a>
                      </div>

                      <div className="card-body table-body">
                        <div className="requests-list">
                          {recentRequests.length > 0 ? (
                            recentRequests.map((req, index) => (
                              <div key={req.id || index} className="request-row">
                                <div className="request-blood-badge">
                                  <span>{req.group}</span>
                                </div>
                                <div className="request-patient-info">
                                  <span className="patient-name">{req.name}</span>
                                </div>
                                <div className="request-location">
                                  <span className="location-text">{req.location}</span>
                                </div>
                                <div className="request-time">
                                  <span className="time-text">{req.time}</span>
                                </div>
                                <div className="request-status">
                                  <span className={`status-pill ${req.statusClass}`}>{req.status}</span>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="no-records-cell" style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
                              No recent blood requests found.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom CTA Banner */}
                <section className="bottom-cta-banner">
                  <div className="cta-left">
                    <div className="cta-icon-wrapper">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="cta-icon">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        <path d="M12 8v8" />
                        <path d="M8 12h8" />
                      </svg>
                    </div>
                    <div className="cta-text">
                      <h3>Be a Hero, Donate Blood</h3>
                      <p>Your support can save countless lives.</p>
                    </div>
                  </div>
                  <div className="cta-right">
                    <button className="cta-button">
                      Add New Request
                    </button>
                  </div>
                </section>
              </>
            )}
          </>
        ) : (
          <>
            {/* Donors Page Summary Stats Grid */}
            <section className="stats-grid">
              {donorStats.map((stat, idx) => (
                <div key={idx} className="stat-card">
                  <div className="stat-card-left">
                    <div className={`stat-icon-wrapper ${stat.colorClass}`}>
                      {stat.icon}
                    </div>
                  </div>
                  <div className="stat-card-right">
                    <span className="stat-card-title">{stat.title}</span>
                    <h3 className="stat-card-value">{stat.value}</h3>
                    {stat.growth && (
                      <span className="stat-card-growth growth-positive">{stat.growth}</span>
                    )}
                  </div>
                </div>
              ))}
            </section>

            {/* Search & Filter Toolbar */}
            <section className="filters-toolbar">
              <div className="search-box-wrapper">
                <Search size={18} className="search-icon-input" />
                <input
                  type="text"
                  placeholder="Search donors by name, phone, email or blood group..."
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
                    value={groupFilter}
                    onChange={(e) => {
                      setGroupFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="toolbar-select"
                  >
                    <option value="All">All Blood Groups</option>
                    {bloodGroups.filter(g => g !== 'All').map(g => (
                      <option key={g} value={g}>{g}</option>
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
                    <option value="All">All Status</option>
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>

                <div className="filter-select-wrapper">
                  <select
                    value={locationFilter}
                    onChange={(e) => {
                      setLocationFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="toolbar-select"
                  >
                    <option value="All">All Locations</option>
                    {locations.filter(loc => loc !== 'All').map(loc => (
                      <option key={loc} value={loc}>{loc}</option>
                    ))}
                  </select>
                </div>

                <button className="add-donor-btn" onClick={handleOpenAddModal}>
                  + Add New Donor
                </button>
              </div>
            </section>

            {/* Donor Records Table */}
            <section className="content-card table-card">
              {donorsLoading && (
                <div className="loading-overlay" style={{ position: 'relative', minHeight: '200px' }}>
                  <Loader2 size={28} className="spinner" />
                  <span>Loading donors...</span>
                </div>
              )}

              {donorsError && (
                <div className="error-banner">
                  <span>⚠️ Failed to load donors: {donorsError}</span>
                  <button onClick={loadDonors} className="retry-btn">Retry</button>
                </div>
              )}

              {!donorsLoading && !donorsError && (
                <>
                  <div className="table-responsive-container">
                    <table className="donors-table">
                      <thead>
                        <tr>
                          <th>Donor ID</th>
                          <th>Name</th>
                          <th>Blood Group</th>
                          <th>Phone</th>
                          <th>Email</th>
                          <th>Location</th>
                          <th>Last Donation</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {donorsList.length > 0 ? (
                          donorsList.map((donor) => (
                            <tr key={donor.id}>
                              <td className="donor-id-cell">{donor.id}</td>
                              <td className="donor-name-cell">{donor.name}</td>
                              <td>
                                <span className="blood-group-badge">{donor.group}</span>
                              </td>
                              <td className="donor-phone-cell">{donor.phone}</td>
                              <td className="donor-email-cell">{donor.email}</td>
                              <td>{donor.location}</td>
                              <td>{donor.lastDonation}</td>
                              <td>
                                <span className={`status-pill-badge ${donor.status === 'Active' ? 'active-badge' : 'inactive-badge'}`}>
                                  {donor.status}
                                </span>
                              </td>
                              <td>
                                <div className="actions-cell-wrapper">
                                  <button
                                    className="action-icon-btn view"
                                    onClick={() => setViewingDonor(donor)}
                                    title="View Details"
                                  >
                                    <Eye size={16} />
                                  </button>
                                  <button
                                    className="action-icon-btn edit"
                                    onClick={() => handleOpenEditModal(donor)}
                                    title="Edit Donor"
                                  >
                                    <Edit2 size={16} />
                                  </button>
                                  <button
                                    className="action-icon-btn delete"
                                    onClick={() => setDeletingDonorId(donor.id)}
                                    title="Delete Donor"
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan="9" className="no-records-cell">
                              No donors found matching the filters.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Table Footer / Pagination */}
                  <div className="table-footer">
                    <div className="footer-info-text">
                      Showing {donorsTotalCount > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, donorsTotalCount)} of {donorsTotalCount} donors
                    </div>
                    <div className="pagination-controls">
                      <button
                        className="pagination-btn"
                        disabled={currentPage === 1}
                        onClick={() => handlePageChange(currentPage - 1)}
                      >
                        Previous
                      </button>
                      
                      {Array.from({ length: donorsTotalPages }, (_, index) => {
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
                        disabled={currentPage === donorsTotalPages}
                        onClick={() => handlePageChange(currentPage + 1)}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </>
              )}
            </section>
          </>
        )}
      </main>

      {/* --- Modals for CRUD operations --- */}

      {/* Add / Edit Donor Modal */}
      {(isAddingDonor || editingDonor) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingDonor ? 'Edit Donor Details' : 'Add New Donor'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingDonor(false);
                  setEditingDonor(null);
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveDonor} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="modal-name">Full Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="modal-name"
                    value={donorForm.name}
                    onChange={(e) => setDonorForm({ ...donorForm, name: e.target.value })}
                    required
                    placeholder="Enter full name"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-group">Blood Group <span className="req-star">*</span></label>
                  <select
                    id="modal-group"
                    value={donorForm.group}
                    onChange={(e) => setDonorForm({ ...donorForm, group: e.target.value })}
                  >
                    {bloodGroups.filter(g => g !== 'All').map(g => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-phone">Phone Number <span className="req-star">*</span></label>
                  <input
                    type="tel"
                    id="modal-phone"
                    value={donorForm.phone}
                    onChange={(e) => setDonorForm({ ...donorForm, phone: e.target.value })}
                    required
                    placeholder="+91 XXXXX XXXXX"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-email">Email Address <span className="req-star">*</span></label>
                  <input
                    type="email"
                    id="modal-email"
                    value={donorForm.email}
                    onChange={(e) => setDonorForm({ ...donorForm, email: e.target.value })}
                    required
                    placeholder="example@gmail.com"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-location">Location <span className="req-star">*</span></label>
                  <select
                    id="modal-location"
                    value={donorForm.location}
                    onChange={(e) => setDonorForm({ ...donorForm, location: e.target.value })}
                    required
                  >
                    <option value="">Select Location</option>
                    {locations.filter(loc => loc !== 'All').map(loc => (
                      <option key={loc} value={loc}>{loc}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-last-donation">Last Donation Date</label>
                  <input
                    type="text"
                    id="modal-last-donation"
                    value={donorForm.lastDonation}
                    onChange={(e) => setDonorForm({ ...donorForm, lastDonation: e.target.value })}
                    placeholder="e.g. 15 Jun 2025"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="modal-status">Status</label>
                  <select
                    id="modal-status"
                    value={donorForm.status}
                    onChange={(e) => setDonorForm({ ...donorForm, status: e.target.value })}
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer-actions">
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => {
                    setIsAddingDonor(false);
                    setEditingDonor(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn" disabled={savingDonor}>
                  {savingDonor ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Donor Modal */}
      {viewingDonor && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Donor Information File</h3>
              <button className="modal-close-btn" onClick={() => setViewingDonor(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large">
                <span>{viewingDonor.group}</span>
              </div>
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Donor ID</span>
                  <span className="detail-val font-semibold">{viewingDonor.id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Full Name</span>
                  <span className="detail-val font-semibold">{viewingDonor.name}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Blood Group</span>
                  <span className="detail-val font-semibold text-rose-red">{viewingDonor.group}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Phone Number</span>
                  <span className="detail-val">{viewingDonor.phone}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Email Address</span>
                  <span className="detail-val">{viewingDonor.email}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Location</span>
                  <span className="detail-val">{viewingDonor.location}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Last Donation</span>
                  <span className="detail-val">{viewingDonor.lastDonation || 'Never'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className={`status-pill-badge ${viewingDonor.status === 'Active' ? 'active-badge' : 'inactive-badge'}`}>
                    {viewingDonor.status}
                  </span>
                </div>
              </div>
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingDonor(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Donor Confirmation Modal */}
      {deletingDonorId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingDonorId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <p>Are you sure you want to permanently delete donor record <strong>{deletingDonorId}</strong>?</p>
              <p className="sub-warning">This action is irreversible and will remove all history associated with this donor.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingDonorId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteDonor}>
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
