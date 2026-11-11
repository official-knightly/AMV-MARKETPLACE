import { useState } from 'react';
import Link from 'next/link';
import { MessageCircle, X, Send, Sparkles, Loader2 } from 'lucide-react';
import { askMarketplaceAssistant } from '../lib/api';

export default function MarketplaceAssistant() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', text: "Hey! I can help you find an AMV editor. Tell me the anime or game, editing style, your budget in ₹, and when you need it." }
  ]);

  const send = async (event) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy) return;
    setMessages((items) => [...items, { role: 'user', text: message }]);
    setDraft('');
    setBusy(true);
    try {
      const response = await askMarketplaceAssistant(message);
      setMessages((items) => [...items, {
        role: 'assistant',
        text: response.data.reply || 'Tell me a little more about the edit you need.',
        gigs: response.data.gigs || []
      }]);
    } catch (error) {
      setMessages((items) => [...items, {
        role: 'assistant',
        text: error.response?.data?.error || 'The assistant is temporarily unavailable. You can still browse the marketplace.'
      }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-[90]">
      {open && (
        <section className="mb-3 flex h-[min(620px,75vh)] w-[min(380px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-white/15 bg-[#101010] shadow-2xl">
          <header className="flex items-center justify-between border-b border-white/10 bg-[#17131f] p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/20 text-purple-300"><Sparkles size={18} /></span>
              <div><h3 className="text-sm font-semibold text-white">Marketplace AI</h3><p className="text-xs text-white/45">Find your next editor</p></div>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close assistant" className="rounded-lg p-2 text-white/60 hover:bg-white/10"><X size={18} /></button>
          </header>
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((item, index) => (
              <div key={index} className={item.role === 'user' ? 'ml-8 rounded-2xl rounded-br-sm bg-purple-600 p-3 text-sm text-white' : 'mr-4 rounded-2xl rounded-bl-sm bg-white/7 p-3 text-sm text-white/85'}>
                <p className="whitespace-pre-wrap leading-relaxed">{item.text}</p>
                {item.gigs?.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {item.gigs.map((gig) => (
                      <Link key={gig.id} href={`/gig/${gig.id}`} onClick={() => setOpen(false)} className="block rounded-xl border border-white/10 bg-black/30 p-3 hover:border-purple-400/50">
                        <div className="font-medium text-white">{gig.title}</div>
                        <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-white/50">
                          <span>₹{gig.price_inr}</span><span>{gig.delivery_days} day delivery</span><span>{gig.seller}</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="flex items-center gap-2 text-xs text-white/45"><Loader2 size={14} className="animate-spin" /> Finding suitable listings…</div>}
          </div>
          <form onSubmit={send} className="flex gap-2 border-t border-white/10 p-3">
            <input value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={1200} placeholder="Describe the edit you need…" className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-sm text-white outline-none placeholder:text-white/35 focus:border-purple-400/60" />
            <button type="submit" disabled={busy || !draft.trim()} aria-label="Send message" className="rounded-xl bg-purple-600 px-3 text-white disabled:opacity-40"><Send size={17} /></button>
          </form>
          <p className="px-3 pb-2 text-[10px] text-white/30">AI suggestions are based on live listings. Check details before ordering.</p>
        </section>
      )}
      <button type="button" onClick={() => setOpen((value) => !value)} aria-label={open ? 'Close marketplace AI' : 'Open marketplace AI'} className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-purple-600 text-white shadow-xl shadow-purple-950/40 transition hover:scale-105">
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </div>
  );
}
