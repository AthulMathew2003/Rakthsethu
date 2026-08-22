import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  User,
  Bell,
  Palette,
  Shield,
  Sliders,
  CheckCircle,
  X,
  Info,
  Camera,
  AlertTriangle
} from 'lucide-react';

const TABS = [
  { id: 'general', label: 'General', icon: <Sliders size={18} /> },
  { id: 'profile', label: 'Admin Profile', icon: <User size={18} /> },
  { id: 'notifications', label: 'Notifications', icon: <Bell size={18} /> },
  { id: 'appearance', label: 'Appearance', icon: <Palette size={18} /> },
  { id: 'security', label: 'Security', icon: <Shield size={18} /> },
  { id: 'system', label: 'System', icon: <SettingsIcon size={18} /> }
];

const DEFAULT_SETTINGS = {
  general: {
    appName: 'Rakthasedu',
    orgName: 'Rakthasedu Blood Management System',
    email: 'admin@rakthasethu.org',
    phone: '+91 94951 78902',
    defaultDistrict: 'Kottayam',
    language: 'English'
  },
  profile: {
    fullName: 'Sruthy M S',
    email: 'sruthy.admin@rakthasethu.org',
    phone: '+91 98456 78901',
    role: 'Admin',
    district: 'Kottayam',
    panchayat: 'Kanjirappally',
    avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=150&auto=format&fit=crop'
  },
  notifications: {
    bloodRequest: true,
    bloodDonation: true,
    lowStock: true,
    expiryAlerts: true,
    newUser: false,
    campusEvents: true,
    systemNotif: true,
    emailNotif: true
  },
  appearance: {
    theme: 'Light',
    sidebarMode: 'Expanded'
  },
  security: {
    twoFactor: false,
    loginAlerts: true,
    sessionTimeout: '30 Minutes'
  },
  system: {
    maintenanceMode: false,
    automaticNotif: true,
    lowStockThreshold: 5,
    expiryWarningDays: 7,
    defaultEventStatus: 'Draft'
  }
};

export default function SettingsPage({ onProfileNameChange }) {
  const [activeSubTab, setActiveSubTab] = useState('general');
  const [settingsState, setSettingsState] = useState(() => JSON.parse(JSON.stringify(DEFAULT_SETTINGS)));

  // Form password states
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmNewPassword: ''
  });

  // Success Notification / Toast state
  const [toastMessage, setToastMessage] = useState(null);
  const [isResetWarningOpen, setIsResetWarningOpen] = useState(false);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleSaveGeneral = (e) => {
    e.preventDefault();
    showToast('Settings saved successfully.');
  };

  const handleSaveProfile = (e) => {
    e.preventDefault();
    showToast('Profile updated successfully.');
    // Trigger callback to update top-right Admin display name in Dashboard.jsx header
    if (onProfileNameChange) {
      onProfileNameChange(settingsState.profile.fullName);
    }
  };

  const handleSaveNotifications = () => {
    showToast('Notification preferences updated.');
  };

  const handleSaveAppearance = (e) => {
    e.preventDefault();
    showToast('Appearance settings saved.');
  };

  const handleSaveSystem = (e) => {
    e.preventDefault();
    showToast('System variables saved successfully.');
  };

  const handlePasswordSubmit = (e) => {
    e.preventDefault();
    if (!passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmNewPassword) {
      alert('Please fill in all password fields.');
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmNewPassword) {
      alert('New password and confirm password do not match.');
      return;
    }
    showToast('Password update will be available after backend integration.');
    setPasswordForm({ currentPassword: '', newPassword: '', confirmNewPassword: '' });
  };

  const handleResetToDefault = () => {
    setSettingsState(JSON.parse(JSON.stringify(DEFAULT_SETTINGS)));
    setIsResetWarningOpen(false);
    showToast('All settings reset to baseline default values.');
    if (onProfileNameChange) {
      onProfileNameChange(DEFAULT_SETTINGS.profile.fullName);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', width: '100%' }}>
      
      {/* Toast Notification popup */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          backgroundColor: '#0F172A',
          color: 'var(--white)',
          padding: '12px 20px',
          borderRadius: '8px',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 9999,
          fontSize: '0.85rem',
          fontWeight: '600',
          borderLeft: '4px solid #10B981'
        }}>
          <CheckCircle size={18} style={{ color: '#10B981' }} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Split Grid: Left Sidebar Navigation + Right settings details form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '28px', alignItems: 'start' }}>
        
        {/* Settings Sidebar navigation */}
        <div className="content-card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: '700',
                cursor: 'pointer',
                textAlign: 'left',
                backgroundColor: activeSubTab === tab.id ? 'var(--primary-rose)' : 'transparent',
                color: activeSubTab === tab.id ? 'var(--white)' : '#475569',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}

          <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '16px', paddingTop: '16px' }}>
            <button
              onClick={() => setIsResetWarningOpen(true)}
              style={{
                border: 'none',
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: '700',
                cursor: 'pointer',
                backgroundColor: '#FFF5F5',
                color: 'var(--primary-rose)',
                border: '1px dashed #FCA5A5'
              }}
            >
              <AlertTriangle size={18} />
              <span>Reset to Default</span>
            </button>
          </div>
        </div>

        {/* Settings Details forms wrapper */}
        <div className="content-card" style={{ padding: '28px', minHeight: '440px' }}>
          
          {/* A. GENERAL SETTINGS */}
          {activeSubTab === 'general' && (
            <form onSubmit={handleSaveGeneral} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>General Settings</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Configure organizational identity parameters.</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Application Name</label>
                  <input
                    type="text"
                    value={settingsState.general.appName}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, appName: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Organization Name</label>
                  <input
                    type="text"
                    value={settingsState.general.orgName}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, orgName: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Contact Email</label>
                  <input
                    type="email"
                    value={settingsState.general.email}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, email: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Contact Phone</label>
                  <input
                    type="text"
                    value={settingsState.general.phone}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, phone: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Default District</label>
                  <input
                    type="text"
                    value={settingsState.general.defaultDistrict}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, defaultDistrict: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Default Language</label>
                  <select
                    value={settingsState.general.language}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      general: { ...settingsState.general, language: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  >
                    <option value="English">English</option>
                    <option value="Malayalam">Malayalam</option>
                    <option value="Hindi">Hindi</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button type="submit" className="add-donor-btn">Save Changes</button>
                <button
                  type="button"
                  onClick={() => setSettingsState({ ...settingsState, general: JSON.parse(JSON.stringify(DEFAULT_SETTINGS.general)) })}
                  style={{
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'transparent',
                    padding: '10px 18px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  Reset
                </button>
              </div>
            </form>
          )}

          {/* B. ADMIN PROFILE */}
          {activeSubTab === 'profile' && (
            <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>Admin Profile</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Update details displaying on your dashboard account.</p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                <div style={{ position: 'relative' }}>
                  <img
                    src={settingsState.profile.avatar}
                    alt="Profile Avatar"
                    style={{ width: '80px', height: '80px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--primary-rose)' }}
                  />
                  <div style={{
                    position: 'absolute',
                    bottom: 0,
                    right: 0,
                    backgroundColor: 'var(--primary-rose)',
                    color: 'white',
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
                  }}>
                    <Camera size={14} />
                  </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Profile Photo URL</label>
                  <input
                    type="text"
                    value={settingsState.profile.avatar}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      profile: { ...settingsState.profile, avatar: e.target.value }
                    })}
                    placeholder="Enter image URL"
                    style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Full Name</label>
                  <input
                    type="text"
                    value={settingsState.profile.fullName}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      profile: { ...settingsState.profile, fullName: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Phone Number</label>
                  <input
                    type="text"
                    value={settingsState.profile.phone}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      profile: { ...settingsState.profile, phone: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700', opacity: 0.7 }}>Email Address (Read-only)</label>
                  <input
                    type="text"
                    value={settingsState.profile.email}
                    disabled
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: '#F1F5F9', color: '#64748b', cursor: 'not-allowed' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700', opacity: 0.7 }}>Account Role (Read-only)</label>
                  <input
                    type="text"
                    value={settingsState.profile.role}
                    disabled
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: '#F1F5F9', color: '#64748b', cursor: 'not-allowed' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700', opacity: 0.7 }}>District (Read-only)</label>
                  <input
                    type="text"
                    value={settingsState.profile.district}
                    disabled
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: '#F1F5F9', color: '#64748b', cursor: 'not-allowed' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700', opacity: 0.7 }}>Panchayat (Read-only)</label>
                  <input
                    type="text"
                    value={settingsState.profile.panchayat}
                    disabled
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: '#F1F5F9', color: '#64748b', cursor: 'not-allowed' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button type="submit" className="add-donor-btn">Save Profile</button>
                <button
                  type="button"
                  onClick={() => setSettingsState({ ...settingsState, profile: JSON.parse(JSON.stringify(DEFAULT_SETTINGS.profile)) })}
                  style={{
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'transparent',
                    padding: '10px 18px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* C. NOTIFICATION PREFERENCES */}
          {activeSubTab === 'notifications' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>Notification Preferences</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Toggle alert criteria for dashboard notifications.</p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* 1 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Blood Request Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Receive alerts when a hospital submits a new request.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.bloodRequest}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, bloodRequest: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 2 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Blood Donation Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Notify when a user schedules or completes a donation.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.bloodDonation}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, bloodDonation: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 3 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Low Blood Stock Alerts</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Receive alerts when blood inventory falls below configured thresholds.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.lowStock}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, lowStock: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 4 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Expiry Alerts</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Receive alerts for batches reaching their warning expiry date.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.expiryAlerts}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, expiryAlerts: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 5 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>New User Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Notify upon registration of a new citizen or department user.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.newUser}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, newUser: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 6 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Campus Event Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Receive updates regarding upcoming donation awareness camps.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.campusEvents}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, campusEvents: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 7 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>System Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Information regarding dashboard logins and platform status.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.systemNotif}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, systemNotif: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                {/* 8 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Email Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Send diagnostic email reports summarizing platform logs.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.notifications.emailNotif}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      notifications: { ...settingsState.notifications, emailNotif: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button className="add-donor-btn" onClick={handleSaveNotifications}>Save Preferences</button>
              </div>
            </div>
          )}

          {/* D. APPEARANCE SETTINGS */}
          {activeSubTab === 'appearance' && (
            <form onSubmit={handleSaveAppearance} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>Appearance</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Customize dashboard aesthetics and menu layouts.</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Aesthetic Theme</label>
                  <select
                    value={settingsState.appearance.theme}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      appearance: { ...settingsState.appearance, theme: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  >
                    <option value="Light">Light</option>
                    <option value="Dark">Dark</option>
                    <option value="System Default">System Default</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Sidebar Navigation Layout</label>
                  <select
                    value={settingsState.appearance.sidebarMode}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      appearance: { ...settingsState.appearance, sidebarMode: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  >
                    <option value="Expanded">Expanded</option>
                    <option value="Collapsed">Collapsed</option>
                  </select>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button type="submit" className="add-donor-btn">Save Appearance</button>
              </div>
            </form>
          )}

          {/* E. SECURITY SETTINGS */}
          {activeSubTab === 'security' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
              
              {/* Change Password Form Mocks */}
              <form onSubmit={handlePasswordSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>Change Password</h4>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Update your administrative dashboard account credentials.</p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Current Password</label>
                    <input
                      type="password"
                      value={passwordForm.currentPassword}
                      onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                      style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                    />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>New Password</label>
                    <input
                      type="password"
                      value={passwordForm.newPassword}
                      onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                      style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                    />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Confirm New Password</label>
                    <input
                      type="password"
                      value={passwordForm.confirmNewPassword}
                      onChange={(e) => setPasswordForm({ ...passwordForm, confirmNewPassword: e.target.value })}
                      style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                    />
                  </div>
                </div>

                <div>
                  <button type="submit" className="add-donor-btn" style={{ backgroundColor: 'var(--primary-rose)' }}>Update Password</button>
                </div>
              </form>

              {/* Mocks Security Toggles */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
                <h5 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>Security & Credentials Options</h5>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Two-Factor Authentication</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Require secondary verification code during dashboard log in.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.security.twoFactor}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      security: { ...settingsState.security, twoFactor: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Login Notifications</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Alert via email on successful dashboard entry.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settingsState.security.loginAlerts}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      security: { ...settingsState.security, loginAlerts: e.target.checked }
                    })}
                    style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>Session Timeout limit</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--muted-text)' }}>Automatically sign out inactive sessions after timing threshold.</div>
                  </div>
                  <select
                    value={settingsState.security.sessionTimeout}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      security: { ...settingsState.security, sessionTimeout: e.target.value }
                    })}
                    style={{ padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}
                  >
                    <option value="15 Minutes">15 Minutes</option>
                    <option value="30 Minutes">30 Minutes</option>
                    <option value="1 Hour">1 Hour</option>
                    <option value="2 Hours">2 Hours</option>
                  </select>
                </div>
              </div>

            </div>
          )}

          {/* F. SYSTEM VARIABLES */}
          {activeSubTab === 'system' && (
            <form onSubmit={handleSaveSystem} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800 }}>System Variable Limits</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted-text)' }}>Configure background thresholds and default variables.</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Low Stock Warning Threshold (Units)</label>
                  <input
                    type="number"
                    min="1"
                    value={settingsState.system.lowStockThreshold}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      system: { ...settingsState.system, lowStockThreshold: parseInt(e.target.value, 10) }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Expiry Alert Days Warning</label>
                  <input
                    type="number"
                    min="1"
                    value={settingsState.system.expiryWarningDays}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      system: { ...settingsState.system, expiryWarningDays: parseInt(e.target.value, 10) }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: '700' }}>Default Created Event Status</label>
                  <select
                    value={settingsState.system.defaultEventStatus}
                    onChange={(e) => setSettingsState({
                      ...settingsState,
                      system: { ...settingsState.system, defaultEventStatus: e.target.value }
                    })}
                    style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
                  >
                    <option value="Draft">Draft</option>
                    <option value="Upcoming">Upcoming</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ fontSize: '0.85rem' }}>Maintenance Mode</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted-text)' }}>Restrict citizen access for diagnostics.</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settingsState.system.maintenanceMode}
                      onChange={(e) => setSettingsState({
                        ...settingsState,
                        system: { ...settingsState.system, maintenanceMode: e.target.checked }
                      })}
                      style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ fontSize: '0.85rem' }}>Automatic Notifications</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted-text)' }}>Trigger automated alerts for low stock batches.</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settingsState.system.automaticNotif}
                      onChange={(e) => setSettingsState({
                        ...settingsState,
                        system: { ...settingsState.system, automaticNotif: e.target.checked }
                      })}
                      style={{ width: '38px', height: '20px', cursor: 'pointer' }}
                    />
                  </div>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <button type="submit" className="add-donor-btn">Save Variables</button>
              </div>
            </form>
          )}

        </div>

      </div>

      {/* --- Reset Confirmation Modal --- */}
      {isResetWarningOpen && (
        <div className="modal-overlay">
          <div className="modal-content-card delete-confirm-modal" style={{ maxWidth: '380px' }}>
            <div className="modal-header">
              <h3>Reset Defaults</h3>
              <button className="modal-close-btn" onClick={() => setIsResetWarningOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="delete-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary-rose)', marginBottom: '14px' }}>
                <AlertTriangle size={24} />
                <strong style={{ fontSize: '1.05rem' }}>Warning: Reset All Settings</strong>
              </div>
              <p>Are you sure you want to reset all settings to their default values? Custom profile names and system thresholds will be cleared.</p>
              <div className="modal-footer-actions">
                <button className="modal-secondary-btn" onClick={() => setIsResetWarningOpen(false)}>
                  Cancel
                </button>
                <button className="modal-delete-btn" onClick={handleResetToDefault} style={{ backgroundColor: 'var(--primary-rose)' }}>
                  Reset Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
