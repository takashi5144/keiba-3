import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Centralized Axios client for the frontend
const apiBaseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const apiClient: AxiosInstance = axios.create({
  baseURL: apiBaseUrl,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Simple helper to wrap API calls and always return AxiosResponse-like shape
async function safeCall<T>(fn: () => Promise<AxiosResponse<T>>): Promise<AxiosResponse<T>> {
  try {
    return await fn();
  } catch (error) {
    // Re-throw so caller hooks (React Query) can handle errors appropriately
    throw error;
  }
}

export const api = {
  prediction: {
    // POST /v1/prediction/predict/today
    predictToday: (payload: Record<string, unknown>) =>
      safeCall(() => apiClient.post('/v1/prediction/predict/today', payload)),

    // GET /v1/prediction/models
    getModels: () => safeCall(() => apiClient.get('/v1/prediction/models')),

    // POST /v1/prediction/backtest
    backtest: (payload: {
      start_date: string;
      end_date: string;
      initial_budget: number;
      min_expected_value: number;
    }) => safeCall(() => apiClient.post('/v1/prediction/backtest', payload)),

    // POST /v1/prediction/predict/batch
    predictBatch: (payload: { target_date: string; place?: string }) =>
      safeCall(() => apiClient.post('/v1/prediction/predict/batch', payload)),
  },
};

export type ApiType = typeof api;


