import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  transformResponse: [(data) => {
    // Handle double-encoded JSON from Django HttpResponse
    try {
      const parsed = JSON.parse(data);
      // If it's still a string (double-encoded), parse again
      if (typeof parsed === 'string') {
        console.log(parsed);
        
        return JSON.parse(parsed);
      }
      return parsed;
    } catch (e) {
      return data;
    }
  }],
});

// Query photos using text search
export const queryPhotos = async (query) => {
  try {
    const response = await api.post('/api/query/', { query });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to search photos');
  }
};

// Upload an image for processing
export const uploadImage = async (imageFile, imageId) => {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('image_id', imageId);
    
    // Use axios directly for FormData to avoid transformResponse issues
    const response = await axios.post(`${API_BASE_URL}/api/upload/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Parse the response data if it's a string
    let data = response.data;
    if (typeof data === 'string') {
      data = JSON.parse(data);
    }
    return data;
  } catch (error) {
    console.error('Upload error:', error);
    throw new Error(error.response?.data?.error || 'Failed to upload image');
  }
};

// Get caption for an image
export const captionImage = async (imageFile, imageId) => {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('image_id', imageId);
    
    const response = await axios.post(`${API_BASE_URL}/api/caption/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    let data = response.data;
    if (typeof data === 'string') {
      data = JSON.parse(data);
    }
    return data;
  } catch (error) {
    console.error('Caption error:', error);
    throw new Error(error.response?.data?.error || 'Failed to caption image');
  }
};

// Detect faces in an image
export const detectFaces = async (imageFile, imageId) => {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('image_id', imageId);
    
    const response = await axios.post(`${API_BASE_URL}/api/face/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    let data = response.data;
    if (typeof data === 'string') {
      data = JSON.parse(data);
    }
    return data;
  } catch (error) {
    console.error('Face detection error:', error);
    throw new Error(error.response?.data?.error || 'Failed to detect faces');
  }
};

// Get album suggestions for an image
export const getAlbumization = async (imageCaption) => {
  try {
    const response = await api.post('/api/albumization/', { image_caption: imageCaption });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to get album suggestions');
  }
};

// Get all photos
export const getPhotos = async () => {
  try {
    const response = await api.get('/api/photos/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch photos');
  }
};

// Get a single photo by ID
export const getPhoto = async (photoId) => {
  try {
    const response = await api.get(`/api/photos/${photoId}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch photo');
  }
};

// Delete a photo
export const deletePhoto = async (photoId) => {
  try {
    const response = await api.delete(`/api/photos/${photoId}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to delete photo');
  }
};

// Get all albums
export const getAlbums = async () => {
  try {
    const response = await api.get('/api/albums/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch albums');
  }
};

// Get a single album by ID
export const getAlbum = async (albumId) => {
  try {
    const response = await api.get(`/api/albums/${albumId}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch album');
  }
};

// Create a new album
export const createAlbum = async (name, description = '') => {
  try {
    const response = await api.post('/api/albums/', { name, description });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to create album');
  }
};

// Delete an album
export const deleteAlbum = async (albumId) => {
  try {
    const response = await api.delete(`/api/albums/${albumId}/`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to delete album');
  }
};

// Add photos to an album
export const addPhotosToAlbum = async (albumId, photoIds) => {
  try {
    const response = await api.post(`/api/albums/${albumId}/photos/`, { photoIds });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to add photos to album');
  }
};

// Get stats
export const getStats = async () => {
  try {
    const response = await api.get('/api/stats/');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to fetch stats');
  }
};

export default api;
