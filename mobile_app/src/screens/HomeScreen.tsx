/**
 * Home Screen — main dashboard showing agent status and quick goal entry
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, RefreshControl, ActivityIndicator, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../services/api';

export default function HomeScreen() {
  const [goal, setGoal] = useState('');
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [events, setEvents] = useState<string[]>([]);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    loadStatus();
    const unsub = api.on('*', (msg) => {
      const entry = `[${msg.type}] ${JSON.stringify(msg.data).substring(0, 100)}`;
      setEvents(prev => [...prev.slice(-50), entry]);
      setTimeout(() => scrollRef.current?.scrollToEnd(), 100);
    });
    return unsub;
  }, []);

  const loadStatus = async () => {
    try {
      const s = await api.getStatus();
      setStatus(s);
    } catch (e: any) {
      setStatus({ error: e.message });
    }
  };

  const sendGoal = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    try {
      await api.sendGoal(goal.trim());
      setGoal('');
      Alert.alert('✅ Goal Sent', 'Agent is now working on your request.');
    } catch (e: any) {
      Alert.alert('❌ Error', e.message || 'Could not reach agent');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStatus();
    setRefreshing(false);
  };

  return (
    <View style={styles.container}>
      {/* Status Card */}
      <View style={styles.statusCard}>
        <View style={styles.statusRow}>
          <View style={[styles.dot, { backgroundColor: status?.error ? '#ff4444' : '#44ff44' }]} />
          <Text style={styles.statusText}>
            {status?.error ? 'Disconnected' : 'Agent Online'}
          </Text>
        </View>
        {status && !status.error && (
          <Text style={styles.statusDetail}>
            {status.current_goal ? `Working: ${status.current_goal.substring(0, 60)}...` : 'Idle — ready for tasks'}
          </Text>
        )}
      </View>

      {/* Goal Input */}
      <View style={styles.inputSection}>
        <TextInput
          style={styles.input}
          placeholder="What should your AI do? (e.g. 'Check my emails')"
          placeholderTextColor="#888"
          value={goal}
          onChangeText={setGoal}
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendButton, loading && styles.sendButtonDisabled]}
          onPress={sendGoal}
          disabled={loading || !goal.trim()}
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Ionicons name="send" size={22} color="#fff" />
          )}
        </TouchableOpacity>
      </View>

      {/* Event Stream */}
      <Text style={styles.sectionTitle}>Live Activity</Text>
      <ScrollView
        ref={scrollRef}
        style={styles.eventStream}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {events.length === 0 ? (
          <Text style={styles.emptyText}>No activity yet. Send a goal to get started.</Text>
        ) : (
          events.map((e, i) => (
            <Text key={i} style={styles.eventEntry}>{e}</Text>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f1a', padding: 16 },
  statusCard: {
    backgroundColor: '#1a1a2e', borderRadius: 12, padding: 14,
    marginBottom: 16, borderWidth: 1, borderColor: '#2a2a4a',
  },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  statusText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  statusDetail: { color: '#aaa', fontSize: 13, marginTop: 4 },
  inputSection: {
    flexDirection: 'row', alignItems: 'flex-end',
    backgroundColor: '#1a1a2e', borderRadius: 12,
    padding: 8, marginBottom: 16, borderWidth: 1, borderColor: '#2a2a4a',
  },
  input: {
    flex: 1, color: '#fff', fontSize: 15, padding: 8,
    maxHeight: 100, minHeight: 44,
  },
  sendButton: {
    backgroundColor: '#6c63ff', borderRadius: 10,
    width: 44, height: 44, justifyContent: 'center', alignItems: 'center',
  },
  sendButtonDisabled: { backgroundColor: '#3a3a6a' },
  sectionTitle: { color: '#aaa', fontSize: 12, fontWeight: '700', marginBottom: 8, letterSpacing: 1 },
  eventStream: { flex: 1, backgroundColor: '#1a1a2e', borderRadius: 12, padding: 10 },
  emptyText: { color: '#666', textAlign: 'center', marginTop: 20 },
  eventEntry: { color: '#88ddff', fontSize: 11, fontFamily: 'monospace', marginBottom: 3 },
});
