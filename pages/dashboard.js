import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { Package, DollarSign, Star, TrendingUp, RefreshCw } from 'lucide-react';
import { useAuthStore } from '../lib/store';
import { getMyOrders } from '../lib/api';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const router = useRouter();
  const { user, isAuthenticated, authReady, updateUser } = useAuthStore();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('buyer');
  const [currentRole, setCurrentRole] = useState('buyer');

  useEffect(() => {
    if (!authReady) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    
    // Check if user has selected a role
    if (!user?.account_type && !user?.is_seller) {
      router.push('/select-role');
      return;
    }
    
    setCurrentRole(user?.is_seller ? 'seller' : 'buyer');
    loadOrders();
  }, [authReady, isAuthenticated, activeTab]);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const res = await getMyOrders(activeTab);
      setOrders(res.data.orders || []);
    } catch (error) {
      console.error('Failed to load orders:', error);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRoleSwitch = async (newRole) => {
    try {
      const res = await api.post('/user/switch-role', { role: newRole });
      setCurrentRole(newRole);
      setActiveTab(newRole);
      updateUser({ is_seller: newRole === 'seller', account_type: newRole });
      toast.success(`Switched to ${newRole} mode!`);
    } catch (error) {
      toast.error('Failed to switch role');
    }
  };

  if (!authReady || !isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-bg text-white pt-24 pb-20 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div>
              <h1 className="text-display text-6xl md:text-8xl mb-2">DASHBOARD</h1>
              <p className="text-white/60 text-lg">Welcome back, {user?.username}!</p>
            </div>
            
            {/* Role Switcher */}
            <div className="flex items-center gap-3 bg-card border border-white/10 rounded-xl p-2">
              <button
                onClick={() => handleRoleSwitch('buyer')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                  currentRole === 'buyer'
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <Package className="w-4 h-4" />
                Buyer Mode
              </button>
              <button
                onClick={() => handleRoleSwitch('seller')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition ${
                  currentRole === 'seller'
                    ? 'bg-gradient-to-r from-green-600 to-teal-600 text-white'
                    : 'text-white/60 hover:text-white'
                }`}
              >
                <DollarSign className="w-4 h-4" />
                Seller Mode
              </button>
            </div>
          </div>
          
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10">
            <div className={`w-2 h-2 rounded-full ${currentRole === 'seller' ? 'bg-green-500' : 'bg-purple-500'} animate-pulse`} />
            <span className="text-sm">
              Currently in <span className="font-semibold capitalize">{currentRole}</span> mode
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <div className="bg-card border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                <Package className="w-6 h-6 text-purple-500" />
              </div>
              <div>
                <div className="text-3xl font-bold">{orders.length}</div>
                <div className="text-sm text-white/50">Total Orders</div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <div className="text-3xl font-bold">₹{user?.balance?.toFixed(2) || '0.00'}</div>
                <div className="text-sm text-white/50">Balance</div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-12 h-12 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                <Star className="w-6 h-6 text-yellow-500" />
              </div>
              <div>
                <div className="text-3xl font-bold">{user?.trust_score?.toFixed(1) || '5.0'}</div>
                <div className="text-sm text-white/50">Trust Score</div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-white/10 rounded-2xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <div className="text-3xl font-bold">{user?.is_seller ? 'Seller' : 'Buyer'}</div>
                <div className="text-sm text-white/50">Account Type</div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {currentRole === 'buyer' ? (
            <>
              <Link href="/marketplace" className="bg-gradient-to-br from-purple-600 to-blue-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">Browse Marketplace</h3>
                <p className="text-white/80 text-sm">Find talented editors</p>
              </Link>

              <Link href="/ai-tools" className="bg-gradient-to-br from-blue-600 to-cyan-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">AI Tools</h3>
                <p className="text-white/80 text-sm">Use free editing tools</p>
              </Link>

              <Link href="/orders" className="bg-gradient-to-br from-orange-600 to-red-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">My Orders</h3>
                <p className="text-white/80 text-sm">Track your purchases</p>
              </Link>
            </>
          ) : (
            <>
              <Link href="/create-gig" className="bg-gradient-to-br from-green-600 to-teal-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">Create Gig</h3>
                <p className="text-white/80 text-sm">List your services</p>
              </Link>

              <Link href="/my-gigs" className="bg-gradient-to-br from-teal-600 to-blue-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">My Gigs</h3>
                <p className="text-white/80 text-sm">Manage your listings</p>
              </Link>

              <Link href="/wallet" className="bg-gradient-to-br from-orange-600 to-red-600 rounded-2xl p-6 hover:scale-105 transition">
                <h3 className="text-xl font-bold mb-2">Wallet</h3>
                <p className="text-white/80 text-sm">Withdraw earnings</p>
              </Link>
            </>
          )}
        </div>

        {/* Orders */}
        <div className="bg-card border border-white/10 rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">My Orders</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('buyer')}
                className={`px-4 py-2 rounded-lg text-sm transition ${
                  activeTab === 'buyer' ? 'bg-white text-black' : 'border border-white/20 hover:bg-white/5'
                }`}
              >
                As Buyer
              </button>
              <button
                onClick={() => setActiveTab('seller')}
                className={`px-4 py-2 rounded-lg text-sm transition ${
                  activeTab === 'seller' ? 'bg-white text-black' : 'border border-white/20 hover:bg-white/5'
                }`}
              >
                As Seller
              </button>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin w-8 h-8 border-2 border-white/20 border-t-white rounded-full mx-auto mb-3" />
              <p className="text-white/60">Loading orders...</p>
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-white/60 mb-4">No orders yet</p>
              <Link href="/marketplace" className="inline-block px-6 py-3 rounded-lg bg-white text-black font-semibold hover:bg-gray-200 transition">
                Browse Marketplace
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {orders.map((order) => (
                <div key={order.id} className="bg-surface border border-white/10 rounded-xl p-6 hover:border-white/20 transition">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold mb-1">{order.gig_title}</h3>
                      <p className="text-sm text-white/50">
                        {activeTab === 'buyer' ? `Seller: ${order.seller}` : `Buyer: ${order.buyer}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold">₹{order.amount}</div>
                      <div className={`text-xs px-3 py-1 rounded-full inline-block mt-1 ${
                        order.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                        order.status === 'in_progress' ? 'bg-blue-500/20 text-blue-500' :
                        'bg-yellow-500/20 text-yellow-500'
                      }`}>
                        {order.status}
                      </div>
                    </div>
                  </div>
                  <div className="flex justify-between items-center text-sm text-white/50">
                    <span>{new Date(order.created_at).toLocaleDateString()}</span>
                    <Link href={`/order/${order.id}`} className="text-white hover:underline">
                      View Details →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
