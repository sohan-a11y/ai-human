/**
 * Screen View — live view of the agent's current screen
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Image, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator, ScrollView, Switch,
} from 'react-native';
import { api } from '../services/api';

export default function ScreenViewScreen() {
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const fetchScreen = useCallback(async () => {
    setLoading(true);
    try {
      const img = await api.getScreenshot();
      setImageB64(img);
      setLastUpdate(new Date().toLocaleTimeString());
    } catch (e: any) {
      console.warn('Screenshot failed:', e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScreen();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(fetchScreen, refreshInterval * 1000);
    return () => clearInterval(timer);
  }, [autoRefresh, refreshInterval, fetchScreen]);

  return (
    <View style={styles.container}>
      <View style={styles.toolbar}>
        <View style={styles.autoRow}>
          <Text style={styles.toolbarText}>Auto-refresh ({refreshInterval}s)</Text>
          <Switch
            value={autoRefresh}
            onValueChange={setAutoRefresh}
            thumbColor={autoRefresh ? '#6c63ff' : '#888'}
            trackColor={{ false: '#333', true: '#3a3480' }}
          />
        </View>
        <TouchableOpacity style={styles.refreshBtn} onPress={fetchScreen} disabled={loading}>
          <Text style={styles.refreshBtnText}>{loading ? '...' : '⟳ Refresh'}</Text>
        </TouchableOpacity>
      </View>

      {lastUpdate ? (
        <Text style={styles.updateTime}>Last updated: {lastUpdate}</Text>
      ) : null}

      <ScrollView contentContainerStyle={styles.imageContainer}>
        {loading && !imageB64 ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color="#6c63ff" />
            <Text style={styles.loadingText}>Capturing screen...</Text>
          </View>
        ) : imageB64 ? (
          <Image
            source={{ uri: `data:image/jpeg;base64,${imageB64}` }}
            style={styles.screenshot}
            resizeMode="contain"
          />
        ) : (
          <View style={styles.loadingBox}>
            <Text style={styles.noScreenText}>No screenshot available</Text>
            <Text style={styles.noScreenSub}>Make sure the agent is running</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f1a' },
  toolbar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 12, backgroundColor: '#1a1a2e', borderBottomWidth: 1, borderColor: '#2a2a4a',
  },
  autoRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  toolbarText: { color: '#aaa', fontSize: 13 },
  refreshBtn: {
    backgroundColor: '#6c63ff', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8,
  },
  refreshBtnText: { color: '#fff', fontWeight: '600' },
  updateTime: { color: '#666', fontSize: 11, textAlign: 'center', padding: 4 },
  imageContainer: { flexGrow: 1, padding: 8 },
  screenshot: { width: '100%', aspectRatio: 16 / 9, borderRadius: 8 },
  loadingBox: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  loadingText: { color: '#aaa', marginTop: 12 },
  noScreenText: { color: '#666', fontSize: 16, marginBottom: 8 },
  noScreenSub: { color: '#444', fontSize: 13 },
});
