import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowRight, Shield, Zap, TrendingUp, Star } from 'lucide-react';
import { getGigs, getMarketplaceStats } from '../lib/api';

export default function Home() {
  const [featuredGigs, setFeaturedGigs] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getGigs({ per_page: 6 })
      .then(res => setFeaturedGigs(res.data.gigs || []))
      .catch(console.error);
    getMarketplaceStats()
      .then(res => setStats(res.data))
      .catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-bg text-white">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-black to-black" />
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px)',
          backgroundSize: '72px 72px',
          maskImage: 'radial-gradient(ellipse 90% 70% at 50% 0%, black, transparent)'
        }} />
        
        <div className="relative z-10 max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full border border-white/20 bg-white/5 text-xs uppercase tracking-wider mb-8">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            AI-Powered Edit Marketplace
          </div>
          
          <h1 className="text-display text-6xl md:text-8xl lg:text-9xl leading-none mb-6">
            THE EDIT<br />
            <span className="text-transparent" style={{ WebkitTextStroke: '1.5px rgba(255,255,255,0.3)' }}>
              MARKETPLACE
            </span><br />
            FOR CREATORS
          </h1>
          
          <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10">
            Buy & sell AMVs, anime edits, montages, and motion graphics. Real AI tools built in. Zero scams.
          </p>
          
          <div className="flex flex-wrap gap-4 justify-center">
            <Link href="/marketplace" className="flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-black font-semibold text-lg hover:scale-105 transition">
              Explore Editors <ArrowRight className="w-5 h-5" />
            </Link>
            <Link href="/ai-tools" className="px-8 py-4 rounded-xl border border-white/20 text-lg hover:bg-white/5 transition">
              Try AI Tools
            </Link>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-12 mt-20 pt-12 border-t border-white/10">
            <div>
              <div className="text-display text-5xl mb-1">{stats ? stats.active_sellers.toLocaleString() : "—"}</div>
              <div className="text-xs text-white/50 uppercase tracking-wider">Active Editors</div>
            </div>
            <div>
              <div className="text-display text-5xl mb-1">{stats ? stats.active_listings.toLocaleString() : "—"}</div>
              <div className="text-xs text-white/50 uppercase tracking-wider">Active Listings</div>
            </div>
            <div>
              <div className="text-display text-5xl mb-1">{stats ? `${Math.round(stats.platform_fee_rate * 100)}%` : "—"}</div>
              <div className="text-xs text-white/50 uppercase tracking-wider">Platform Fee</div>
            </div>
          </div>
        </div>
      </section>

      {/* Ticker */}
      <div className="border-y border-white/10 bg-surface py-4 overflow-hidden">
        <div className="flex gap-12 animate-scroll whitespace-nowrap">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="flex gap-12">
              <span className="text-xs text-white/50 uppercase tracking-widest">AMV Edits ✦</span>
              <span className="text-xs text-white/50 uppercase tracking-widest">JJK Edits ✦</span>
              <span className="text-xs text-white/50 uppercase tracking-widest">Gaming Montages ✦</span>
              <span className="text-xs text-white/50 uppercase tracking-widest">TikTok Reels ✦</span>
              <span className="text-xs text-white/50 uppercase tracking-widest">Motion Graphics ✦</span>
            </div>
          ))}
        </div>
      </div>

      {/* Featured Gigs */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-end mb-12">
            <div>
              <div className="text-xs text-white/50 uppercase tracking-widest mb-3">Marketplace</div>
              <h2 className="text-display text-5xl md:text-7xl">TOP GIGS</h2>
            </div>
            <Link href="/marketplace" className="text-sm text-white/60 hover:text-white transition">
              View All →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {featuredGigs.map((gig) => (
              <Link key={gig.id} href={`/gig/${gig.id}`}>
                <div className="bg-card border border-white/10 rounded-2xl overflow-hidden hover:border-white/20 hover:-translate-y-2 transition-all duration-300 cursor-pointer">
                  <div className="h-48 bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                    <span className="text-display text-6xl text-white/10">{gig.category.toUpperCase()}</span>
                  </div>
                  <div className="p-6">
                    <h3 className="font-semibold text-lg mb-2">{gig.title}</h3>
                    <p className="text-sm text-white/50 mb-4">by {gig.seller.username}</p>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-display text-3xl">₹{gig.price}</div>
                        <div className="text-xs text-white/50 flex items-center gap-1">
                          <Star className="w-3 h-3 fill-yellow-500 text-yellow-500" />
                          {gig.rating} rating
                        </div>
                      </div>
                      <button className="px-5 py-2 rounded-lg bg-white text-black text-sm font-semibold hover:scale-105 transition">
                        Order
                      </button>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-surface">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="text-xs text-white/50 uppercase tracking-widest mb-3">Protection</div>
            <h2 className="text-display text-5xl md:text-7xl mb-4">ZERO SCAM POLICY</h2>
            <p className="text-white/60 max-w-xl mx-auto">
              Buyer confirms the AMV first, or AI (Claude, Codex, Cursor) verifies delivery. Fake AMVs removed automatically.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { icon: Shield, title: 'Escrow Payments', desc: 'Funds held until buyer confirms delivery. No exceptions.' },
              { icon: Zap, title: 'Stolen Edit Detection', desc: 'AI fingerprint matching flags plagiarized work before listing.' },
              { icon: TrendingUp, title: 'Quality Gate', desc: 'Auto export analysis blocks low-quality deliverables.' },
              { icon: Star, title: 'AI Trust Score', desc: 'Editors scored on history, delivery rate and reviews.' },
            ].map((feature, i) => (
              <div key={i} className="bg-card border border-white/10 rounded-xl p-6 flex gap-4">
                <div className="w-12 h-12 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-white/60">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 bg-white text-black text-center">
        <h2 className="text-display text-6xl md:text-8xl mb-6">
          BUILD YOUR<br />CREATOR EMPIRE
        </h2>
        <p className="text-black/60 text-lg max-w-xl mx-auto mb-10">
          The most loyal audience in creative media is waiting. Focus on the craft. Vortex handles everything else.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <Link href="/signup" className="px-8 py-4 rounded-xl bg-black text-white font-semibold text-lg hover:scale-105 transition">
            Start Selling Free →
          </Link>
          <Link href="/pricing" className="px-8 py-4 rounded-xl border border-black/20 text-lg hover:bg-black/5 transition">
            View Pricing
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface border-t border-white/10 py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="text-display text-2xl mb-4">VORTEX</div>
              <p className="text-sm text-white/50">The AI marketplace for video editors.</p>
            </div>
            <div>
              <h4 className="text-xs uppercase tracking-wider text-white/50 mb-4">Platform</h4>
              <div className="space-y-2">
                <Link href="/marketplace" className="block text-sm text-white/60 hover:text-white">Marketplace</Link>
                <Link href="/ai-tools" className="block text-sm text-white/60 hover:text-white">AI Tools</Link>
                <Link href="/pricing" className="block text-sm text-white/60 hover:text-white">Pricing</Link>
              </div>
            </div>
            <div>
              <h4 className="text-xs uppercase tracking-wider text-white/50 mb-4">Editors</h4>
              <div className="space-y-2">
                <Link href="/signup" className="block text-sm text-white/60 hover:text-white">Start Selling</Link>
                <Link href="/dashboard" className="block text-sm text-white/60 hover:text-white">Dashboard</Link>
                <Link href="/wallet" className="block text-sm text-white/60 hover:text-white">Payouts</Link>
              </div>
            </div>
            <div>
              <h4 className="text-xs uppercase tracking-wider text-white/50 mb-4">Company</h4>
              <div className="space-y-2">
                <Link href="/about" className="block text-sm text-white/60 hover:text-white">About</Link>
                <Link href="/contact" className="block text-sm text-white/60 hover:text-white">Contact</Link>
                <a href={process.env.NEXT_PUBLIC_DONATE_UPI} target="_blank" rel="noopener noreferrer" className="block text-sm text-white/60 hover:text-white">Donate</a>
              </div>
            </div>
          </div>
          <div className="pt-8 border-t border-white/10 flex flex-wrap justify-between items-center gap-4 text-sm text-white/30">
            <p>VORTEX © 2026 — All rights reserved.</p>
            <p>Privacy · Terms · Cookies</p>
          </div>
        </div>
      </footer>

      <style jsx>{`
        @keyframes scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-scroll {
          animation: scroll 30s linear infinite;
        }
      `}</style>
    </div>
  );
}
