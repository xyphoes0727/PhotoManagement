import React, { useState, useEffect } from 'react';
import { 
  FolderOpen, 
  Plus, 
  MoreVertical,
  Image,
  Edit2,
  Trash2,
  X,
  Loader
} from 'lucide-react';
import { getAlbums, createAlbum, deleteAlbum, getPhotos } from '../services/api';
import './Albums.css';

const Albums = () => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAlbumName, setNewAlbumName] = useState('');
  const [selectedAlbum, setSelectedAlbum] = useState(null);
  const [albums, setAlbums] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [albumsData, photosData] = await Promise.all([
        getAlbums(),
        getPhotos()
      ]);
      
      const formattedAlbums = (albumsData.albums || []).map(album => ({
        id: album.id,
        name: album.name,
        photoCount: album.photoCount || album.photoIds?.length || 0,
        photoIds: album.photoIds || [],
        cover: album.coverPhotoUrl,
        createdAt: album.createdAt ? new Date(album.createdAt).toISOString().split('T')[0] : null
      }));
      setAlbums(formattedAlbums);
      
      const formattedPhotos = (photosData.photos || []).map(photo => ({
        id: photo.id,
        caption: photo.caption,
        faces: photo.faceCount || 0
      }));
      setPhotos(formattedPhotos);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Generate suggested albums based on photo captions
  const generateSuggestions = () => {
    if (photos.length === 0) return [];
    
    const suggestions = [];
    
    // Check for nature-related photos
    const naturePhotos = photos.filter(p => 
      (p.caption || '').toLowerCase().match(/nature|tree|forest|mountain|beach|sunset|sunrise|sky|flower|garden|outdoor/)
    );
    if (naturePhotos.length >= 2) {
      suggestions.push({ name: 'Nature', reason: `Based on ${naturePhotos.length} nature photos` });
    }
    
    // Check for people photos
    const peoplePhotos = photos.filter(p => p.faces > 0);
    if (peoplePhotos.length >= 2) {
      suggestions.push({ name: 'People', reason: `Based on ${peoplePhotos.length} photos with faces` });
    }
    
    // Check for food photos
    const foodPhotos = photos.filter(p => 
      (p.caption || '').toLowerCase().match(/food|meal|dinner|lunch|breakfast|cooking|restaurant|eat/)
    );
    if (foodPhotos.length >= 2) {
      suggestions.push({ name: 'Food & Dining', reason: `Based on ${foodPhotos.length} food photos` });
    }
    
    return suggestions.slice(0, 3);
  };

  const suggestedAlbums = generateSuggestions();

  const handleCreateAlbum = async (nameOrEvent) => {
    // Handle both direct name string and form submission (event or no arg)
    let albumName;
    if (typeof nameOrEvent === 'string') {
      albumName = nameOrEvent.trim();
    } else {
      albumName = newAlbumName.trim();
    }
    
    if (albumName) {
      try {
        const newAlbum = await createAlbum(albumName, '');
        setAlbums(prev => [...prev, {
          id: newAlbum.id,
          name: newAlbum.name,
          photoCount: 0,
          photoIds: [],
          cover: null,
          createdAt: new Date().toISOString().split('T')[0]
        }]);
        setNewAlbumName('');
        setShowCreateModal(false);
      } catch (error) {
        console.error('Failed to create album:', error);
        // Fallback to local creation
        const newAlbum = {
          id: `album_${Date.now()}`,
          name: albumName,
          photoCount: 0,
          photoIds: [],
          cover: null,
          createdAt: new Date().toISOString().split('T')[0]
        };
        setAlbums(prev => [...prev, newAlbum]);
        setNewAlbumName('');
        setShowCreateModal(false);
      }
    }
  };

  const handleDeleteAlbum = async (id) => {
    try {
      await deleteAlbum(id);
      setAlbums(prev => prev.filter(a => a.id !== id));
      setSelectedAlbum(null);
    } catch (error) {
      console.error('Failed to delete album:', error);
      // Still remove locally on error
      setAlbums(prev => prev.filter(a => a.id !== id));
      setSelectedAlbum(null);
    }
  };

  if (loading) {
    return (
      <div className="albums-page">
        <div className="loading-state">
          <Loader size={48} className="spin" />
          <p>Loading albums...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="albums-page">
      <div className="albums-header">
        <div className="albums-stats">
          <span>{albums.length} Albums</span>
          <span className="separator">•</span>
          <span>{albums.reduce((sum, a) => sum + a.photoCount, 0)} Photos</span>
        </div>
        <button 
          className="create-album-btn"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus size={18} />
          <span>Create Album</span>
        </button>
      </div>

      {suggestedAlbums.length > 0 && (
        <section className="suggested-section">
          <h2 className="section-title">✨ AI Suggested Albums</h2>
          <div className="suggested-albums">
            {suggestedAlbums.map((suggestion, index) => (
              <div key={index} className="suggested-card">
                <div className="suggested-icon">
                  <FolderOpen size={24} />
                </div>
                <div className="suggested-info">
                  <span className="suggested-name">{suggestion.name}</span>
                  <span className="suggested-reason">{suggestion.reason}</span>
                </div>
                <button className="suggested-btn" onClick={() => handleCreateAlbum(suggestion.name)}>Create</button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="albums-section">
        <h2 className="section-title">Your Albums</h2>
        <div className="albums-grid">
          {albums.map(album => (
            <div 
              key={album.id} 
              className="album-card"
              onClick={() => setSelectedAlbum(album)}
            >
              <div className="album-cover">
                <FolderOpen size={48} className="album-icon" />
                <div className="album-actions">
                  <button 
                    className="album-action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Edit action
                    }}
                  >
                    <Edit2 size={16} />
                  </button>
                  <button 
                    className="album-action-btn danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteAlbum(album.id);
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="album-info">
                <span className="album-name">{album.name}</span>
                <span className="album-count">{album.photoCount} photos</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {albums.length === 0 && (
        <div className="empty-albums">
          <FolderOpen size={64} />
          <h3>No albums yet</h3>
          <p>Create your first album to organize your photos</p>
          <button 
            className="create-album-btn"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={18} />
            <span>Create Album</span>
          </button>
        </div>
      )}

      {/* Create Album Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create New Album</h2>
              <button 
                className="modal-close"
                onClick={() => setShowCreateModal(false)}
              >
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <label className="form-label">Album Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="Enter album name..."
                value={newAlbumName}
                onChange={(e) => setNewAlbumName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateAlbum()}
                autoFocus
              />
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary"
                onClick={() => setShowCreateModal(false)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={handleCreateAlbum}
                disabled={!newAlbumName.trim()}
              >
                Create Album
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Album Detail View */}
      {selectedAlbum && (
        <div className="modal-overlay" onClick={() => setSelectedAlbum(null)}>
          <div className="album-detail-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedAlbum.name}</h2>
              <button 
                className="modal-close"
                onClick={() => setSelectedAlbum(null)}
              >
                <X size={20} />
              </button>
            </div>
            <div className="album-detail-body">
              <div className="album-detail-stats">
                <span>{selectedAlbum.photoCount} photos</span>
                <span>Created: {selectedAlbum.createdAt}</span>
              </div>
              
              {selectedAlbum.photoCount > 0 ? (
                <div className="album-photos-grid">
                  {[...Array(Math.min(selectedAlbum.photoCount, 12))].map((_, i) => (
                    <div key={i} className="album-photo-item">
                      <Image size={32} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-album">
                  <Image size={48} />
                  <p>No photos in this album</p>
                  <button className="btn btn-primary">Add Photos</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Albums;
