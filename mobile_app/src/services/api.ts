/**
 * API service — connects to the AI Human mobile bridge server.
 * All calls go to http://{serverIP}:8081
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEFAULT_PORT = 8081;

class ApiService {
  private baseUrl: string = '';
  private ws: WebSocket | null = null;
  private eventHandlers: Map<string, ((data: any) => void)[]> = new Map();

  async getServerUrl(): Promise<string> {
    if (this.baseUrl) return this.baseUrl;
    const saved = await AsyncStorage.getItem('server_url');
    if (saved) {
      this.baseUrl = saved;
      return saved;
    }
    return '';
  }

  async setServerUrl(ip: string, port: number = DEFAULT_PORT): Promise<void> {
    this.baseUrl = `http://${ip}:${port}`;
    await AsyncStorage.setItem('server_url', this.baseUrl);
    this.connectWebSocket();
  }

  async getStatus(): Promise<any> {
    const url = await this.getServerUrl();
    const r = await axios.get(`${url}/mobile/status`, { timeout: 5000 });
    return r.data;
  }

  async sendGoal(goal: string): Promise<any> {
    const url = await this.getServerUrl();
    const r = await axios.post(`${url}/mobile/goal`, { goal }, { timeout: 10000 });
    return r.data;
  }

  async getScreenshot(): Promise<string> {
    const url = await this.getServerUrl();
    const r = await axios.get(`${url}/mobile/screenshot/base64`, { timeout: 15000 });
    return r.data.image;  // base64 JPEG
  }

  async getNotifications(): Promise<any[]> {
    const url = await this.getServerUrl();
    const r = await axios.get(`${url}/mobile/notifications`, { timeout: 5000 });
    return r.data.notifications || [];
  }

  async dismissNotification(id: string): Promise<void> {
    const url = await this.getServerUrl();
    await axios.post(`${url}/mobile/notification/dismiss`, { id }, { timeout: 5000 });
  }

  async getTemplates(): Promise<any[]> {
    const url = await this.getServerUrl();
    const r = await axios.get(`${url}/mobile/templates`, { timeout: 5000 });
    return r.data.templates || [];
  }

  async runTemplate(templateId: string, params: Record<string, string>): Promise<any> {
    const url = await this.getServerUrl();
    const r = await axios.post(
      `${url}/mobile/template/run`,
      { template_id: templateId, params },
      { timeout: 10000 }
    );
    return r.data;
  }

  async sendVoice(audioBase64: string): Promise<{ transcription: string; status: string }> {
    const url = await this.getServerUrl();
    const r = await axios.post(
      `${url}/mobile/voice`,
      { audio: audioBase64 },
      { timeout: 30000 }
    );
    return r.data;
  }

  connectWebSocket(): void {
    if (this.ws) {
      this.ws.close();
    }
    const wsUrl = this.baseUrl.replace('http://', 'ws://') + '/mobile/stream';
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const handlers = this.eventHandlers.get(msg.type) || [];
          handlers.forEach(h => h(msg.data));
          const allHandlers = this.eventHandlers.get('*') || [];
          allHandlers.forEach(h => h(msg));
        } catch {}
      };
      this.ws.onerror = () => {
        setTimeout(() => this.connectWebSocket(), 5000);
      };
      this.ws.onclose = () => {
        setTimeout(() => this.connectWebSocket(), 5000);
      };
    } catch {}
  }

  on(eventType: string, handler: (data: any) => void): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);
    return () => {
      const handlers = this.eventHandlers.get(eventType) || [];
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    };
  }
}

export const api = new ApiService();
