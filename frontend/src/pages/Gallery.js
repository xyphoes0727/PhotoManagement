import React, { useState, useEffect } from 'react';
import { 
  Grid, 
  List, 
  Filter, 
  SortAsc,
  Image,
  ZoomIn,
  Heart,
  Download,
  Trash2,
  X,
  Loader
} from 'lucide-react';
import { getPhotos, deletePhoto } from '../services/api';
import './Gallery.css';

const Gallery = () => {
  const [viewMode, setViewMode] = useState('grid'); // grid or list
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [filter, setFilter] = useState('all');
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPhotos();
  }, []);

  const fetchPhotos = async () => {
    try {
      setLoading(true);
      const data = await getPhotos();
      const formattedPhotos = (data.photos || []).map(photo => ({
        id: photo.id,
        name: photo.name,
        caption: photo.caption,
        albumId: photo.albumId || 0,
        faces: photo.faceCount || 0,
        uploadedAt: photo.uploadedAt,
        preview: photo.url,
        url: photo.url
      }));
      setPhotos(formattedPhotos);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filter photos - 'all' shows everything, otherwise filter by albumId
  const filteredPhotos = filter === 'all' 
    ? photos 
    : photos.filter(p => String(p.albumId) === filter);

  // Get unique album IDs for filtering
  const albumIds = ['all', ...new Set(photos.map(p => String(p.albumId)).filter(id => id !== '0'))];

  const openLightbox = (photo) => {
    setSelectedPhoto(photo);
  };

  const closeLightbox = () => {
    setSelectedPhoto(null);
  };

  const handleDeletePhoto = async (photoId) => {
    try {
      await deletePhoto(photoId);
      setPhotos(prev => prev.filter(p => p.id !== photoId));
      setSelectedPhoto(null);
    } catch (err) {
      console.error('Failed to delete photo:', err);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown';
    return new Date(isoString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="gallery-page">
        <div className="loading-state">
          <Loader size={48} className="spin" />
          <p>Loading photos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gallery-page">
        <div className="error-state">
          <p>Error: {error}</p>
          <button onClick={fetchPhotos}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="gallery-page">
      <div className="gallery-toolbar">
        <div className="toolbar-left">
          <div className="filter-group">
            <Filter size={18} />
            {albumIds.map(albumId => (
              <button
                key={albumId}
                className={`filter-btn ${filter === albumId ? 'active' : ''}`}
                onClick={() => setFilter(albumId)}
              >
                {albumId === 'all' ? 'All' : `Album ${albumId}`}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-right">
          <button className="sort-btn">
            <SortAsc size={18} />
            <span>Date</span>
          </button>
          <div className="view-toggle">
            <button 
              className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              <Grid size={18} />
            </button>
            <button 
              className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </div>

      <div className={`gallery-content ${viewMode}`}>
        {filteredPhotos.map(photo => (
          <div 
            key={photo.id} 
            className="photo-card"
            onClick={() => openLightbox(photo)}
          >
            <div className="photo-thumbnail">
              {photo.preview ? (
                <img src={photo.preview} alt={photo.name} className="thumbnail-img" />
              ) : (
                <Image size={48} className="placeholder-icon" />
              )}
              <div className="photo-overlay">
                <ZoomIn size={24} />
              </div>
            </div>
            {viewMode === 'list' && (
              <div className="photo-details">
                <span className="photo-name">{photo.name}</span>
                <span className="photo-caption">{photo.caption || 'No caption'}</span>
                <div className="photo-meta">
                  <span>{formatDate(photo.uploadedAt)}</span>
                  {photo.faces > 0 && <span>👤 {photo.faces}</span>}
                  {photo.albumId > 0 && <span className="photo-album">Album {photo.albumId}</span>}
                </div>
              </div>
            )}
            {viewMode === 'grid' && (
              <div className="photo-info">
                <span className="photo-name">{photo.name}</span>
                <span className="photo-date">{formatDate(photo.uploadedAt)}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredPhotos.length === 0 && (
        <div className="empty-gallery">
          <Image size={64} />
          <h3>No photos found</h3>
          <p>Try a different filter or upload some photos</p>
        </div>
      )}

      {/* Lightbox Modal */}
      {selectedPhoto && (
        <div className="lightbox" onClick={closeLightbox}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={closeLightbox}>
              <X size={24} />
            </button>
            
            <div className="lightbox-image">
              {selectedPhoto.preview ? (
                <img src={selectedPhoto.preview} alt={selectedPhoto.name} className="lightbox-img" />
              ) : (
                <Image size={120} className="placeholder-icon" />
              )}
            </div>
            
            <div className="lightbox-info">
              <h2>{selectedPhoto.name}</h2>
              <p className="lightbox-caption">{selectedPhoto.caption || 'No caption'}</p>
              
              <div className="lightbox-meta">
                <span>📅 {formatDate(selectedPhoto.uploadedAt)}</span>
                {selectedPhoto.albumId > 0 && <span>📁 Album {selectedPhoto.albumId}</span>}
                {selectedPhoto.faces > 0 && <span>👤 {selectedPhoto.faces} faces</span>}
              </div>
              
              <div className="lightbox-actions">
                <button className="lightbox-btn">
                  <Heart size={18} />
                  <span>Favorite</span>
                </button>
                <button className="lightbox-btn">
                  <Download size={18} />
                  <span>Download</span>
                </button>
                <button className="lightbox-btn danger" onClick={() => handleDeletePhoto(selectedPhoto.id)}>
                  <Trash2 size={18} />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Gallery;
