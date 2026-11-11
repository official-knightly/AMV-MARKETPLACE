import { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import OrderChat from '../components/OrderChat';
import { useAuthStore } from '../lib/store';
import { getMyOrders, completeOrder, deliverOrder, disputeEscrow, requestAiVerify, confirmStripeCheckout, requestOrderCancellation, respondToDispute } from '../lib/api';
import toast from 'react-hot-toast';
import { Shield, CheckCircle, AlertTriangle, Bot, Download } from 'lucide-react';

export default function Orders() {
  const router = useRouter();
  const { isAuthenticated, authReady } = useAuthStore();
  const [tab, setTab] = useState('buyer');
  const [orders, setOrders] = useState([]);
  const [deliveryUrl, setDeliveryUrl] = useState({});
  const [aiLoading, setAiLoading] = useState(null);
  const [stripeSessionHandled, setStripeSessionHandled] = useState(false);

  const load = () => {
    getMyOrders(tab).then((res) => setOrders(res.data.orders)).catch(console.error);
  };

  useEffect(() => {
    if (!authReady) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    if (router.query.session_id && !stripeSessionHandled) {
      setStripeSessionHandled(true);
      confirmStripeCheckout(String(router.query.session_id))
        .then((res) => toast.success(res.data.message || 'Stripe payment confirmed'))
        .catch((error) => toast.error(error.response?.data?.error || 'Payment confirmation is still pending'))
        .finally(load);
    } else {
      load();
    }
  }, [authReady, isAuthenticated, tab, router, router.query.session_id, stripeSessionHandled]);

  const handleConfirmReceived = async (id) => {
    if (!confirm('Confirm you received the AMV? Escrow will release to the seller.')) return;
    try {
      const res = await completeOrder(id);
      toast.success(res.data.message || 'Payment released');
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed');
    }
  };

  const handleAiVerify = async (id) => {
    setAiLoading(id);
    try {
      const res = await requestAiVerify(id);
      toast.success(res.data.message);
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'AI verification failed');
    } finally {
      setAiLoading(null);
    }
  };

  const handleDeliver = async (id) => {
    const url = deliveryUrl[id];
    if (!url) {
      toast.error('Enter delivery file URL (video link)');
      return;
    }
    try {
      const res = await deliverOrder(id, { file_url: url });
      toast.success(res.data.message);
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed');
    }
  };

  const handleDisputeResponse = async (id) => {
    const response = window.prompt('Explain your response to the buyer\'s dispute:');
    if (!response) return;
    try {
      await respondToDispute(id, { response });
      toast.success('Your dispute response was submitted');
      load();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not submit dispute response');
    }
  };

  const handleCancel = async (id) => {
    const reason = prompt('Why should this order be cancelled?');
    if (!reason) return;
    try {
      const res = await requestOrderCancellation(id, { reason });
      toast.success(res.data.message || 'Cancellation request submitted');
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Could not request cancellation');
    }
  };

  const handleDispute = async (id) => {
    const reason = prompt('Why are you opening a dispute?');
    if (!reason) return;
    try {
      await disputeEscrow(id, { reason });
      toast.success('Dispute opened — escrow held');
      load();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed');
    }
  };

  if (!isAuthenticated) return null;

  return (
    <>
      <Head><title>Orders - VORTEX</title></Head>
      <main className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-display text-5xl mb-2">ORDERS</h1>
          <p className="text-white/50 text-sm mb-8 flex items-center gap-2">
            <Bot className="w-4 h-4 text-purple-400" />
            Stripe Checkout · order chat · AI safety checks · buyer confirms delivery before release
          </p>

          <div className="flex gap-2 mb-8">
            {['buyer', 'seller'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-lg capitalize ${tab === t ? 'bg-white text-black' : 'border border-white/10'}`}
              >
                As {t}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {orders.map((o) => (
              <div key={o.id} className="bg-[#131313] border border-white/10 rounded-xl p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold">{o.gig_title}</h3>
                    <p className="text-sm text-white/50">
                      {o.status} · <Shield className="w-3 h-3 inline text-green-400" /> escrow: {o.escrow_status}
                    </p>
                    {o.delivered_at && (
                      <p className="text-xs text-white/40 mt-1">Delivered {new Date(o.delivered_at).toLocaleString()}</p>
                    )}
                    {o.ai_verification_score != null && (
                      <p className="text-xs text-purple-400 mt-1">AI score: {o.ai_verification_score} {o.ai_verified ? '✓' : ''}</p>
                    )}
                    {o.release_method && (
                      <p className="text-xs text-green-400">Released via {o.release_method}</p>
                    )}
                  </div>
                  <span className="text-display text-2xl">₹{o.amount}</span>
                </div>

                {tab === 'seller' && o.status === 'disputed' && (
                  <div className="mt-4">
                    <button type="button" onClick={() => handleDisputeResponse(o.id)} className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/5">
                      Submit dispute response
                    </button>
                    {o.seller_message && <p className="mt-2 text-xs text-white/45">Your response: {o.seller_message}</p>}
                  </div>
                )}

                {o.delivery_file && (
                  <a
                    href={o.delivery_file}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-sm text-purple-400 mb-4 hover:underline"
                  >
                    <Download className="w-4 h-4" /> View delivered AMV
                  </a>
                )}

                {o.status !== 'completed' && o.status !== 'cancelled' && o.status !== 'disputed' && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => handleCancel(o.id)} className="rounded-lg border border-red-500/40 px-3 py-2 text-sm text-red-300 hover:bg-red-500/10">
                      Request / approve cancellation
                    </button>
                    <span className="self-center text-xs text-white/35">Paid orders require both sides to agree; Stripe refund is then requested.</span>
                  </div>
                )}

                {tab === 'seller' && o.status === 'in_progress' && o.escrow_status === 'held' && !o.delivery_file && (
                  <div className="flex gap-2 mt-4">
                    <input
                      type="url"
                      placeholder="Delivery video URL (Google Drive, etc.)"
                      value={deliveryUrl[o.id] || ''}
                      onChange={(e) => setDeliveryUrl({ ...deliveryUrl, [o.id]: e.target.value })}
                      className="flex-1 px-3 py-2 rounded-lg bg-black border border-white/10 text-sm"
                    />
                    <button type="button" onClick={() => handleDeliver(o.id)} className="px-4 py-2 rounded-lg bg-purple-600 text-sm font-semibold">
                      Deliver AMV
                    </button>
                  </div>
                )}

                {tab === 'buyer' && o.status === 'in_progress' && o.escrow_status === 'held' && o.delivery_file && !o.buyer_confirmed && (
                  <div className="flex flex-wrap gap-2 mt-4">
                    <button
                      type="button"
                      onClick={() => handleConfirmReceived(o.id)}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-sm font-semibold"
                    >
                      <CheckCircle className="w-4 h-4" /> I received my AMV — release payment
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAiVerify(o.id)}
                      disabled={aiLoading === o.id}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600/80 text-sm font-semibold disabled:opacity-50"
                    >
                      <Bot className="w-4 h-4" />
                      {aiLoading === o.id ? 'AI checking...' : 'AI verify delivery'}
                    </button>
                    <button type="button" onClick={() => handleDispute(o.id)} className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-500/50 text-red-400 text-sm">
                      <AlertTriangle className="w-4 h-4" /> Not received — dispute
                    </button>
                  </div>
                )}

                <OrderChat orderId={o.id} closed={o.status === 'completed' || o.status === 'cancelled'} />

                {tab === 'buyer' && o.delivery_file && !o.buyer_confirmed && o.escrow_status === 'held' && (
                  <p className="text-xs text-white/40 mt-3">
                    If you don&apos;t confirm, AI auto-verifies after 72h and releases only if delivery is valid.
                  </p>
                )}
              </div>
            ))}
            {orders.length === 0 && <p className="text-white/50">No orders yet.</p>}
          </div>
        </div>
      </main>
    </>
  );
}
