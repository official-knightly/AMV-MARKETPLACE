import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../../lib/store';
import { ArrowLeft, Loader2 } from 'lucide-react';
import ChatBox from '../../components/ChatBox';
import api from '../../lib/api';
import toast from 'react-hot-toast';

export default function OrderChat() {
  const router = useRouter();
  const { orderId } = router.query;
  const { user, authReady } = useAuthStore();
  const [order, setOrder] = useState(null);
  const [otherUser, setOtherUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authReady) return;
    if (!user) {
      router.push('/login');
      return;
    }

    if (orderId) {
      loadOrderDetails();
    }
  }, [authReady, orderId, user]);

  const loadOrderDetails = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/orders/${orderId}`);
      const orderData = response.data;
      
      setOrder(orderData);
      
      // Determine the other user (buyer or seller)
      if (orderData.buyer_id === user.id) {
        setOtherUser({
          id: orderData.seller_id,
          username: orderData.seller_username || 'Seller',
          profile_image: orderData.seller_profile_image
        });
      } else if (orderData.seller_id === user.id) {
        setOtherUser({
          id: orderData.buyer_id,
          username: orderData.buyer_username || 'Buyer',
          profile_image: orderData.buyer_profile_image
        });
      } else {
        toast.error('You are not part of this order');
        router.push('/orders');
        return;
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error loading order:', error);
      toast.error('Failed to load order details');
      router.push('/orders');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white pt-20 pb-12">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Orders
          </button>
          
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h1 className="text-2xl font-bold mb-2">Order Chat</h1>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span>Order #{orderId}</span>
              <span>•</span>
              <span>{order?.gig_title}</span>
              <span>•</span>
              <span className="capitalize">{order?.status}</span>
            </div>
          </div>
        </div>

        {/* Chat Box */}
        <ChatBox orderId={parseInt(orderId)} otherUser={otherUser} />
      </div>
    </div>
  );
}
