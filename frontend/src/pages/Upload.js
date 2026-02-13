import React, { useState, useCallback } from 'react';
import { Upload as UploadIcon, X, Check, AlertCircle, Loader, Image } from 'lucide-react';
import { uploadImage } from '../services/api';
import './Upload.css';

const Upload = () => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const generateImageId = () => {
    return `img_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  }, []);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (newFiles) => {
    const imageFiles = newFiles.filter(file => file.type.startsWith('image/'));
    const filesWithStatus = imageFiles.map(file => ({
      file,
      id: generateImageId(),
      preview: URL.createObjectURL(file),
      status: 'pending', // pending, uploading, success, error
      result: null,
      error: null
    }));
    setFiles(prev => [...prev, ...filesWithStatus]);
  };

  const removeFile = (id) => {
    setFiles(prev => {
      const file = prev.find(f => f.id === id);
      if (file?.preview) {
        URL.revokeObjectURL(file.preview);
      }
      return prev.filter(f => f.id !== id);
    });
  };

  const uploadAllFiles = async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    setUploading(true);

    for (const fileObj of pendingFiles) {
      setFiles(prev => prev.map(f => 
        f.id === fileObj.id ? { ...f, status: 'uploading' } : f
      ));

      try {
        const result = await uploadImage(fileObj.file, fileObj.id);

        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, status: 'success', result } : f
        ));
      } catch (error) {
        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, status: 'error', error: error.message } : f
        ));
      }
    }

    setUploading(false);
  };

  const clearCompleted = () => {
    setFiles(prev => {
      prev.filter(f => f.status === 'success').forEach(f => {
        if (f.preview) URL.revokeObjectURL(f.preview);
      });
      return prev.filter(f => f.status !== 'success');
    });
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const successCount = files.filter(f => f.status === 'success').length;

  return (
    <div className="upload-page">
      <div 
        className={`upload-zone ${dragActive ? 'active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept="image/*"
          onChange={handleFileInput}
          className="file-input"
        />
        <label htmlFor="file-input" className="upload-label">
          <UploadIcon size={48} className="upload-icon" />
          <h3>Drag & drop photos here</h3>
          <p>or click to browse files</p>
          <span className="supported-formats">
            Supports: JPG, PNG, GIF, WebP
          </span>
        </label>
      </div>

      {files.length > 0 && (
        <div className="upload-controls">
          <div className="upload-stats">
            <span>{files.length} file(s) selected</span>
            {successCount > 0 && (
              <span className="success-count">{successCount} uploaded</span>
            )}
          </div>
          <div className="upload-actions">
            {successCount > 0 && (
              <button className="btn btn-secondary" onClick={clearCompleted}>
                Clear Completed
              </button>
            )}
            <button 
              className="btn btn-primary" 
              onClick={uploadAllFiles}
              disabled={uploading || pendingCount === 0}
            >
              {uploading ? (
                <>
                  <Loader size={16} className="spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadIcon size={16} />
                  Upload {pendingCount} Photo{pendingCount !== 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div className="file-list">
          {files.map(fileObj => (
            <div key={fileObj.id} className={`file-card ${fileObj.status}`}>
              <div className="file-preview">
                <img src={fileObj.preview} alt={fileObj.file.name} />
              </div>
              <div className="file-info">
                <span className="file-name">{fileObj.file.name}</span>
                <span className="file-size">
                  {(fileObj.file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                {fileObj.status === 'success' && fileObj.result && (
                  <div className="file-result">
                    <span className="caption">
                      📝 {fileObj.result.caption || 'No caption generated'}
                    </span>
                    <span className="faces">
                      👤 {fileObj.result.n_faces || 0} face(s) detected
                    </span>
                    {fileObj.result.album_tags && fileObj.result.album_tags.length > 0 && (
                      <span className="album-tags">
                        📁 Tags: {fileObj.result.album_tags.join(', ')}
                      </span>
                    )}
                  </div>
                )}
                {fileObj.status === 'error' && (
                  <span className="file-error">{fileObj.error}</span>
                )}
              </div>
              <div className="file-status">
                {fileObj.status === 'pending' && (
                  <button 
                    className="remove-btn"
                    onClick={() => removeFile(fileObj.id)}
                  >
                    <X size={18} />
                  </button>
                )}
                {fileObj.status === 'uploading' && (
                  <Loader size={20} className="spin status-icon uploading" />
                )}
                {fileObj.status === 'success' && (
                  <Check size={20} className="status-icon success" />
                )}
                {fileObj.status === 'error' && (
                  <AlertCircle size={20} className="status-icon error" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {files.length === 0 && (
        <div className="empty-state">
          <Image size={64} className="empty-icon" />
          <h3>No photos selected</h3>
          <p>Upload photos to get started with AI-powered organization</p>
        </div>
      )}
    </div>
  );
};

export default Upload;
