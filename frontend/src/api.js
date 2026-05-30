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

export const suggestRecipe = (inventory, timeMode) => {
  const hasExpiry = inventory.some((i) => i.expiry_date)
  if (hasExpiry) {
    return api.post('/chef/suggest', { inventory_with_expiry: inventory, time_mode: timeMode })
  }
  return api.post('/chef/suggest', { inventory: inventory.map((i) => i.name || i), time_mode: timeMode })
};

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

// Inventory
export const getInventory = () => api.get('/inventory');
export const updateInventoryItem = (id, data) => api.put(`/inventory/${id}`, data);
export const deleteInventoryItem = (id) => api.delete(`/inventory/${id}`);

// Recipes
export const getSavedRecipes = (favoritesOnly = false) =>
  api.get('/auth/recipes', { params: { favorites_only: favoritesOnly } });
export const saveRecipe = (data) => api.post('/auth/recipes', data);
export const updateRecipe = (id, data) => api.put(`/auth/recipes/${id}`, data);
export const deleteRecipe = (id) => api.delete(`/auth/recipes/${id}`);
