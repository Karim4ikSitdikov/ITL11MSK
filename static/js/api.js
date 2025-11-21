// API Base URL
const API_BASE_URL = window.location.origin;

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// Set auth token
function setAuthToken(token) {
    localStorage.setItem('access_token', token);
}

// Remove auth token
function removeAuthToken() {
    localStorage.removeItem('access_token');
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getAuthToken();
}

// API request wrapper
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    // Add auth token if available
    const token = getAuthToken();
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, config);

        // Check content type before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text);
            throw new Error('Сервер вернул неожиданный ответ. Проверьте консоль для деталей.');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Auth API
const AuthAPI = {
    register: async (email, password, preferences, fullName = null) => {
        const payload = { email, password, preferences };
        if (fullName) {
            payload.full_name = fullName;
        }
        return apiRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    login: async (email, password) => {
        return apiRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },

    getCurrentUser: async () => {
        return apiRequest('/api/auth/me');
    },

    logout: () => {
        removeAuthToken();
        window.location.href = '/';
    }
};

// Preferences API
const PreferencesAPI = {
    get: async () => {
        return apiRequest('/api/preferences');
    },

    update: async (preferences) => {
        return apiRequest('/api/preferences', {
            method: 'PUT',
            body: JSON.stringify(preferences)
        });
    }
};

// Chat API
const ChatAPI = {
    sendMessage: async (message) => {
        return apiRequest('/api/chat', {
            method: 'POST',
            body: JSON.stringify({ message })
        });
    },

    getHistory: async (limit = 50, offset = 0) => {
        return apiRequest(`/api/chat/history?limit=${limit}&offset=${offset}`);
    },

    clearHistory: async () => {
        return apiRequest('/api/chat/history', {
            method: 'DELETE'
        });
    }
};

// Lotteries API
const LotteriesAPI = {
    getAll: async (filters = {}) => {
        const params = new URLSearchParams(filters);
        return apiRequest(`/api/lotteries?${params}`);
    },

    getById: async (id) => {
        return apiRequest(`/api/lotteries/${id}`);
    },

    getRecommended: async () => {
        return apiRequest('/api/lotteries/recommended');
    }
};

// Analytics API
const AnalyticsAPI = {
    getSummary: async () => {
        return apiRequest('/api/analytics/summary');
    },

    getLotteryAnalytics: async (lotteryId) => {
        return apiRequest(`/api/analytics/lottery/${lotteryId}`);
    },

    getWinProbability: async (lotteryId) => {
        return apiRequest(`/api/analytics/win-probability/${lotteryId}`);
    }
};

// UI Helpers
function showError(message) {
    // You can implement a toast notification here
    alert(message);
}

function showSuccess(message) {
    // You can implement a toast notification here
    alert(message);
}

function showLoading(element) {
    element.classList.add('loading');
}

function hideLoading(element) {
    element.classList.remove('loading');
}

// Redirect if not authenticated
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/';
    }
}

// Check authentication on protected pages
if (window.location.pathname !== '/' && window.location.pathname !== '/register') {
    if (!isAuthenticated()) {
        window.location.href = '/';
    }
}
