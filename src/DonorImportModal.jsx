import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  X,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { previewDonorImport, executeDonorImport } from './api.js';

export default function DonorImportModal({ isOpen, onClose, onImportSuccess, userHospitalId }) {
  const [file, setFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('upload'); // 'upload' | 'preview' | 'result'
  const [previewData, setPreviewData] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      processSelectedFile(selected);
    }
  };

  const processSelectedFile = async (selectedFile) => {
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setErrorMessage('Please select a valid .csv or .xlsx Excel file.');
      return;
    }

    setFile(selectedFile);
    setErrorMessage('');
    setLoading(true);

    try {
      const preview = await previewDonorImport(selectedFile, userHospitalId);
      setPreviewData(preview);
      setStep('preview');
    } catch (err) {
      console.error('Import preview failed:', err);
      setErrorMessage(err.message || 'Failed to preview the dataset.');
    } finally {
      setLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files?.[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleExecuteImport = async () => {
    if (!file) return;

    setLoading(true);
    setErrorMessage('');
    try {
      const result = await executeDonorImport(file, userHospitalId);
      setResultData(result);
      setStep('result');
      if (onImportSuccess) {
        onImportSuccess(result);
      }
    } catch (err) {
      console.error('Execute import failed:', err);
      setErrorMessage(err.message || 'Failed to execute import.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreviewData(null);
    setResultData(null);
    setErrorMessage('');
    setStep('upload');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="modal-overlay" style={{ zIndex: 1100 }}>
      <div className="modal-content-card" style={{ maxWidth: '850px', width: '90%', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: '#FFE4E6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#E11D48'
            }}>
              <FileSpreadsheet size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#0F172A' }}>Bulk Import Donors</h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748B' }}>
                Upload hospital donor records via CSV or Excel (.xlsx)
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {errorMessage && (
          <div style={{
            margin: '16px 24px 0',
            padding: '12px 16px',
            backgroundColor: '#FEF2F2',
            border: '1px solid #FCA5A5',
            borderRadius: '8px',
            color: '#DC2626',
            fontSize: '0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertTriangle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        <div style={{ padding: '20px 24px' }}>
          {/* STEP 1: UPLOAD */}
          {step === 'upload' && (
            <div>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: isDragOver ? '2px dashed #E11D48' : '2px dashed #CBD5E1',
                  borderRadius: '12px',
                  backgroundColor: isDragOver ? '#FFF1F2' : '#F8FAFC',
                  padding: '48px 24px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".csv, .xlsx, .xls"
                  style={{ display: 'none' }}
                />
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  backgroundColor: '#FFE4E6',
                  color: '#E11D48',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {loading ? <Loader2 className="spinner" size={28} /> : <UploadCloud size={28} />}
                </div>
                <h4 style={{ margin: 0, fontSize: '1.05rem', color: '#1E293B' }}>
                  {loading ? 'Analyzing Dataset...' : 'Click to browse or drag and drop file here'}
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#64748B' }}>
                  Supported formats: <strong>CSV</strong> or <strong>Excel (.xlsx)</strong> up to 10MB
                </p>
                <div style={{
                  marginTop: '12px',
                  display: 'inline-flex',
                  gap: '16px',
                  fontSize: '0.75rem',
                  color: '#94A3B8'
                }}>
                  <span>Required columns: Full Name, Blood Group, Phone, District</span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: PREVIEW */}
          {step === 'preview' && previewData && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Summary Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: '12px'
              }}>
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#64748B', display: 'block' }}>Total Rows</span>
                  <strong style={{ fontSize: '1.3rem', color: '#0F172A' }}>{previewData.total_rows}</strong>
                </div>
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#059669', display: 'block' }}>Valid Rows</span>
                  <strong style={{ fontSize: '1.3rem', color: '#059669' }}>{previewData.valid_rows}</strong>
                </div>
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#2563EB', display: 'block' }}>New Donors</span>
                  <strong style={{ fontSize: '1.3rem', color: '#2563EB' }}>{previewData.new_donors}</strong>
                </div>
                <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#F5F3FF', border: '1px solid #DDD6FE', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#7C3AED', display: 'block' }}>Existing Donors</span>
                  <strong style={{ fontSize: '1.3rem', color: '#7C3AED' }}>{previewData.existing_donors}</strong>
                </div>
                {previewData.invalid_rows > 0 && (
                  <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#FEF2F2', border: '1px solid #FCA5A5', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: '#DC2626', display: 'block' }}>Invalid Rows</span>
                    <strong style={{ fontSize: '1.3rem', color: '#DC2626' }}>{previewData.invalid_rows}</strong>
                  </div>
                )}
              </div>

              {/* Rows Preview Table */}
              <div>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', color: '#334155' }}>Preview Sample Rows:</h4>
                <div style={{ maxHeight: '280px', overflowY: 'auto', border: '1px solid #E2E8F0', borderRadius: '8px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                    <thead style={{ backgroundColor: '#F1F5F9', position: 'sticky', top: 0, zIndex: 1 }}>
                      <tr>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>Row</th>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>Name</th>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>Group</th>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>Phone</th>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>District</th>
                        <th style={{ padding: '8px 12px', borderBottom: '1px solid #E2E8F0' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.preview_rows?.map((row) => (
                        <tr key={row.row} style={{ borderBottom: '1px solid #F1F5F9', backgroundColor: row.is_valid ? 'transparent' : '#FFF1F2' }}>
                          <td style={{ padding: '8px 12px', color: '#64748B' }}>#{row.row}</td>
                          <td style={{ padding: '8px 12px', fontWeight: 600 }}>{row.full_name || '—'}</td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '12px',
                              backgroundColor: '#FFE4E6',
                              color: '#BE123C',
                              fontWeight: 600,
                              fontSize: '0.75rem'
                            }}>
                              {row.blood_group || '—'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px' }}>{row.normalized_phone || row.phone || '—'}</td>
                          <td style={{ padding: '8px 12px' }}>{row.district || '—'}</td>
                          <td style={{ padding: '8px 12px' }}>
                            {row.is_valid ? (
                              <span style={{ color: '#059669', display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}>
                                <CheckCircle2 size={14} /> {row.is_existing ? 'Update' : 'New'}
                              </span>
                            ) : (
                              <span style={{ color: '#DC2626', display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }} title={row.errors?.join(', ')}>
                                <XCircle size={14} /> Invalid
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={handleReset}
                  disabled={loading}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <RefreshCw size={14} /> Change File
                </button>
                <button
                  type="button"
                  className="modal-primary-btn"
                  onClick={handleExecuteImport}
                  disabled={loading || previewData.valid_rows === 0}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 20px' }}
                >
                  {loading ? (
                    <>
                      <Loader2 className="spinner" size={16} />
                      <span>Importing Donors...</span>
                    </>
                  ) : (
                    <>
                      <span>Import {previewData.valid_rows} Valid Records</span>
                      <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: RESULT */}
          {step === 'result' && resultData && (
            <div style={{ textAlign: 'center', padding: '16px 0', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: '#ECFDF5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto'
              }}>
                <CheckCircle2 size={36} />
              </div>
              <div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', color: '#0F172A' }}>Import Completed Successfully!</h3>
                <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748B' }}>
                  Processed <strong>{resultData.total_records}</strong> total donor records from {resultData.batch?.filename || 'dataset'}.
                </p>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '12px',
                margin: '8px 0'
              }}>
                <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0' }}>
                  <span style={{ fontSize: '0.8rem', color: '#059669', display: 'block' }}>New Registered</span>
                  <strong style={{ fontSize: '1.4rem', color: '#059669' }}>{resultData.new_donors_created}</strong>
                </div>
                <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                  <span style={{ fontSize: '0.8rem', color: '#2563EB', display: 'block' }}>Profiles Updated</span>
                  <strong style={{ fontSize: '1.4rem', color: '#2563EB' }}>{resultData.existing_donors_updated}</strong>
                </div>
                <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: resultData.failed_records > 0 ? '#FEF2F2' : '#F8FAFC', border: '1px solid #E2E8F0' }}>
                  <span style={{ fontSize: '0.8rem', color: resultData.failed_records > 0 ? '#DC2626' : '#64748B', display: 'block' }}>Failed</span>
                  <strong style={{ fontSize: '1.4rem', color: resultData.failed_records > 0 ? '#DC2626' : '#64748B' }}>{resultData.failed_records}</strong>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
                <button
                  type="button"
                  className="modal-secondary-btn"
                  onClick={handleReset}
                >
                  Import Another File
                </button>
                <button
                  type="button"
                  className="modal-primary-btn"
                  onClick={onClose}
                >
                  View Donors List
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
