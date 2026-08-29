import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  Droplet,
  Package,
  Calendar,
  ShieldAlert,
  Sliders,
  AlertTriangle,
  Info
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
const COMPONENTS = ['Whole Blood', 'Packed RBC', 'Plasma', 'Platelets', 'Cryoprecipitate'];
const STATUSES = ['Available', 'Low Stock', 'Critical', 'Reserved', 'Expired'];

const LOW_STOCK_THRESHOLD = 10;
const CRITICAL_STOCK_THRESHOLD = 4;

// Helper to determine stock status from quantities
function determineStockStatus(availableUnits, expiryDateStr) {
  const today = new Date('2026-08-22');
  const expiry = new Date(expiryDateStr);
  if (expiry < today) {
    return 'Expired';
  }
  if (availableUnits === 0) return 'Critical';
  if (availableUnits <= CRITICAL_STOCK_THRESHOLD) return 'Critical';
  if (availableUnits <= LOW_STOCK_THRESHOLD) return 'Low Stock';
  return 'Available';
}

// Helper to check if expiring soon (<= 7 days from today 2026-08-22)
function getExpiryWarning(expiryDateStr) {
  const today = new Date('2026-08-22');
  const expiry = new Date(expiryDateStr);
  const diffTime = expiry.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'Expired';
  if (diffDays <= 7) return 'Expiring Soon';
  return 'Good';
}

function getStatusStyles(status) {
  switch (status) {
    case 'Available':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // green
    case 'Low Stock':
      return { bg: '#FFFBEB', text: '#D97706', border: '#FDE68A' }; // amber
    case 'Critical':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    case 'Reserved':
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' }; // gray
    case 'Expired':
      return { bg: '#F8FAFC', text: '#64748B', border: '#E2E8F0' }; // slate
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

export default function BloodInventoryPage({
  inventory,
  onAddStock,
  onEditStock,
  onDeleteStock,
  onAdjustStock
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [bloodGroupFilter, setBloodGroupFilter] = useState('All');
  const [componentFilter, setComponentFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal states
  const [isAddingStock, setIsAddingStock] = useState(false);
  const [viewingItem, setViewingItem] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [adjustingItem, setAdjustingItem] = useState(null);
  const [deletingItemId, setDeletingItemId] = useState(null);

  // Form State
  const [stockForm, setStockForm] = useState({
    bloodGroup: 'O+',
    component: 'Whole Blood',
    availableUnits: 10,
    reservedUnits: 0,
    collectionDate: '',
    expiryDate: '',
    storageLocation: '',
    notes: ''
  });

  // Adjustment State
  const [adjustmentForm, setAdjustmentForm] = useState({
    type: 'add', // 'add' or 'remove'
    quantity: 1,
    reason: ''
  });

  const resetForm = () => {
    setStockForm({
      bloodGroup: 'O+',
      component: 'Whole Blood',
      availableUnits: 10,
      reservedUnits: 0,
      collectionDate: '',
      expiryDate: '',
      storageLocation: '',
      notes: ''
    });
  };

  const handleOpenAddModal = () => {
    resetForm();
    setIsAddingStock(true);
  };

  const handleOpenEditModal = (item) => {
    setStockForm({
      bloodGroup: item.bloodGroup,
      component: item.component,
      availableUnits: item.availableUnits,
      reservedUnits: item.reservedUnits,
      collectionDate: item.collectionDate,
      expiryDate: item.expiryDate,
      storageLocation: item.storageLocation,
      notes: item.notes || ''
    });
    setEditingItem(item);
  };

  const handleSaveStockSubmit = (e) => {
    e.preventDefault();
    if (
      !stockForm.bloodGroup ||
      !stockForm.component ||
      stockForm.availableUnits === undefined ||
      !stockForm.collectionDate ||
      !stockForm.expiryDate ||
      !stockForm.storageLocation
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const available = parseInt(stockForm.availableUnits, 10);
    const reserved = parseInt(stockForm.reservedUnits || 0, 10);

    const stockData = {
      bloodGroup: stockForm.bloodGroup,
      component: stockForm.component,
      availableUnits: available,
      reservedUnits: reserved,
      totalUnits: available + reserved,
      collectionDate: stockForm.collectionDate,
      expiryDate: stockForm.expiryDate,
      storageLocation: stockForm.storageLocation,
      status: determineStockStatus(available, stockForm.expiryDate),
      notes: stockForm.notes
    };

    if (editingItem) {
      onEditStock({
        ...stockData,
        id: editingItem.id,
        dbId: editingItem.dbId
      });
      setEditingItem(null);
    } else {
      onAddStock(stockData);
      setIsAddingStock(false);
    }
    resetForm();
  };

  const handleAdjustStockSubmit = (e) => {
    e.preventDefault();
    if (!adjustingItem || adjustmentForm.quantity <= 0) return;

    const delta = adjustmentForm.type === 'add' ? adjustmentForm.quantity : -adjustmentForm.quantity;
    let newAvailable = adjustingItem.availableUnits + delta;
    if (newAvailable < 0) {
      alert('Available stock units cannot drop below zero.');
      return;
    }

    onAdjustStock(adjustingItem.id, newAvailable, adjustmentForm.reason);
    setAdjustingItem(null);
    setAdjustmentForm({ type: 'add', quantity: 1, reason: '' });
  };

  const handleDeleteStockConfirm = () => {
    if (deletingItemId) {
      onDeleteStock(deletingItemId);
      setDeletingItemId(null);

      const filtered = filteredInventory();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // Client-side filtering logic
  const filteredInventory = () => {
    return inventory.filter((item) => {
      const status = determineStockStatus(item.availableUnits, item.expiryDate);
      const matchesSearch =
        item.bloodGroup.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.component.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.storageLocation.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesBloodGroup = bloodGroupFilter === 'All' || item.bloodGroup === bloodGroupFilter;
      const matchesComponent = componentFilter === 'All' || item.component === componentFilter;
      const matchesStatus = statusFilter === 'All' || status === statusFilter;

      return matchesSearch && matchesBloodGroup && matchesComponent && matchesStatus;
    });
  };

  const filteredList = filteredInventory();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // Page slice
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedInventory = filteredList.slice(startIndex, startIndex + itemsPerPage);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Statistical calculations
  const totalBloodUnits = inventory.reduce((sum, item) => sum + (item.availableUnits + item.reservedUnits), 0);
  const availableBloodUnits = inventory.reduce((sum, item) => sum + item.availableUnits, 0);
  const lowStockCount = inventory.filter(item => {
    const status = determineStockStatus(item.availableUnits, item.expiryDate);
    return status === 'Low Stock' || status === 'Critical';
  }).length;
  const expiringSoonCount = inventory.filter(item => {
    const warning = getExpiryWarning(item.expiryDate);
    return warning === 'Expiring Soon' || warning === 'Expired';
  }).length;

  // Calculate available units per blood group
  const groupTotals = {};
  BLOOD_GROUPS.forEach(g => { groupTotals[g] = 0; });
  inventory.forEach(item => {
    groupTotals[item.bloodGroup] += item.availableUnits;
  });

  // Identify critically low groups (total units <= 4)
  const criticalGroups = Object.keys(groupTotals).filter(g => groupTotals[g] <= CRITICAL_STOCK_THRESHOLD);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', width: '100%' }}>
      
      {/* Critical Stock Alert Banner */}
      {criticalGroups.length > 0 && (
        <div style={{
          backgroundColor: '#FFF1F2',
          border: '1px solid #FECDD3',
          borderRadius: '12px',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          boxShadow: 'var(--card-shadow)'
        }}>
          <div style={{
            backgroundColor: '#FDA4AF',
            color: '#E11D48',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <ShieldAlert size={22} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <h4 style={{ margin: 0, color: '#9F1239', fontSize: '0.95rem', fontWeight: '700' }}>Low Stock Alert</h4>
            <p style={{ margin: 0, color: '#BE123C', fontSize: '0.9rem' }}>
              <strong>{criticalGroups.join(', ')}</strong> blood stock is critically low. Please schedule immediate camps or requests.
            </p>
          </div>
        </div>
      )}

      {/* Inventory Stat Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-donors">
              <Droplet size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Total Blood Units</span>
            <h3 className="stat-card-value">{totalBloodUnits} U</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-inventory">
              <Package size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Available Units</span>
            <h3 className="stat-card-value" style={{ color: '#059669' }}>{availableBloodUnits} U</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-requests">
              <AlertTriangle size={20} className="stat-icon-svg" style={{ color: '#ea580c' }} />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Low / Critical Batches</span>
            <h3 className="stat-card-value" style={{ color: '#ea580c' }}>{lowStockCount}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-units">
              <Calendar size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Expiring / Expired</span>
            <h3 className="stat-card-value" style={{ color: '#e11d48' }}>{expiringSoonCount}</h3>
          </div>
        </div>
      </section>

      {/* Blood Group Overview Section */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--muted-text)', margin: '0' }}>Blood Group Available Overview</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
          {BLOOD_GROUPS.map(group => {
            const units = groupTotals[group];
            const maxCapacity = 50; // Mock reference for progress bar sizing
            const percentage = Math.min((units / maxCapacity) * 100, 100);
            
            // Determine progress color
            let progressColor = '#059669'; // Green (Good)
            if (units <= CRITICAL_STOCK_THRESHOLD) progressColor = '#e11d48'; // Red (Critical)
            else if (units <= LOW_STOCK_THRESHOLD) progressColor = '#ea580c'; // Orange (Low)

            return (
              <div key={group} style={{
                backgroundColor: 'var(--white)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '14px 18px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                boxShadow: 'var(--card-shadow)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--dark-text)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: progressColor }}></span>
                    {group}
                  </span>
                  <span style={{ fontSize: '0.95rem', fontWeight: '700', color: progressColor }}>
                    {units} Units
                  </span>
                </div>
                {/* Progress bar container */}
                <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${percentage}%`, height: '100%', backgroundColor: progressColor, borderRadius: '4px', transition: 'width 0.3s ease' }}></div>
                </div>
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
            placeholder="Search stock by group, component, location, ID..."
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
              value={componentFilter}
              onChange={(e) => {
                setComponentFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="toolbar-select"
            >
              <option value="All">All Components</option>
              {COMPONENTS.map(c => (
                <option key={c} value={c}>{c}</option>
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
            + Add Blood Stock
          </button>
        </div>
      </section>

      {/* Inventory Table */}
      <section className="content-card table-card">
        <div className="table-responsive-container">
          <table className="donors-table">
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Blood Group</th>
                <th>Component</th>
                <th>Available Units</th>
                <th>Reserved Units</th>
                <th>Total Units</th>
                <th>Collection Date</th>
                <th>Expiry Date</th>
                <th>Storage Location</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedInventory.length > 0 ? (
                paginatedInventory.map((item) => {
                  const status = determineStockStatus(item.availableUnits, item.expiryDate);
                  const statusColors = getStatusStyles(status);
                  const expiryWarning = getExpiryWarning(item.expiryDate);

                  return (
                    <tr key={item.id}>
                      <td className="donor-id-cell font-semibold">{item.id}</td>
                      <td>
                        <span className="blood-group-badge">{item.bloodGroup}</span>
                      </td>
                      <td>{item.component}</td>
                      <td style={{ textAlign: 'center', fontWeight: '700' }}>{item.availableUnits}</td>
                      <td style={{ textAlign: 'center', color: '#64748b' }}>{item.reservedUnits}</td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>{item.availableUnits + item.reservedUnits}</td>
                      <td>{item.collectionDate}</td>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          {item.expiryDate}
                          {expiryWarning === 'Expired' && (
                            <span style={{ color: '#e11d48', fontSize: '0.75rem', fontWeight: '700' }}>(Expired)</span>
                          )}
                          {expiryWarning === 'Expiring Soon' && (
                            <span style={{ color: '#ea580c', fontSize: '0.75rem', fontWeight: '700' }}>(Expiring)</span>
                          )}
                        </span>
                      </td>
                      <td>{item.storageLocation}</td>
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
                          {status}
                        </span>
                      </td>
                      <td>
                        <div className="actions-cell-wrapper">
                          <button
                            className="action-icon-btn view"
                            onClick={() => setViewingItem(item)}
                            title="View Details"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            className="action-icon-btn edit"
                            onClick={() => handleOpenEditModal(item)}
                            title="Edit Record"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            className="action-icon-btn edit"
                            style={{ color: 'var(--primary-rose)' }}
                            onClick={() => {
                              setAdjustingItem(item);
                              setAdjustmentForm({ type: 'add', quantity: 1, reason: '' });
                            }}
                            title="Adjust Stock Quantity"
                          >
                            <Sliders size={16} />
                          </button>
                          <button
                            className="action-icon-btn delete"
                            onClick={() => setDeletingItemId(item.id)}
                            title="Delete Batch"
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
                  <td colSpan="11" className="no-records-cell">
                    No blood inventory batches found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer / Pagination */}
        <div className="table-footer">
          <div className="footer-info-text">
            Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} batches
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

      {/* --- Add / Edit Inventory Modal --- */}
      {(isAddingStock || editingItem) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingItem ? 'Edit Blood Stock Record' : 'Add Blood Stock Batch'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsAddingStock(false);
                  setEditingItem(null);
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveStockSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item">
                  <label htmlFor="inv-group">Blood Group <span className="req-star">*</span></label>
                  <select
                    id="inv-group"
                    value={stockForm.bloodGroup}
                    onChange={(e) => setStockForm({ ...stockForm, bloodGroup: e.target.value })}
                    required
                  >
                    {BLOOD_GROUPS.map(g => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="inv-component">Blood Component <span className="req-star">*</span></label>
                  <select
                    id="inv-component"
                    value={stockForm.component}
                    onChange={(e) => setStockForm({ ...stockForm, component: e.target.value })}
                    required
                  >
                    {COMPONENTS.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="inv-avail">Available Units <span className="req-star">*</span></label>
                  <input
                    type="number"
                    min="0"
                    id="inv-avail"
                    value={stockForm.availableUnits}
                    onChange={(e) => setStockForm({ ...stockForm, availableUnits: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="inv-res">Reserved Units</label>
                  <input
                    type="number"
                    min="0"
                    id="inv-res"
                    value={stockForm.reservedUnits}
                    onChange={(e) => setStockForm({ ...stockForm, reservedUnits: e.target.value })}
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="inv-col-date">Collection Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="inv-col-date"
                    value={stockForm.collectionDate}
                    onChange={(e) => setStockForm({ ...stockForm, collectionDate: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="inv-exp-date">Expiry Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="inv-exp-date"
                    value={stockForm.expiryDate}
                    onChange={(e) => setStockForm({ ...stockForm, expiryDate: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="inv-loc">Storage Location <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="inv-loc"
                    value={stockForm.storageLocation}
                    onChange={(e) => setStockForm({ ...stockForm, storageLocation: e.target.value })}
                    required
                    placeholder="e.g. Blood Bank A - Rack 03"
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="inv-notes">Additional Notes</label>
                  <textarea
                    id="inv-notes"
                    value={stockForm.notes}
                    onChange={(e) => setStockForm({ ...stockForm, notes: e.target.value })}
                    placeholder="Add batch info, lab technician observations..."
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
                    setIsAddingStock(false);
                    setEditingItem(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingItem ? 'Save Changes' : 'Add Stock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Stock Details Modal --- */}
      {viewingItem && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Inventory Batch Profile</h3>
              <button className="modal-close-btn" onClick={() => setViewingItem(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              <div className="donor-card-badge-large" style={{ backgroundColor: '#EEF2F6', color: '#1E293B' }}>
                <Package size={24} />
              </div>
              <h4 style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 20px 0', color: 'var(--dark-text)' }}>
                Batch {viewingItem.id}
              </h4>
              
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Blood Group</span>
                  <span className="detail-val font-semibold" style={{ color: 'var(--primary-rose)' }}>
                    {viewingItem.bloodGroup}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Blood Component</span>
                  <span className="detail-val font-semibold">{viewingItem.component}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Available Units</span>
                  <span className="detail-val font-bold" style={{ color: '#059669' }}>{viewingItem.availableUnits} Units</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Reserved Units</span>
                  <span className="detail-val font-semibold" style={{ color: '#64748b' }}>{viewingItem.reservedUnits} Units</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Total Units</span>
                  <span className="detail-val font-bold">{viewingItem.availableUnits + viewingItem.reservedUnits} Units</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Storage Location</span>
                  <span className="detail-val">{viewingItem.storageLocation}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Collection Date</span>
                  <span className="detail-val">{viewingItem.collectionDate}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Expiry Date</span>
                  <span className="detail-val">{viewingItem.expiryDate}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Status</span>
                  <span className="detail-val">
                    <span style={{
                      backgroundColor: getStatusStyles(determineStockStatus(viewingItem.availableUnits, viewingItem.expiryDate)).bg,
                      color: getStatusStyles(determineStockStatus(viewingItem.availableUnits, viewingItem.expiryDate)).text,
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {determineStockStatus(viewingItem.availableUnits, viewingItem.expiryDate)}
                    </span>
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Remarks & Notes</span>
                  <span className="detail-val" style={{ whiteSpace: 'pre-wrap', fontStyle: viewingItem.notes ? 'normal' : 'italic' }}>
                    {viewingItem.notes || 'No batch notes provided.'}
                  </span>
                </div>
              </div>
              
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingItem(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Stock Adjustment Modal --- */}
      {adjustingItem && (
        <div className="modal-overlay">
          <div className="modal-content-card" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3>Adjust Stock Quantity</h3>
              <button
                className="modal-close-btn"
                onClick={() => setAdjustingItem(null)}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleAdjustStockSubmit} className="modal-form">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ padding: '12px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <p style={{ margin: '0 0 6px 0', fontSize: '0.85rem', color: '#64748b' }}>Batch: <strong>{adjustingItem.id}</strong> ({adjustingItem.bloodGroup} - {adjustingItem.component})</p>
                  <p style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--dark-text)' }}>Current Available Units: <span style={{ color: 'var(--primary-rose)' }}>{adjustingItem.availableUnits}</span></p>
                </div>

                <div className="form-group-item">
                  <label>Adjustment Type</label>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="adj-type"
                        value="add"
                        checked={adjustmentForm.type === 'add'}
                        onChange={() => setAdjustmentForm({ ...adjustmentForm, type: 'add' })}
                      />
                      + Add Units
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="adj-type"
                        value="remove"
                        checked={adjustmentForm.type === 'remove'}
                        onChange={() => setAdjustmentForm({ ...adjustmentForm, type: 'remove' })}
                      />
                      - Remove Units
                    </label>
                  </div>
                </div>

                <div className="form-group-item">
                  <label htmlFor="adj-qty">Units Quantity</label>
                  <input
                    type="number"
                    min="1"
                    id="adj-qty"
                    value={adjustmentForm.quantity}
                    onChange={(e) => setAdjustmentForm({ ...adjustmentForm, quantity: parseInt(e.target.value, 10) || 1 })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="adj-reason">Reason / Justification</label>
                  <input
                    type="text"
                    id="adj-reason"
                    value={adjustmentForm.reason}
                    onChange={(e) => setAdjustmentForm({ ...adjustmentForm, reason: e.target.value })}
                    placeholder="e.g. Blood donation received / damaged vial"
                    required
                  />
                </div>
              </div>

              <div className="modal-footer-actions" style={{ marginTop: '24px' }}>
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={() => setAdjustingItem(null)}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  Confirm Adjustment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingItemId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingItemId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Delete Inventory Batch</strong>
              </div>
              <p>Are you sure you want to delete blood inventory record <strong>{deletingItemId}</strong>? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingItemId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteStockConfirm}>
                  Delete Batch
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
