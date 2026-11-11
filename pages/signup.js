import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { googleAuth, register } from '../lib/api';
import { useAuthStore } from '../lib/store';
import GoogleAuthButton from '../components/GoogleAuthButton';
import toast from 'react-hot-toast';

export default function Signup() {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignup = async (e) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const res = await register({
        email: formData.email,
        username: formData.username,
        full_name: formData.full_name,
        password: formData.password,
      });
      setAuth(res.data.user, res.data.token);
      toast.success('Account created successfully!');
      router.push('/select-role');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignup = async (credentialResponse) => {
    try {
      const token = credentialResponse?.credential;
      if (!token) {
        toast.error('Google signup did not return a token');
        return;
      }
      const res = await googleAuth(token);
      setAuth(res.data.user, res.data.token);
      toast.success('Signed in with Google');
      router.push(res.data.user.account_type ? '/dashboard' : '/select-role');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Google signup failed');
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-6 pt-20 pb-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-display text-5xl mb-3">SIGN UP</h1>
          <p className="text-white/60">Join the creator revolution</p>
        </div>

        <div className="bg-card border border-white/10 rounded-2xl p-8">
          <form onSubmit={handleSignup} className="space-y-4">
            <div>
              <label className="block text-sm text-white/60 mb-2">Full Name</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 focus:border-white/30 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">Username</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 focus:border-white/30 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 focus:border-white/30 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 focus:border-white/30 outline-none transition"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-white/60 mb-2">Confirm Password</label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="w-full px-4 py-3 rounded-lg bg-surface border border-white/10 focus:border-white/30 outline-none transition"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg bg-white text-black font-semibold hover:bg-gray-200 transition disabled:opacity-50"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-xs text-white/30">
            <div className="h-px flex-1 bg-white/10" />
            <span>OR</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <GoogleAuthButton mode="signup" onSuccess={handleGoogleSignup} />

          <p className="text-center text-sm text-white/60 mt-6">
            Already have an account?{' '}
            <Link href="/login" className="text-white hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
