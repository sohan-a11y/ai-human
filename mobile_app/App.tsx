/**
 * AI Human Mobile Companion App
 * Root component with navigation
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, SafeAreaView, StatusBar,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from './src/services/api';
import HomeScreen from './src/screens/HomeScreen';
import ScreenViewScreen from './src/screens/ScreenViewScreen';
import TemplatesScreen from './src/screens/TemplatesScreen';

const Tab = createBottomTabNavigator();

export default function App() {
  const [serverConfigured, setServerConfigured] = useState(false);
  const [serverIp, setServerIp] = useState('');
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('server_url').then(url => {
      if (url) {
        setServerConfigured(true);
        api.connectWebSocket();
      }
    });
  }, []);

  const connect = async () => {
    if (!serverIp.trim()) return;
    setConnecting(true);
    try {
      await api.setServerUrl(serverIp.trim());
      // Test connection
      await api.getStatus();
      setServerConfigured(true);
    } catch (e: any) {
      Alert.alert('Connection Failed', `Cannot reach AI Human at ${serverIp}:8081\n\nMake sure:\n• Agent is running\n• Same WiFi network\n• Correct IP address`);
    } finally {
      setConnecting(false);
    }
  };

  if (!serverConfigured) {
    return (
      <SafeAreaView style={styles.setupContainer}>
        <StatusBar barStyle="light-content" backgroundColor="#0f0f1a" />
        <View style={styles.setupContent}>
          <Text style={styles.logo}>🤖</Text>
          <Text style={styles.setupTitle}>AI Human</Text>
          <Text style={styles.setupSubtitle}>Mobile Companion</Text>
          <Text style={styles.setupInstruction}>
            Enter the IP address of your PC running AI Human
          </Text>
          <TextInput
            style={styles.ipInput}
            placeholder="e.g. 192.168.1.100"
            placeholderTextColor="#666"
            value={serverIp}
            onChangeText={setServerIp}
            keyboardType="numeric"
            autoCapitalize="none"
          />
          <TouchableOpacity
            style={[styles.connectBtn, connecting && styles.connectBtnDisabled]}
            onPress={connect}
            disabled={connecting}
          >
            <Text style={styles.connectBtnText}>
              {connecting ? 'Connecting...' : 'Connect to AI Human'}
            </Text>
          </TouchableOpacity>
          <Text style={styles.helpText}>
            Find your PC IP: open Command Prompt and run{'\n'}
            <Text style={styles.code}>ipconfig</Text> (look for IPv4 Address)
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#0f0f1a" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarIcon: ({ focused, color, size }) => {
            const icons: Record<string, string> = {
              Home: focused ? 'home' : 'home-outline',
              Screen: focused ? 'desktop' : 'desktop-outline',
              Templates: focused ? 'list' : 'list-outline',
            };
            return <Ionicons name={icons[route.name] as any} size={size} color={color} />;
          },
          tabBarActiveTintColor: '#6c63ff',
          tabBarInactiveTintColor: '#555',
          tabBarStyle: { backgroundColor: '#1a1a2e', borderTopColor: '#2a2a4a' },
          headerStyle: { backgroundColor: '#1a1a2e' },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: '700' },
        })}
      >
        <Tab.Screen name="Home" component={HomeScreen} options={{ title: 'AI Human' }} />
        <Tab.Screen name="Screen" component={ScreenViewScreen} options={{ title: 'Live Screen' }} />
        <Tab.Screen name="Templates" component={TemplatesScreen} options={{ title: 'Templates' }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  setupContainer: { flex: 1, backgroundColor: '#0f0f1a' },
  setupContent: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  logo: { fontSize: 64, marginBottom: 16 },
  setupTitle: { color: '#fff', fontSize: 32, fontWeight: '800', letterSpacing: 1 },
  setupSubtitle: { color: '#6c63ff', fontSize: 16, marginBottom: 40, letterSpacing: 2 },
  setupInstruction: { color: '#aaa', fontSize: 15, textAlign: 'center', marginBottom: 20 },
  ipInput: {
    width: '100%', backgroundColor: '#1a1a2e', color: '#fff',
    borderRadius: 12, padding: 16, fontSize: 18, textAlign: 'center',
    borderWidth: 1, borderColor: '#2a2a4a', marginBottom: 16,
  },
  connectBtn: {
    width: '100%', backgroundColor: '#6c63ff', borderRadius: 12,
    padding: 16, alignItems: 'center', marginBottom: 24,
  },
  connectBtnDisabled: { backgroundColor: '#3a3480' },
  connectBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  helpText: { color: '#666', fontSize: 13, textAlign: 'center', lineHeight: 20 },
  code: { color: '#88ddff', fontFamily: 'monospace' },
});
