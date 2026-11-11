import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const googleAuth = (token) => api.post('/auth/google', { token });
export const getCurrentUser = () => api.get('/auth/me');
export const requestPhoneOtp = (phone_number) => api.post('/auth/otp/request', { phone_number });

// Gigs
export const getGigs = (params) => api.get('/gigs', { params });
export const getGig = (id) => api.get(`/gigs/${id}`);
export const getGigFull = (id) => api.get(`/gigs/${id}/full`);
export const createGig = (data) => api.post('/gigs', data);
export const updateGig = (id, data) => api.put(`/gigs/${id}`, data);
export const addGigPackages = (id, packages) => api.post(`/gigs/${id}/packages`, { packages });
export const addGigExtras = (id, extras) => api.post(`/gigs/${id}/extras`, { extras });
export const addGigFaqs = (id, faqs) => api.post(`/gigs/${id}/faqs`, { faqs });

// Categories & discovery
export const getCategories = () => api.get('/categories');
export const search = (params) => api.get('/search', { params });
export const aiRecommendGigs = (params) => api.get('/ai/recommend-gigs', { params });
export const getMarketplaceFeatures = () => api.get('/marketplace/features');

// Sellers
export const getSellerProfile = (username) => api.get(`/sellers/${username}`);
export const updateSellerProfile = (data) => api.put('/sellers/profile', data);
export const getSellerAnalytics = () => api.get('/seller/analytics');

// Orders
export const createOrder = (data) => api.post('/orders/create', data);
export const createOrderFull = (data) => api.post('/orders/create-full', data);
export const getMyOrders = (role) => api.get('/orders/my-orders', { params: { role } });
export const completeOrder = (id) => api.post(`/orders/${id}/complete`);
export const deliverOrder = (id, data) => api.post(`/orders/${id}/deliver`, data);
export const requestRevision = (id, data) => api.post(`/orders/${id}/revision`, data);
export const requestAiVerify = (orderId) => api.post(`/orders/${orderId}/request-ai-verify`);

// Payment
export const createRazorpayPayment = (orderId) => api.post('/payment/razorpay/create', { order_id: orderId });
export const verifyRazorpayPayment = (data) => api.post('/payment/razorpay/verify', data);
export const createStripeCheckoutSession = (orderId) => api.post('/payment/stripe/create-checkout-session', { order_id: orderId });
export const confirmStripeCheckout = (sessionId) => api.post('/payment/stripe/confirm', { session_id: sessionId });
export const startStripeSellerOnboarding = () => api.post('/stripe/connect/onboarding');
export const getStripeSellerStatus = () => api.get('/stripe/connect/status');
export const createUPIPayment = (orderId) => api.post('/payment/upi/create', { order_id: orderId });
export const validateCoupon = (code) => api.post('/coupons/validate', { code });

// Withdrawal
export const requestWithdrawal = (data) => api.post('/withdrawal/request', data);
export const getWithdrawalHistory = () => api.get('/withdrawal/history');

// Wallet (Seller only)
export const getWalletBalance = () => api.get('/wallet/balance');
export const getWalletTransactions = () => api.get('/wallet/transactions');
export const getEarningsStats = () => api.get('/wallet/earnings-stats');
export const getWithdrawMethods = () => api.get('/wallet/withdraw-methods');
export const savePaymentMethod = (data) => api.post('/wallet/save-payment-method', data);

// Chat
export const getChatMessages = (orderId) => api.get(`/chat/messages/${orderId}`);
export const sendOrderChatMessage = (orderId, data) => api.post(`/chat/messages/${orderId}`, data);
export const requestOrderCancellation = (orderId, data) => api.post(`/orders/${orderId}/cancel`, data);
export const getOrderCancellation = (orderId) => api.get(`/orders/${orderId}/cancel`);
export const getUnreadCount = () => api.get('/chat/unread-count');

// Reviews
export const createReview = (data) => api.post('/reviews', data);

// Messaging
export const getConversations = () => api.get('/conversations');
export const startConversation = (data) => api.post('/conversations', data);
export const getMessages = (cid) => api.get(`/conversations/${cid}/messages`);
export const sendMessage = (cid, data) => api.post(`/conversations/${cid}/messages`, data);

// Notifications
export const getNotifications = () => api.get('/notifications');
export const readAllNotifications = () => api.post('/notifications/read-all');

// Favorites
export const getFavorites = () => api.get('/favorites');
export const toggleFavorite = (gigId) => api.post(`/favorites/${gigId}`);

// Custom offers & buyer requests
export const createCustomOffer = (data) => api.post('/custom-offers', data);
export const acceptCustomOffer = (id) => api.post(`/custom-offers/${id}/accept`);
export const getBuyerRequests = () => api.get('/buyer-requests');
export const postBuyerRequest = (data) => api.post('/buyer-requests', data);
export const pitchBuyerRequest = (id, data) => api.post(`/buyer-requests/${id}/offer`, data);

// Escrow
export const disputeEscrow = (orderId, data) => api.post(`/escrow/${orderId}/dispute`, data);
export const refundEscrow = (orderId) => api.post(`/escrow/${orderId}/refund`);

// AI Tools
export const removeBackground = (formData) => api.post('/ai/remove-background', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
});
export const greenScreen = (formData) => api.post('/ai/green-screen', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
});
export const detectPlagiarism = (formData) => api.post('/ai/detect-plagiarism', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 120000,
});
export const getAiGuardStatus = () => api.get('/ai/guard/status');

export const DONATE_URL = process.env.NEXT_PUBLIC_DONATE_UPI || 'https://urpy.link/gkLVl4';

export default api;
