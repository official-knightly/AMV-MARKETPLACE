import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { ShoppingBag, Briefcase, ArrowRight } from 'lucide-react';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import toast from 'react-hot-toast';

export default function SelectRole() {
  const router = useRouter();
  const { user, updateUser, authReady } = useAuthStore();
  const [selectedRole, setSelectedRole] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (authReady && !user) router.replace('/login');
  }, [authReady, user, router]);

  const handleRoleSelection = async () => {
    if (!authReady || !user) return;
    if (!selectedRole) {
      toast.error('Please select a role');
      return;
    }

    setLoading(true);

    try {
      const res = await api.post('/user/set-role', {
        role: selectedRole
      });

      updateUser({ account_type: selectedRole, is_seller: selectedRole === 'seller' });
      toast.success(`Welcome as a ${selectedRole}!`);
      
      if (selectedRole === 'seller') {
        router.push('/dashboard?tab=seller');
      } else {
        router.push('/marketplace');
      }
    } catch (error) {
      toast.error('Failed to set role');
    } finally {
      setLoading(false);
    }
  };

  const roles = [
    {
      id: 'buyer',
      title: 'I want to Buy',
      subtitle: 'Find talented editors',
      icon: ShoppingBag,
      features: [
        'Browse thousands of gigs',
        'Secure escrow payments',
        'AI-powered recommendations',
        'Quality guaranteed',
        'Fast delivery',
      ],
      gradient: 'from-purple-600 to-blue-600',
    },
    {
      id: 'seller',
      title: 'I want to Sell',
      subtitle: 'Offer your editing services',
      icon: Briefcase,
      features: [
        'Create unlimited gigs',
        'Set your own prices',
        'AI-optimized listings',
        'Instant payouts to UPI',
        'Build your reputation',
      ],
      gradient: 'from-green-600 to-teal-600',
    },
  ];

  if (!authReady || !user) return null;

  return (
    <div className="min-h-screen bg-bg text-white flex items-center justify-center px-6 py-20">
      <div className="max-w-6xl w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-display text-5xl md:text-7xl mb-4">CHOOSE YOUR PATH</h1>
          <p className="text-white/60 text-lg">
            Select how you want to use Vortex. You can switch anytime!
          </p>
        </div>

        {/* Role Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          {roles.map((role) => {
            const Icon = role.icon;
            const isSelected = selectedRole === role.id;

            return (
              <div
                key={role.id}
                onClick={() => setSelectedRole(role.id)}
                className={`relative bg-card border-2 rounded-3xl p-8 cursor-pointer transition-all duration-300 ${
                  isSelected
                    ? 'border-white scale-105 shadow-2xl'
                    : 'border-white/10 hover:border-white/30 hover:scale-102'
                }`}
              >
                {/* Selected Badge */}
                {isSelected && (
                  <div className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white flex items-center justify-center">
                    <svg className="w-5 h-5 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}

                {/* Icon */}
                <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${role.gradient} flex items-center justify-center mb-6`}>
                  <Icon className="w-10 h-10" />
                </div>

                {/* Title */}
                <h2 className="text-3xl font-bold mb-2">{role.title}</h2>
                <p className="text-white/60 mb-6">{role.subtitle}</p>

                {/* Features */}
                <ul className="space-y-3">
                  {role.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <span className="text-sm text-white/80">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        {/* Continue Button */}
        <div className="text-center">
          <button
            onClick={handleRoleSelection}
            disabled={!selectedRole || loading}
            className="inline-flex items-center gap-3 px-10 py-4 rounded-xl bg-white text-black font-bold text-lg hover:scale-105 transition disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {loading ? (
              <>
                <div className="animate-spin w-5 h-5 border-2 border-black/20 border-t-black rounded-full" />
                Setting up...
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          <p className="text-sm text-white/50 mt-4">
            Don't worry! You can switch between buyer and seller anytime from your dashboard.
          </p>
        </div>
      </div>
    </div>
  );
}
