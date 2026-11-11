import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Search, Filter, Star } from 'lucide-react';
import { getGigs } from '../lib/api';

export default function Marketplace() {
  const [gigs, setGigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => loadGigs(), 250);
    return () => clearTimeout(timer);
  }, [category, searchQuery]);

  const loadGigs = async () => {
    setLoading(true);
    try {
      const params = {
        category: category === 'all' ? undefined : category,
        search: searchQuery.trim() || undefined,
      };
      const res = await getGigs(params);
      setGigs(res.data.gigs || []);
    } catch (error) {
      console.error('Failed to load gigs:', error);
      setGigs([]);
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    { id: 'all', label: 'All' },
    { id: 'amv', label: 'AMV' },
    { id: 'gaming', label: 'Gaming' },
    { id: 'tiktok', label: 'TikTok' },
    { id: 'motion', label: 'Motion Graphics' },
  ];

  return (
    <div className="min-h-screen bg-bg text-white pt-24 pb-20 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-display text-6xl md:text-8xl mb-4">MARKETPLACE</h1>
          <p className="text-white/60 text-lg">Discover talented editors and find the perfect gig</p>
        </div>

        {/* Search & Filters */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              type="text"
              placeholder="Search for edits..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 rounded-xl bg-card border border-white/10 focus:border-white/30 outline-none transition"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategory(cat.id)}
                className={`px-5 py-2 rounded-full text-sm transition ${
                  category === cat.id
                    ? 'bg-white text-black'
                    : 'border border-white/20 hover:bg-white/5'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Gigs Grid */}
        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin w-12 h-12 border-2 border-white/20 border-t-white rounded-full mx-auto mb-4" />
            <p className="text-white/60">Loading gigs...</p>
          </div>
        ) : gigs.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-white/60 text-lg mb-4">No gigs found</p>
            <Link href="/create-gig" className="inline-block px-6 py-3 rounded-lg bg-white text-black font-semibold hover:bg-gray-200 transition">
              Create First Gig
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {gigs.map((gig) => (
              <Link key={gig.id} href={`/gig/${gig.id}`}>
                <div className="bg-card border border-white/10 rounded-2xl overflow-hidden hover:border-white/20 hover:-translate-y-2 transition-all duration-300 cursor-pointer">
                  <div className="h-48 bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
                    <span className="text-display text-6xl text-white/10">
                      {gig.category?.toUpperCase() || 'EDIT'}
                    </span>
                  </div>
                  <div className="p-6">
                    <h3 className="font-semibold text-lg mb-2 line-clamp-2">{gig.title}</h3>
                    <p className="text-sm text-white/50 mb-4">by {gig.seller?.username || 'Unknown'}</p>
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-display text-3xl">₹{gig.price}</div>
                        <div className="text-xs text-white/50 flex items-center gap-1">
                          <Star className="w-3 h-3 fill-yellow-500 text-yellow-500" />
                          {gig.rating || '5.0'} ({gig.total_orders || 0} orders)
                        </div>
                      </div>
                      <button className="px-5 py-2 rounded-lg bg-white text-black text-sm font-semibold hover:scale-105 transition">
                        View
                      </button>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
