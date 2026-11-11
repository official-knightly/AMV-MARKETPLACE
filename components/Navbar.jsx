import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Menu, X, Search, User, LogOut, Wallet, Heart } from 'lucide-react';
import { useAuthStore } from '../lib/store';
import { useRouter } from 'next/router';

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center justify-between px-6 md:px-10 bg-black/95 backdrop-blur-xl border-b border-white/10">
      <Link href="/" className="text-display text-2xl md:text-3xl tracking-widest">
        VORTEX
      </Link>

      {/* Desktop Navigation */}
      <div className="hidden md:flex items-center gap-8">
        <Link href="/marketplace" className="text-sm text-white/60 hover:text-white transition">
          Marketplace
        </Link>
        <Link href="/ai-tools" className="text-sm text-white/60 hover:text-white transition">
          AI Tools
        </Link>
        {user?.is_admin && (
          <Link href="/admin" className="text-sm text-white/60 hover:text-white transition">Admin</Link>
        )}
        <Link href="/how-it-works" className="text-sm text-white/60 hover:text-white transition">
          How It Works
        </Link>
        <a 
          href={process.env.NEXT_PUBLIC_DONATE_UPI} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-pink-500 to-purple-600 text-white text-sm font-semibold hover:scale-105 transition"
        >
          <Heart className="w-4 h-4" />
          Donate
        </a>
      </div>

      {/* Auth Buttons */}
      <div className="hidden md:flex items-center gap-3">
        {isAuthenticated ? (
          <>
            <Link href="/dashboard" className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/20 hover:bg-white/5 transition">
              <User className="w-4 h-4" />
              <span className="text-sm">{user?.username}</span>
            </Link>
            <Link href="/wallet" className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/20 hover:bg-white/5 transition">
              <Wallet className="w-4 h-4" />
              <span className="text-sm">₹{user?.balance?.toFixed(2) || '0.00'}</span>
            </Link>
            <button onClick={handleLogout} className="p-2 rounded-lg hover:bg-white/5 transition">
              <LogOut className="w-4 h-4" />
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="px-4 py-2 rounded-lg border border-white/20 text-sm hover:bg-white/5 transition">
              Login
            </Link>
            <Link href="/signup" className="px-4 py-2 rounded-lg bg-white text-black text-sm font-semibold hover:bg-gray-200 transition">
              Sign Up
            </Link>
          </>
        )}
      </div>

      {/* Mobile Menu Button */}
      <button 
        onClick={() => setMenuOpen(!menuOpen)}
        className="md:hidden p-2 rounded-lg hover:bg-white/5 transition"
      >
        {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="absolute top-16 left-0 right-0 bg-black/98 backdrop-blur-xl border-b border-white/10 p-6 md:hidden">
          <div className="flex flex-col gap-4">
            <Link href="/marketplace" className="text-white/80 hover:text-white transition">
              Marketplace
            </Link>
            <Link href="/ai-tools" className="text-white/80 hover:text-white transition">
              AI Tools
            </Link>
            {user?.is_admin && <Link href="/admin" className="text-white/80 hover:text-white transition">Admin</Link>}
            <Link href="/how-it-works" className="text-white/80 hover:text-white transition">
              How It Works
            </Link>
            <a 
              href={process.env.NEXT_PUBLIC_DONATE_UPI} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-pink-500 to-purple-600 text-white font-semibold justify-center"
            >
              <Heart className="w-4 h-4" />
              Donate
            </a>
            
            {isAuthenticated ? (
              <>
                <Link href="/dashboard" className="px-4 py-2 rounded-lg border border-white/20 text-center">
                  Dashboard
                </Link>
                <Link href="/wallet" className="px-4 py-2 rounded-lg border border-white/20 text-center">
                  Wallet: ₹{user?.balance?.toFixed(2) || '0.00'}
                </Link>
                <button onClick={handleLogout} className="px-4 py-2 rounded-lg bg-red-600 text-white">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="px-4 py-2 rounded-lg border border-white/20 text-center">
                  Login
                </Link>
                <Link href="/signup" className="px-4 py-2 rounded-lg bg-white text-black font-semibold text-center">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
