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

export default api;
