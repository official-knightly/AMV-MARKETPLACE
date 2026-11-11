import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Navbar from '../../components/Navbar';
import { getGig, createOrder, createStripeCheckoutSession } from '../../lib/api';
import { useAuthStore } from '../../lib/store';
import toast from 'react-hot-toast';
import { Star, Shield, Clock, CheckCircle } from 'lucide-react';

export default function GigDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { isAuthenticated } = useAuthStore();
  const [gig, setGig] = useState(null);
  const [message, setMessage] = useState('');
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    if (!id) return;
    getGig(id).then((res) => setGig(res.data)).catch(() => toast.error('Gig not found'));
  }, [id]);

  const handleOrder = async () => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    setPaying(true);
    try {
      const orderRes = await createOrder({ gig_id: parseInt(id, 10), message });
      const orderId = orderRes.data.order_id;
      const paymentRes = await createStripeCheckoutSession(orderId);
      if (!paymentRes.data.checkout_url) {
        throw new Error('Stripe did not return a checkout URL');
      }
      window.location.assign(paymentRes.data.checkout_url);
    } catch (e) {
      toast.error(e.response?.data?.error || e.message || 'Could not start secure checkout');
      setPaying(false);
    }
  };

  if (!gig) {
    return (
      <>
        <Navbar />
        <div className="pt-32 text-center text-white/50">Loading...</div>
      </>
    );
  }

  return (
    <>
      <Head>
        <title>{gig.title} - VORTEX</title>
      </Head>
      <Navbar />

      <main className="pt-24 pb-16 px-6">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-3 gap-10">
          <div className="lg:col-span-2">
            <div className="aspect-video rounded-2xl bg-gradient-to-br from-purple-600/20 to-pink-600/20 mb-6 overflow-hidden">
              {gig.video_url ? (
                <video src={gig.video_url} controls className="w-full h-full object-cover" />
              ) : gig.thumbnail ? (
                <img src={gig.thumbnail} alt={gig.title} className="w-full h-full object-cover" />
              ) : null}
            </div>
            <h1 className="text-3xl font-bold mb-4">{gig.title}</h1>
            <p className="text-white/70 whitespace-pre-wrap">{gig.description}</p>

            {gig.reviews?.length > 0 && (
              <div className="mt-10">
                <h2 className="text-xl font-semibold mb-4">Reviews</h2>
                {gig.reviews.map((r) => (
                  <div key={r.id} className="border-b border-white/10 py-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                      <span>{r.rating}</span>
                      <span className="text-white/40 text-sm">— {r.reviewer}</span>
                    </div>
                    <p className="text-sm text-white/60">{r.comment}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-24 bg-[#131313] border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-6">
                <img
                  src={gig.seller.profile_image || '/default-avatar.png'}
                  alt=""
                  className="w-12 h-12 rounded-full"
                />
                <div>
                  <p className="font-semibold">{gig.seller.username}</p>
                  <p className="text-xs text-white/50">Trust {gig.seller.trust_score}/5</p>
                </div>
              </div>

              <p className="text-display text-4xl mb-4">₹{gig.price}</p>

              <div className="space-y-2 text-sm text-white/60 mb-6">
                <p className="flex items-center gap-2"><Clock className="w-4 h-4" /> {gig.delivery_days} day delivery</p>
                <p className="flex items-center gap-2"><Star className="w-4 h-4 text-yellow-400" /> {gig.rating} ({gig.total_orders} orders)</p>
                <p className="flex items-center gap-2"><Shield className="w-4 h-4 text-green-400" /> Escrow protected</p>
              </div>

              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe what you need..."
                rows={4}
                className="w-full px-4 py-3 rounded-lg bg-black border border-white/10 mb-4 text-sm"
              />

              <button
                type="button"
                onClick={handleOrder}
                disabled={paying}
                className="w-full py-4 rounded-xl bg-white text-black font-semibold hover:bg-gray-200 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-5 h-5" />
                {paying ? 'Redirecting to Stripe...' : 'Pay securely with Stripe'}
              </button>

              <p className="text-xs text-white/40 mt-4 text-center">
                Secure Stripe Checkout. Funds stay in marketplace escrow until you approve delivery.
              </p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
