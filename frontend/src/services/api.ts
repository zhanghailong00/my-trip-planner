import axios from 'axios';
import type { TripRequest, TripPlan } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const tripApi = {
  /**
   * 生成旅行计划
   */
  async createPlan(request: TripRequest): Promise<TripPlan> {
    const response = await api.post<TripPlan>('/trip/plan', request);
    return response.data;
  },
  
  /**
   * 健康检查
   */
  async checkHealth() {
    const response = await api.get('/health');
    return response.data;
  }
};
