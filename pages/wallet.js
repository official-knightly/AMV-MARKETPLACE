import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../lib/store';
import { 
  Wallet as WalletIcon, 
  TrendingUp, 
  DollarSign, 
  ArrowUpRight, 
  ArrowDownRight,
  Loader2,
  CreditCard,
  Building2
} from 'lucide-react';
import toast from 'react-hot-toast';
import api, { startStripeSellerOnboarding, getStripeSellerStatus } from '../lib/api';

export default function Wallet() {
  const router = useRouter();
  const { user, authReady } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [walletData, setWalletData] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState(null);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawMethod, setWithdrawMethod] = useState('upi');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [upiId, setUpiId] = useState('');
  const [bankDetails, setBankDetails] = useState({
    account_number: '',
    ifsc_code: '',
    account_holder: '',
    bank_name: ''
  });
  const [processing, setProcessing] = useState(false);
  const [stripeStatus, setStripeStatus] = useState(null);

  useEffect(() => {
    if (!authReady) return;
    if (!user) {
      router.push('/login');
      return;
    }

    if (!user.is_seller) {
      toast.error('Wallet is only available for sellers');
      router.push('/dashboard');
      return;
    }

    loadWalletData();
  }, [authReady, user]);

  const loadWalletData = async () => {
    try {
      setLoading(true);
      
      // Load wallet balance
      const balanceRes = await api.get('/wallet/balance');
      setWalletData(balanceRes.data);

      // Load transactions
      const transactionsRes = await api.get('/wallet/transactions');
      setTransactions(transactionsRes.data.transactions || []);

      // Load earnings stats
      const statsRes = await api.get('/wallet/earnings-stats');
      setStats(statsRes.data);

      // Load saved payment methods
      const stripeRes = await getStripeSellerStatus().catch(() => null);
      if (stripeRes) setStripeStatus(stripeRes.data);

      const methodsRes = await api.get('/wallet/withdraw-methods');
      if (methodsRes.data.upi_id) {
        setUpiId(methodsRes.data.upi_id);
      }
      if (methodsRes.data.bank_account) {
        setBankDetails(JSON.parse(methodsRes.data.bank_account));
      }

      setLoading(false);
    } catch (error) {
      console.error('Error loading wallet:', error);
      toast.error('Failed to load wallet data');
      setLoading(false);
    }
  };

  const handleStripeOnboarding = async () => {
    try {
      const response = await startStripeSellerOnboarding();
      if (response.data.url) window.location.assign(response.data.url);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not start Stripe verification');
    }
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(withdrawAmount);
    
    if (!amount || amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    if (amount > walletData.available) {
      toast.error('Insufficient balance');
      return;
    }

    if (amount < 100) {
      toast.error('Minimum withdrawal amount is ₹100');
      return;
    }

    if (withdrawMethod === 'upi' && !upiId) {
      toast.error('Please enter your UPI ID');
      return;
    }

    if (withdrawMethod === 'bank_transfer' && (!bankDetails.account_number || !bankDetails.ifsc_code)) {
      toast.error('Please enter complete bank details');
      return;
    }

    try {
      setProcessing(true);

      // Save the selected withdrawal method, then submit the withdrawal request
      await api.post('/wallet/save-payment-method', {
        method: withdrawMethod,
        upi_id: withdrawMethod === 'upi' ? upiId : null,
        bank_details: withdrawMethod === 'bank_transfer' ? JSON.stringify(bankDetails) : null
      });
      await api.post('/withdrawal/request', {
        amount,
        method: withdrawMethod,
        upi_id: withdrawMethod === 'upi' ? upiId : null,
        bank_details: withdrawMethod === 'bank_transfer' ? JSON.stringify(bankDetails) : null
      });
      toast.success('Withdrawal request submitted successfully!');
      setShowWithdrawModal(false);
      setWithdrawAmount('');
      loadWalletData();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Withdrawal failed');
    } finally {
      setProcessing(false);
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Seller Wallet
          </h1>
          <p className="text-gray-400">Manage your earnings and withdrawals</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Stripe seller verification</h2>
            <p className="text-sm text-gray-400 mt-1">
              {stripeStatus?.verified ? "Your Stripe account is verified and payouts are enabled." : "Verify your identity and connect a payout account securely through Stripe."}
            </p>
            {stripeStatus?.connected && !stripeStatus?.verified && (
              <p className="text-xs text-yellow-400 mt-2">Verification or payout setup is still pending.</p>
            )}
          </div>
          <button type="button" onClick={handleStripeOnboarding} className="px-5 py-3 rounded-lg bg-white text-black font-semibold hover:bg-gray-200">
            {stripeStatus?.verified ? "Update Stripe details" : "Verify with Stripe"}
          </button>
        </div>

        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <WalletIcon className="w-8 h-8" />
              <span className="text-sm opacity-80">Available</span>
            </div>
            <p className="text-3xl font-bold">₹{walletData?.available?.toFixed(2) || '0.00'}</p>
            <button
              onClick={() => setShowWithdrawModal(true)}
              className="mt-4 w-full bg-white text-purple-600 py-2 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              Withdraw
            </button>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-8 h-8 text-green-500" />
              <span className="text-sm text-gray-400">Total Earned</span>
            </div>
            <p className="text-3xl font-bold">₹{walletData?.total_earned?.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-gray-400 mt-2">All time earnings</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <DollarSign className="w-8 h-8 text-yellow-500" />
              <span className="text-sm text-gray-400">Pending</span>
            </div>
            <p className="text-3xl font-bold">₹{walletData?.pending?.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-gray-400 mt-2">In escrow</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <ArrowDownRight className="w-8 h-8 text-blue-500" />
              <span className="text-sm text-gray-400">Withdrawn</span>
            </div>
            <p className="text-3xl font-bold">₹{walletData?.withdrawn?.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-gray-400 mt-2">Total withdrawn</p>
          </div>
        </div>

        {/* Earnings Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-gray-400 text-sm mb-2">This Month</h3>
              <p className="text-2xl font-bold text-green-500">₹{stats.this_month?.toFixed(2) || '0.00'}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-gray-400 text-sm mb-2">Last 7 Days</h3>
              <p className="text-2xl font-bold text-blue-500">₹{stats.last_7_days?.toFixed(2) || '0.00'}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-gray-400 text-sm mb-2">Average Order Value</h3>
              <p className="text-2xl font-bold text-purple-500">₹{stats.average_order_value?.toFixed(2) || '0.00'}</p>
            </div>
          </div>
        )}

        {/* Transaction History */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-2xl font-bold mb-6">Transaction History</h2>
          
          {transactions.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <WalletIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>No transactions yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  className="flex items-center justify-between p-4 bg-gray-800 rounded-lg hover:bg-gray-750 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      transaction.type === 'earning' 
                        ? 'bg-green-500/20 text-green-500' 
                        : 'bg-red-500/20 text-red-500'
                    }`}>
                      {transaction.type === 'earning' ? (
                        <ArrowUpRight className="w-5 h-5" />
                      ) : (
                        <ArrowDownRight className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <p className="font-semibold">{transaction.description}</p>
                      <p className="text-sm text-gray-400">
                        {new Date(transaction.created_at).toLocaleDateString('en-IN', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-xl font-bold ${
                      transaction.type === 'earning' ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {transaction.type === 'earning' ? '+' : '-'}₹{transaction.amount.toFixed(2)}
                    </p>
                    {transaction.status && (
                      <p className="text-sm text-gray-400 capitalize">{transaction.status}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-xl max-w-md w-full p-6 border border-gray-800">
            <h2 className="text-2xl font-bold mb-6">Withdraw Funds</h2>
            
            <form onSubmit={handleWithdraw} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Amount</label>
                <input
                  type="number"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  placeholder="Enter amount"
                  min="100"
                  max={walletData?.available}
                  step="0.01"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
                <p className="text-xs text-gray-400 mt-1">
                  Available: ₹{walletData?.available?.toFixed(2)} | Min: ₹100
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Withdrawal Method</label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => setWithdrawMethod('upi')}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      withdrawMethod === 'upi'
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <CreditCard className="w-6 h-6 mx-auto mb-2" />
                    <p className="text-sm font-semibold">UPI</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setWithdrawMethod('bank_transfer')}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      withdrawMethod === 'bank_transfer'
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <Building2 className="w-6 h-6 mx-auto mb-2" />
                    <p className="text-sm font-semibold">Bank</p>
                  </button>
                </div>
              </div>

              {withdrawMethod === 'upi' && (
                <div>
                  <label className="block text-sm font-medium mb-2">UPI ID</label>
                  <input
                    type="text"
                    value={upiId}
                    onChange={(e) => setUpiId(e.target.value)}
                    placeholder="yourname@upi"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>
              )}

              {withdrawMethod === 'bank_transfer' && (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={bankDetails.account_holder}
                    onChange={(e) => setBankDetails({...bankDetails, account_holder: e.target.value})}
                    placeholder="Account Holder Name"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                  <input
                    type="text"
                    value={bankDetails.account_number}
                    onChange={(e) => setBankDetails({...bankDetails, account_number: e.target.value})}
                    placeholder="Account Number"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                  <input
                    type="text"
                    value={bankDetails.ifsc_code}
                    onChange={(e) => setBankDetails({...bankDetails, ifsc_code: e.target.value})}
                    placeholder="IFSC Code"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                  <input
                    type="text"
                    value={bankDetails.bank_name}
                    onChange={(e) => setBankDetails({...bankDetails, bank_name: e.target.value})}
                    placeholder="Bank Name"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowWithdrawModal(false)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 py-2 rounded-lg transition-colors"
                  disabled={processing}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={processing}
                  className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-2 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {processing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Withdraw'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
