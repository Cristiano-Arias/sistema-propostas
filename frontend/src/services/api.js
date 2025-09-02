import axios from 'axios';

// Detecta automaticamente a URL da API no Render ou usa a local
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

const api = axios.create({
  baseURL: API_URL,
} );

// Adiciona o /api na frente de cada requisição
api.interceptors.request.use(config => {
    config.url = `/api${config.url}`;
    return config;
});

export default api;
