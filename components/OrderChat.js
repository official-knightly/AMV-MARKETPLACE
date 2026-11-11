import { useEffect, useState } from 'react';
import { getChatMessages, sendOrderChatMessage } from '../lib/api';
import toast from 'react-hot-toast';

export default function OrderChat({ orderId, closed }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);

  const load = async () => {
    try {
      const res = await getChatMessages(orderId);
      setMessages(res.data.messages || []);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not load order chat');
    }
  };

  useEffect(() => {
    if (orderId) load();
    const timer = setInterval(() => { if (orderId) load(); }, 5000);
    return () => clearInterval(timer);
  }, [orderId]);

  const send = async (event) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || sending) return;
    setSending(true);
    try {
      const res = await sendOrderChatMessage(orderId, { content });
      setMessages((current) => [...current, res.data.message]);
      setDraft('');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Message blocked or failed to send');
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="mt-5 rounded-xl border border-white/10 bg-black/30 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold">Buyer · Seller chat</h4>
        <span className="text-xs text-white/40">Safety Guard active</span>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-3 mb-3 pr-1">
        {messages.map((message) => (
          <div key={message.id} className="rounded-lg bg-white/5 p-3">
            <div className="flex justify-between gap-3 text-xs text-white/45 mb-1">
              <span>{message.sender?.username || 'Participant'}</span>
              <span>{new Date(message.timestamp).toLocaleString()}</span>
            </div>
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          </div>
        ))}
        {messages.length === 0 && <p className="text-sm text-white/40">No messages yet. Keep order details and files in this chat.</p>}
      </div>
      {!closed ? (
        <form onSubmit={send} className="flex gap-2">
          <input value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={3000}
            placeholder="Message the other person..." className="min-w-0 flex-1 rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm" />
          <button disabled={sending || !draft.trim()} className="rounded-lg bg-white text-black px-4 py-2 text-sm font-semibold disabled:opacity-50">
            {sending ? 'Sending…' : 'Send'}
          </button>
        </form>
      ) : <p className="text-xs text-white/40">This order is closed; chat is read-only.</p>}
      <p className="text-xs text-white/35 mt-2">Automated safety checks messages for scams, harassment, suspicious links and attempts to move payments off-platform. Never share passwords or payment details.</p>
    </section>
  );
}
