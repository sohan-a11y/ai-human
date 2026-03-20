/**
 * Templates Screen — browse and run task templates
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  Alert, TextInput, Modal, ScrollView,
} from 'react-native';
import { api } from '../services/api';

const CATEGORY_COLORS: Record<string, string> = {
  productivity: '#6c63ff',
  development: '#00cc88',
  research: '#ff9900',
  system: '#ff4466',
  communication: '#00aaff',
};

export default function TemplatesScreen() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [modalVisible, setModalVisible] = useState(false);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    api.getTemplates().then(setTemplates).catch(console.warn);
  }, []);

  const openTemplate = (template: any) => {
    setSelected(template);
    // Initialize params with empty strings
    const initParams: Record<string, string> = {};
    Object.keys(template.parameters || {}).forEach(k => { initParams[k] = ''; });
    setParams(initParams);
    setModalVisible(true);
  };

  const runTemplate = async () => {
    if (!selected) return;
    try {
      await api.runTemplate(selected.id, params);
      setModalVisible(false);
      Alert.alert('✅ Started', `Running: ${selected.name}`);
    } catch (e: any) {
      Alert.alert('❌ Error', e.message);
    }
  };

  const filtered = templates.filter(t =>
    !filter || t.name.toLowerCase().includes(filter.toLowerCase()) ||
    t.category.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search templates..."
        placeholderTextColor="#666"
        value={filter}
        onChangeText={setFilter}
      />
      <FlatList
        data={filtered}
        keyExtractor={t => t.id}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.card} onPress={() => openTemplate(item)}>
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <View style={[styles.badge, { backgroundColor: CATEGORY_COLORS[item.category] || '#555' }]}>
                <Text style={styles.badgeText}>{item.category}</Text>
              </View>
            </View>
            <Text style={styles.cardDesc}>{item.description}</Text>
            <Text style={styles.cardMeta}>~{item.estimated_minutes} min  •  {(item.tags || []).join(', ')}</Text>
          </TouchableOpacity>
        )}
        contentContainerStyle={{ padding: 12 }}
      />

      {/* Template Run Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{selected?.name}</Text>
            <Text style={styles.modalDesc}>{selected?.description}</Text>
            <ScrollView style={styles.paramsScroll}>
              {selected && Object.entries(selected.parameters || {}).map(([key, desc]) => (
                <View key={key} style={styles.paramRow}>
                  <Text style={styles.paramLabel}>{key}</Text>
                  <Text style={styles.paramDesc}>{String(desc)}</Text>
                  <TextInput
                    style={styles.paramInput}
                    placeholder={`Enter ${key}...`}
                    placeholderTextColor="#666"
                    value={params[key] || ''}
                    onChangeText={v => setParams(p => ({ ...p, [key]: v }))}
                  />
                </View>
              ))}
            </ScrollView>
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.runBtn} onPress={runTemplate}>
                <Text style={styles.runBtnText}>▶ Run Template</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f1a' },
  search: {
    margin: 12, backgroundColor: '#1a1a2e', color: '#fff',
    borderRadius: 10, padding: 10, fontSize: 15,
    borderWidth: 1, borderColor: '#2a2a4a',
  },
  card: {
    backgroundColor: '#1a1a2e', borderRadius: 12, padding: 14,
    marginBottom: 10, borderWidth: 1, borderColor: '#2a2a4a',
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  cardTitle: { color: '#fff', fontWeight: '700', fontSize: 15, flex: 1 },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3, marginLeft: 8 },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  cardDesc: { color: '#aaa', fontSize: 13, marginBottom: 6 },
  cardMeta: { color: '#666', fontSize: 11 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end' },
  modalContent: {
    backgroundColor: '#1a1a2e', borderTopLeftRadius: 20, borderTopRightRadius: 20,
    padding: 20, maxHeight: '85%',
  },
  modalTitle: { color: '#fff', fontSize: 18, fontWeight: '700', marginBottom: 6 },
  modalDesc: { color: '#aaa', fontSize: 13, marginBottom: 14 },
  paramsScroll: { maxHeight: 300 },
  paramRow: { marginBottom: 14 },
  paramLabel: { color: '#6c63ff', fontWeight: '600', fontSize: 13, marginBottom: 2 },
  paramDesc: { color: '#888', fontSize: 12, marginBottom: 4 },
  paramInput: {
    backgroundColor: '#0f0f1a', color: '#fff', borderRadius: 8,
    padding: 10, fontSize: 14, borderWidth: 1, borderColor: '#2a2a4a',
  },
  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 16 },
  cancelBtn: { flex: 1, padding: 14, borderRadius: 10, borderWidth: 1, borderColor: '#3a3a5a', alignItems: 'center' },
  cancelBtnText: { color: '#aaa', fontWeight: '600' },
  runBtn: { flex: 2, backgroundColor: '#6c63ff', padding: 14, borderRadius: 10, alignItems: 'center' },
  runBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
