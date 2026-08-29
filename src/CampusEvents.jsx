import React, { useState } from 'react';
import {
  Search,
  Eye,
  Edit2,
  Trash2,
  X,
  Calendar,
  Clock,
  MapPin,
  Users,
  ShieldAlert,
  Info,
  Layers,
  Phone,
  Image as ImageIcon
} from 'lucide-react';

const EVENT_TYPES = [
  'Blood Donation',
  'Health Camp',
  'Awareness Program',
  'Volunteer Activity',
  'Fundraising',
  'Community Service',
  'Workshop',
  'Seminar',
  'Other'
];

const STATUSES = ['Draft', 'Upcoming', 'Ongoing', 'Completed', 'Cancelled'];

function getStatusStyles(status) {
  switch (status) {
    case 'Draft':
      return { bg: '#F1F5F9', text: '#475569', border: '#CBD5E1' }; // slate
    case 'Upcoming':
      return { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' }; // blue
    case 'Ongoing':
      return { bg: '#FFFBEB', text: '#D97706', border: '#FDE68A' }; // amber
    case 'Completed':
      return { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' }; // emerald
    case 'Cancelled':
      return { bg: '#FEF2F2', text: '#DC2626', border: '#FCA5A5' }; // red
    default:
      return { bg: '#F3F4F6', text: '#374151', border: '#E5E7EB' };
  }
}

export default function CampusEventsPage({
  events,
  onCreateEvent,
  onEditEvent,
  onDeleteEvent,
  onStatusChange
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'calendar'

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 7;

  // Modal states
  const [isCreatingEvent, setIsCreatingEvent] = useState(false);
  const [viewingEvent, setViewingEvent] = useState(null);
  const [editingEvent, setEditingEvent] = useState(null);
  const [deletingEventId, setDeletingEventId] = useState(null);

  // Form State
  const [eventForm, setEventForm] = useState({
    title: '',
    type: 'Blood Donation',
    date: '',
    startTime: '',
    endTime: '',
    venue: '',
    organizer: '',
    maxParticipants: 100,
    description: '',
    contactNumber: '',
    registrationRequired: false,
    registrationDeadline: '',
    imageBanner: '',
    status: 'Upcoming'
  });

  const resetForm = () => {
    setEventForm({
      title: '',
      type: 'Blood Donation',
      date: '',
      startTime: '',
      endTime: '',
      venue: '',
      organizer: '',
      maxParticipants: 100,
      description: '',
      contactNumber: '',
      registrationRequired: false,
      registrationDeadline: '',
      imageBanner: '',
      status: 'Upcoming'
    });
  };

  const handleOpenCreateModal = () => {
    resetForm();
    setIsCreatingEvent(true);
  };

  const handleOpenEditModal = (evt) => {
    setEventForm({
      title: evt.title,
      type: evt.type,
      date: evt.date,
      startTime: evt.startTime,
      endTime: evt.endTime || '',
      venue: evt.venue,
      organizer: evt.organizer,
      maxParticipants: evt.maxParticipants || 100,
      description: evt.description || '',
      contactNumber: evt.contactNumber || '',
      registrationRequired: evt.registrationRequired || false,
      registrationDeadline: evt.registrationDeadline || '',
      imageBanner: evt.imageBanner || '',
      status: evt.status || 'Upcoming'
    });
    setEditingEvent(evt);
  };

  const handleSaveEventSubmit = (e) => {
    e.preventDefault();
    if (
      !eventForm.title ||
      !eventForm.type ||
      !eventForm.date ||
      !eventForm.startTime ||
      !eventForm.venue ||
      !eventForm.organizer ||
      !eventForm.status
    ) {
      alert('Please fill in all required fields.');
      return;
    }

    const eventData = {
      title: eventForm.title,
      type: eventForm.type,
      date: eventForm.date,
      startTime: eventForm.startTime,
      endTime: eventForm.endTime,
      venue: eventForm.venue,
      organizer: eventForm.organizer,
      maxParticipants: parseInt(eventForm.maxParticipants, 10),
      description: eventForm.description,
      contactNumber: eventForm.contactNumber,
      registrationRequired: eventForm.registrationRequired,
      registrationDeadline: eventForm.registrationDeadline,
      imageBanner: eventForm.imageBanner,
      status: eventForm.status,
      participants: editingEvent ? editingEvent.participants : 0
    };

    if (editingEvent) {
      onEditEvent({
        ...eventData,
        id: editingEvent.id,
        dbId: editingEvent.dbId
      });
      setEditingEvent(null);
    } else {
      onCreateEvent(eventData);
      setIsCreatingEvent(false);
    }
    resetForm();
  };

  const handleDeleteEventConfirm = () => {
    if (deletingEventId) {
      onDeleteEvent(deletingEventId);
      setDeletingEventId(null);

      const filtered = filteredEvents();
      const newTotalPages = Math.ceil((filtered.length - 1) / itemsPerPage);
      if (currentPage > 1 && currentPage > newTotalPages) {
        setCurrentPage(newTotalPages);
      }
    }
  };

  // Client-side filtering logic
  const filteredEvents = () => {
    return events.filter((evt) => {
      const matchesSearch =
        evt.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.venue.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evt.organizer.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesType = eventTypeFilter === 'All' || evt.type === eventTypeFilter;
      const matchesStatus = statusFilter === 'All' || evt.status === statusFilter;

      return matchesSearch && matchesType && matchesStatus;
    });
  };

  const filteredList = filteredEvents();
  const totalItems = filteredList.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;

  // Page slice for list view
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedEvents = filteredList.slice(startIndex, startIndex + itemsPerPage);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Statistics calculation
  const totalEvents = events.length;
  const upcomingEvents = events.filter(e => e.status === 'Upcoming').length;
  const ongoingEvents = events.filter(e => e.status === 'Ongoing').length;
  const completedEvents = events.filter(e => e.status === 'Completed').length;

  // Sort upcoming events nearest first (comparing date strings)
  const nearestUpcoming = events
    .filter(e => e.status === 'Upcoming')
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .slice(0, 3);

  // Custom Monthly Calendar builder (renders September 2026)
  const renderCalendarMonth = () => {
    const totalDays = 30; // September has 30 days
    const startOffset = 2; // Sept 1, 2026 is Tuesday (Sun=0, Mon=1, Tue=2...)
    const daysArray = [];

    for (let i = 0; i < startOffset; i++) {
      daysArray.push(null);
    }
    for (let i = 1; i <= totalDays; i++) {
      daysArray.push(i);
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: 'var(--dark-text)', textAlign: 'center' }}>
          September 2026
        </h3>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: '8px',
          backgroundColor: 'var(--white)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '16px',
          boxShadow: 'var(--card-shadow)'
        }}>
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
            <div key={d} style={{ fontWeight: '700', textAlign: 'center', paddingBottom: '8px', borderBottom: '2px solid var(--border-color)', color: 'var(--muted-text)', fontSize: '0.85rem' }}>{d}</div>
          ))}
          {daysArray.map((day, idx) => {
            if (day === null) return <div key={`empty-${idx}`} style={{ minHeight: '80px', backgroundColor: '#F8FAFC', borderRadius: '6px', opacity: 0.4 }}></div>;

            const dayStr = String(day).padStart(2, '0');
            const dateStr = `2026-09-${dayStr}`;
            // Match events on this date
            const dayEvents = filteredList.filter(e => e.date === dateStr);

            return (
              <div key={day} style={{
                minHeight: '85px',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '6px',
                backgroundColor: 'var(--white)',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                alignItems: 'stretch',
                justifyContent: 'flex-start'
              }}>
                <span style={{ fontSize: '0.85rem', fontWeight: '700', color: '#1e293b' }}>{day}</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', overflowY: 'auto' }}>
                  {dayEvents.map(evt => {
                    const styles = getStatusStyles(evt.status);
                    return (
                      <div
                        key={evt.id}
                        onClick={() => setViewingEvent(evt)}
                        style={{
                          fontSize: '0.65rem',
                          fontWeight: '700',
                          padding: '2px 4px',
                          borderRadius: '4px',
                          backgroundColor: styles.bg,
                          color: styles.text,
                          border: `1px solid ${styles.border}`,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}
                        title={`${evt.title} (${evt.startTime})`}
                      >
                        {evt.title}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', width: '100%' }}>
      
      {/* Event Stats grid */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-donors">
              <Layers size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Total Events</span>
            <h3 className="stat-card-value">{totalEvents}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-requests">
              <Calendar size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Upcoming Events</span>
            <h3 className="stat-card-value" style={{ color: '#2563EB' }}>{upcomingEvents}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-inventory">
              <Clock size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Ongoing Events</span>
            <h3 className="stat-card-value" style={{ color: '#d97706' }}>{ongoingEvents}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-left">
            <div className="stat-icon-wrapper stat-units">
              <Clock size={20} className="stat-icon-svg" />
            </div>
          </div>
          <div className="stat-card-right">
            <span className="stat-card-title">Completed Events</span>
            <h3 className="stat-card-value" style={{ color: '#059669' }}>{completedEvents}</h3>
          </div>
        </div>
      </section>

      {/* Main split row: Events Content (Left) + Highlights Column (Right) */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '28px', alignItems: 'start' }}>
        
        {/* Left Column: Events Toolbar, Table or Calendar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Search & Filter Toolbar */}
          <section className="filters-toolbar" style={{ flexWrap: 'wrap' }}>
            <div className="search-box-wrapper">
              <Search size={18} className="search-icon-input" />
              <input
                type="text"
                placeholder="Search events by name, ID, type, venue, organizer..."
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
                  value={eventTypeFilter}
                  onChange={(e) => {
                    setEventTypeFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="toolbar-select"
                >
                  <option value="All">All Event Types</option>
                  {EVENT_TYPES.map(t => (
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

              {/* List / Calendar toggle buttons */}
              <div style={{ display: 'inline-flex', backgroundColor: '#e2e8f0', borderRadius: '8px', padding: '2px' }}>
                <button
                  onClick={() => setViewMode('list')}
                  style={{
                    border: 'none',
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    backgroundColor: viewMode === 'list' ? 'var(--white)' : 'transparent',
                    color: viewMode === 'list' ? 'var(--dark-text)' : '#64748b'
                  }}
                >
                  List
                </button>
                <button
                  onClick={() => setViewMode('calendar')}
                  style={{
                    border: 'none',
                    padding: '6px 12px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    backgroundColor: viewMode === 'calendar' ? 'var(--white)' : 'transparent',
                    color: viewMode === 'calendar' ? 'var(--dark-text)' : '#64748b'
                  }}
                >
                  Calendar
                </button>
              </div>

              <button className="add-donor-btn" onClick={handleOpenCreateModal}>
                + Create Event
              </button>
            </div>
          </section>

          {/* Conditional rendering based on list/calendar mode */}
          {viewMode === 'list' ? (
            <section className="content-card table-card">
              <div className="table-responsive-container">
                <table className="donors-table">
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Event Name</th>
                      <th>Event Type</th>
                      <th>Date</th>
                      <th>Time</th>
                      <th>Venue</th>
                      <th>Organizer</th>
                      <th>Participants</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedEvents.length > 0 ? (
                      paginatedEvents.map((evt) => {
                        const statusColors = getStatusStyles(evt.status);
                        return (
                          <tr key={evt.id}>
                            <td className="donor-id-cell font-semibold">{evt.id}</td>
                            <td className="donor-name-cell font-semibold">{evt.title}</td>
                            <td>{evt.type}</td>
                            <td>{evt.date}</td>
                            <td>{evt.startTime}</td>
                            <td>{evt.venue}</td>
                            <td>{evt.organizer}</td>
                            <td style={{ textAlign: 'center', fontWeight: '600' }}>
                              {evt.participants} / {evt.maxParticipants || 'No limit'}
                            </td>
                            <td>
                              {/* Interactive Inline Status Changer */}
                              <select
                                value={evt.status}
                                onChange={(e) => onStatusChange(evt.id, e.target.value)}
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
                                  onClick={() => setViewingEvent(evt)}
                                  title="View Details"
                                >
                                  <Eye size={16} />
                                </button>
                                <button
                                  className="action-icon-btn edit"
                                  onClick={() => handleOpenEditModal(evt)}
                                  title="Edit Event"
                                >
                                  <Edit2 size={16} />
                                </button>
                                <button
                                  className="action-icon-btn delete"
                                  onClick={() => setDeletingEventId(evt.id)}
                                  title="Delete Event"
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
                          No campus events found matching the filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Table Footer / Pagination */}
              <div className="table-footer">
                <div className="footer-info-text">
                  Showing {totalItems > 0 ? ((currentPage - 1) * itemsPerPage) + 1 : 0} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} events
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
          ) : (
            renderCalendarMonth()
          )}
        </div>

        {/* Right Column: Upcoming Events Section card */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--muted-text)', margin: '0' }}>Upcoming Events Highlights</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {nearestUpcoming.length > 0 ? (
              nearestUpcoming.map(evt => (
                <div key={evt.id} style={{
                  backgroundColor: 'var(--white)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '16px',
                  boxShadow: 'var(--card-shadow)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--primary-rose)', padding: '2px 8px', backgroundColor: '#FFF5F5', borderRadius: '4px' }}>
                      {evt.type}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{evt.id}</span>
                  </div>
                  <h5 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '700', color: 'var(--dark-text)' }}>{evt.title}</h5>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px', fontSize: '0.8rem', color: '#475569' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Calendar size={13} style={{ color: '#2563eb' }} />
                      <span>{evt.date}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Clock size={13} style={{ color: '#d97706' }} />
                      <span>{evt.startTime} - {evt.endTime || 'N/A'}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <MapPin size={13} style={{ color: '#059669' }} />
                      <span>{evt.venue}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setViewingEvent(evt)}
                    style={{
                      border: 'none',
                      backgroundColor: 'transparent',
                      color: 'var(--primary-rose)',
                      fontSize: '0.8rem',
                      fontWeight: '700',
                      textAlign: 'left',
                      padding: 0,
                      cursor: 'pointer',
                      marginTop: '8px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    View Event details →
                  </button>
                </div>
              ))
            ) : (
              <div style={{ padding: '16px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '12px', textAlign: 'center', fontSize: '0.85rem', color: '#64748b' }}>
                No upcoming events registered.
              </div>
            )}
          </div>
        </section>

      </div>

      {/* --- Create / Edit Event Modal --- */}
      {(isCreatingEvent || editingEvent) && (
        <div className="modal-overlay">
          <div className="modal-content-card">
            <div className="modal-header">
              <h3>{editingEvent ? 'Edit Event Details' : 'Create Campus Event'}</h3>
              <button
                className="modal-close-btn"
                onClick={() => {
                  setIsCreatingEvent(false);
                  setEditingEvent(null);
                  resetForm();
                }}
              >
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveEventSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="evt-title">Event Name <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="evt-title"
                    value={eventForm.title}
                    onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
                    required
                    placeholder="e.g. Annual Blood Donation Camp"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-type">Event Type <span className="req-star">*</span></label>
                  <select
                    id="evt-type"
                    value={eventForm.type}
                    onChange={(e) => setEventForm({ ...eventForm, type: e.target.value })}
                    required
                  >
                    {EVENT_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-date">Event Date <span className="req-star">*</span></label>
                  <input
                    type="date"
                    id="evt-date"
                    value={eventForm.date}
                    onChange={(e) => setEventForm({ ...eventForm, date: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-start">Start Time <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="evt-start"
                    value={eventForm.startTime}
                    onChange={(e) => setEventForm({ ...eventForm, startTime: e.target.value })}
                    required
                    placeholder="e.g. 09:00 AM"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-end">End Time</label>
                  <input
                    type="text"
                    id="evt-end"
                    value={eventForm.endTime}
                    onChange={(e) => setEventForm({ ...eventForm, endTime: e.target.value })}
                    placeholder="e.g. 03:00 PM"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-venue">Venue <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="evt-venue"
                    value={eventForm.venue}
                    onChange={(e) => setEventForm({ ...eventForm, venue: e.target.value })}
                    required
                    placeholder="e.g. College Seminar Hall"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-org">Organizer <span className="req-star">*</span></label>
                  <input
                    type="text"
                    id="evt-org"
                    value={eventForm.organizer}
                    onChange={(e) => setEventForm({ ...eventForm, organizer: e.target.value })}
                    required
                    placeholder="e.g. Rakthasedu Chapter"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-max">Max Participants</label>
                  <input
                    type="number"
                    min="1"
                    id="evt-max"
                    value={eventForm.maxParticipants}
                    onChange={(e) => setEventForm({ ...eventForm, maxParticipants: e.target.value })}
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-phone">Contact Number</label>
                  <input
                    type="tel"
                    id="evt-phone"
                    value={eventForm.contactNumber}
                    onChange={(e) => setEventForm({ ...eventForm, contactNumber: e.target.value })}
                    placeholder="Enter organizer phone"
                  />
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-status">Status <span className="req-star">*</span></label>
                  <select
                    id="evt-status"
                    value={eventForm.status}
                    onChange={(e) => setEventForm({ ...eventForm, status: e.target.value })}
                    required
                  >
                    {STATUSES.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group-item">
                  <label htmlFor="evt-deadline">Reg. Deadline</label>
                  <input
                    type="date"
                    id="evt-deadline"
                    value={eventForm.registrationDeadline}
                    onChange={(e) => setEventForm({ ...eventForm, registrationDeadline: e.target.value })}
                  />
                </div>

                <div className="form-group-item" style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '28px' }}>
                  <input
                    type="checkbox"
                    id="evt-reg"
                    checked={eventForm.registrationRequired}
                    onChange={(e) => setEventForm({ ...eventForm, registrationRequired: e.target.checked })}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                  <label htmlFor="evt-reg" style={{ cursor: 'pointer', fontWeight: 600 }}>Registration Required</label>
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="evt-banner">Event Image / Banner URL</label>
                  <input
                    type="text"
                    id="evt-banner"
                    value={eventForm.imageBanner}
                    onChange={(e) => setEventForm({ ...eventForm, imageBanner: e.target.value })}
                    placeholder="e.g. https://images.unsplash.com/... or leave blank"
                  />
                </div>

                <div className="form-group-item" style={{ gridColumn: 'span 2' }}>
                  <label htmlFor="evt-desc">Description</label>
                  <textarea
                    id="evt-desc"
                    value={eventForm.description}
                    onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })}
                    placeholder="Describe the activities, event goals, and instructions..."
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
                    setIsCreatingEvent(false);
                    setEditingEvent(null);
                    resetForm();
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="modal-primary-btn">
                  {editingEvent ? 'Save Changes' : 'Create Event'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- View Event Details Modal --- */}
      {viewingEvent && (
        <div className="modal-overlay">
          <div className="modal-content-card detail-modal">
            <div className="modal-header">
              <h3>Campus Event Folder</h3>
              <button className="modal-close-btn" onClick={() => setViewingEvent(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-details-body">
              {viewingEvent.imageBanner ? (
                <img
                  src={viewingEvent.imageBanner}
                  alt={viewingEvent.title}
                  style={{
                    width: '100%',
                    height: '140px',
                    objectFit: 'cover',
                    borderRadius: '8px',
                    marginBottom: '16px',
                    border: '1px solid var(--border-color)'
                  }}
                />
              ) : (
                <div style={{
                  width: '100%',
                  height: '100px',
                  backgroundColor: '#EFF6FF',
                  color: '#2563EB',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  border: '1px solid #BFDBFE'
                }}>
                  <ImageIcon size={24} />
                  <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>Banner Image Not Provided</span>
                </div>
              )}

              <h4 style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 20px 0', color: 'var(--dark-text)' }}>
                {viewingEvent.title}
              </h4>
              
              <div className="details-grid">
                <div className="detail-row">
                  <span className="detail-lbl">Event ID</span>
                  <span className="detail-val font-semibold">{viewingEvent.id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Event Type</span>
                  <span className="detail-val font-semibold" style={{ color: 'var(--primary-rose)' }}>
                    {viewingEvent.type}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Date</span>
                  <span className="detail-val font-semibold" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Calendar size={14} /> {viewingEvent.date}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Time Range</span>
                  <span className="detail-val">{viewingEvent.startTime} - {viewingEvent.endTime || 'N/A'}</span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Venue</span>
                  <span className="detail-val font-semibold">{viewingEvent.venue}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Organizer</span>
                  <span className="detail-val">{viewingEvent.organizer}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Contact Number</span>
                  <span className="detail-val">{viewingEvent.contactNumber || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Participants</span>
                  <span className="detail-val font-semibold">{viewingEvent.participants} Registered</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Max Limit</span>
                  <span className="detail-val">{viewingEvent.maxParticipants || 'No limit'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Reg. Required</span>
                  <span className="detail-val font-semibold">{viewingEvent.registrationRequired ? 'Yes' : 'No'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Reg. Deadline</span>
                  <span className="detail-val">{viewingEvent.registrationDeadline || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-lbl">Event Status</span>
                  <span className="detail-val">
                    <span style={{
                      backgroundColor: getStatusStyles(viewingEvent.status).bg,
                      color: getStatusStyles(viewingEvent.status).text,
                      padding: '4px 10px',
                      borderRadius: '20px',
                      fontSize: '0.8rem',
                      fontWeight: '600'
                    }}>
                      {viewingEvent.status}
                    </span>
                  </span>
                </div>
                <div className="detail-row" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-lbl">Description</span>
                  <span className="detail-val" style={{ whiteSpace: 'pre-wrap', fontStyle: viewingEvent.description ? 'normal' : 'italic' }}>
                    {viewingEvent.description || 'No description provided.'}
                  </span>
                </div>
              </div>
              
              <div className="modal-footer-actions justify-center">
                <button className="modal-primary-btn" onClick={() => setViewingEvent(null)}>
                  Close File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Delete Confirmation Modal --- */}
      {deletingEventId && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal">
            <div className="modal-header">
              <h3>Confirm Deletion</h3>
              <button className="modal-close-btn" onClick={() => setDeletingEventId(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <ShieldAlert size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Delete Event</strong>
              </div>
              <p>Are you sure you want to delete event <strong>{deletingEventId}</strong>? This action cannot be undone.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setDeletingEventId(null)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleDeleteEventConfirm}>
                  Delete Event
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
