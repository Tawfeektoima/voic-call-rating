import axios from 'axios';

/**
 * Centralized API client for the Voice Call Rating Platform.
 * Connects to the FastAPI backend via the /api proxy.
 */
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Auth Token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Global Error Handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized (e.g., redirect to login or clear state)
    if (error.response && error.response.status === 401) {
      console.warn('Unauthorized access detected. Clearing session.');
      localStorage.removeItem('token');
      // window.location.href = '/login'; // Optional: Redirect to login
    }

    // You can add more global error handling here (e.g., 500 server errors)
    return Promise.reject(error);
  }
);

export default api;
