import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_id');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// Auth
export const signup = (data) => api.post('/auth/signup', data);
export const signin = (data) => api.post('/auth/signin', data);
export const getProfile = () => api.get('/auth/me');
export const updateProfile = (data) => api.put('/auth/profile', data);

// Fridge
export const scanFridge = (file) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/scan_fridge', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const confirmScan = (data) => api.post('/inventory/confirm_scan', data);
export const manualAdd = (data) => api.post('/fridge/manual_add', data);

// Receipt
export const parseReceipt = (file) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/receipt/parse', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Chef
export const analyzeIngredient = (name) =>
  api.post('/chef/analyze-ingredient', { ingredient_name: name });

export const suggestRecipe = (inventory, timeMode) =>
  api.post('/chef/suggest', { inventory, time_mode: timeMode });

export const generateMenu = (inventory, lat, lon) =>
  api.post('/chef/generate-menu', { inventory, latitude: lat, longitude: lon });

export const cookRecipe = (recipeName, ingredients) =>
  api.post('/chef/cook', { recipe_name: recipeName, ingredients_used: ingredients });

// Substitutions
export const molecularSub = (ingredient, restriction, context) =>
  api.get('/substitute/molecular/' + encodeURIComponent(ingredient), {
    params: { restriction, recipe_context: context },
  });

export const philosophicalSub = (ingredient) =>
  api.get('/substitute/philosophical/' + encodeURIComponent(ingredient));

// Context
export const getEnvironment = (lat, lon) =>
  api.get('/context/environment', { params: { lat, lon } });

// Recipes
export const getSavedRecipes = (favoritesOnly = false) =>
  api.get('/auth/recipes', { params: { favorites_only: favoritesOnly } });
