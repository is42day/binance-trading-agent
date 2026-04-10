// In production (served via nginx), use relative paths - nginx proxies /api/* to FastAPI
// In development (npm run dev), use localhost:8000 (vite proxies too)
// VITE_API_URL can be set explicitly if needed
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? '';
