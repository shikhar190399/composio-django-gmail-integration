/**
 * API client for email service
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || error.message || 'Request failed');
  }
  
  return response.json();
}

export const api = {
  // Emails
  getEmails: (page = 1) => request(`/emails/?page=${page}`),
  getEmail: (id) => request(`/emails/${id}/`),
  markRead: (id) => request(`/emails/${id}/mark_read/`, { method: 'POST' }),
  getStats: () => request('/emails/stats/'),
  
  // Connection
  getConnectionStatus: () => request('/connect/status/'),
  initiateConnection: (userId = 'default-user') => 
    request('/connect/', { 
      method: 'POST', 
      body: JSON.stringify({ user_id: userId }) 
    }),
  completeConnection: (userId, connectedAccountId) =>
    request('/connect/complete/', {
      method: 'POST',
      body: JSON.stringify({ 
        user_id: userId, 
        connected_account_id: connectedAccountId 
      }),
    }),
  
  // Sync
  syncEmails: () => request('/sync/', { method: 'POST' }),
};

