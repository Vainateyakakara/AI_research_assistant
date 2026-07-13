import { useState, useRef, useEffect } from 'react';
import { useUpload } from '../hooks/useUpload';
import { getStatus } from '../utils/api';

export default function UploadPanel({ onUploadComplete }) {
  const { isProcessing, result, error, upload, reset } = useUpload();
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [dbStats, setDbStats] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchStats();
  }, [result]);

  async function fetchStats() {
    try {
      const s = await getStatus();
      setDbStats(s);
    } catch {
      // ignore
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      reset();
    }
  }

  function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      reset();
    }
  }

  async function handleProcess() {
    if (!selectedFile) return;
    await upload(selectedFile);
    if (onUploadComplete) onUploadComplete();
  }

  return (
    <div className="upload-page">
      <h2 className="upload-page-title">📤 Upload Research Papers</h2>
      <div className="upload-info">
        💡 Upload PDFs here to add them to your <strong>local knowledge base</strong>.
        Use <strong>📊 Analyse Documents</strong> to query them.
        The <strong>🔬 Research</strong> button fetches fresh papers from arXiv instead.
      </div>

      {/* Drop zone */}
      <div
        className={`upload-zone ${dragOver ? 'dragover' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        id="upload-zone"
      >
        <div className="upload-zone-icon">📄</div>
        <div className="upload-zone-text">
          Drag & drop a PDF here, or click to browse
        </div>
        <div className="upload-zone-hint">Supports .pdf files</div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          id="file-input"
        />
      </div>

      {/* File preview */}
      {selectedFile && (
        <div className="file-preview">
          <div className="file-info">
            <span>📎</span>
            <div>
              <div className="file-info-name">{selectedFile.name}</div>
              <div className="file-info-size">{(selectedFile.size / 1024).toFixed(1)} KB</div>
            </div>
          </div>
          <button
            className="btn-process"
            onClick={handleProcess}
            disabled={isProcessing}
            id="btn-process"
          >
            {isProcessing ? '⏳ Processing…' : '🚀 Process'}
          </button>
        </div>
      )}

      {/* Processing steps */}
      {isProcessing && (
        <div className="processing-steps">
          <div className="progress-step active">
            <span className="step-icon">⏳</span>
            Processing document…
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="processing-steps">
          <div className="progress-step" style={{ borderColor: 'rgba(239,68,68,0.3)', color: 'var(--error)' }}>
            <span className="step-icon">❌</span>
            {error}
          </div>
        </div>
      )}

      {/* Result */}
      {result && result.success && (
        <>
          <div className="processing-steps">
            <div className="progress-step completed">
              <span className="step-icon">✅</span>
              Successfully processed <strong>{result.filename}</strong>
            </div>
          </div>

          <div className="result-metrics">
            <div className="metric-card">
              <div className="metric-card-value">{result.pages}</div>
              <div className="metric-card-label">Pages</div>
            </div>
            <div className="metric-card">
              <div className="metric-card-value">{result.chunks}</div>
              <div className="metric-card-label">Chunks</div>
            </div>
            <div className="metric-card">
              <div className="metric-card-value">{result.avgChunkSize}</div>
              <div className="metric-card-label">Avg Size</div>
            </div>
          </div>

          <div className="processing-steps" style={{ marginTop: '12px' }}>
            <div className="progress-step completed">
              <span className="step-icon">📊</span>
              Total documents in database: <strong>{result.totalDocuments}</strong>
            </div>
          </div>
        </>
      )}

      {/* Current DB stats */}
      <div className="db-stats">
        <h3 className="db-stats-title">📊 Current Local Database</h3>
        <div className="db-stats-grid">
          <div className="metric-card">
            <div className="metric-card-value">{dbStats?.numDocuments ?? '—'}</div>
            <div className="metric-card-label">Total Chunks</div>
          </div>
          <div className="metric-card">
            <div className="metric-card-value">{dbStats?.uploadedPapers?.length ?? '—'}</div>
            <div className="metric-card-label">Papers</div>
          </div>
        </div>
      </div>
    </div>
  );
}
