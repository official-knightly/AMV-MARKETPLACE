import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../lib/store';
import {
  getAdminOverview, getAdminDisputes, getAdminCopyrightReports,
  resolveAdminDispute, updateAdminCopyrightReport,
} from '../lib/api';
import toast from 'react-hot-toast';
import { RefreshCw, ShieldCheck, FileWarning, Scale } from 'lucide-react';

export default function AdminDashboard() {
  const router = useRouter();
  const { user, authReady, isAuthenticated } = useAuthStore();
  const [overview, setOverview] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [summary, disputeList, reportList] = await Promise.all([
        getAdminOverview(), getAdminDisputes(), getAdminCopyrightReports(),
      ]);
      setOverview(summary.data);
      setDisputes(disputeList.data.disputes || []);
      setReports(reportList.data.reports || []);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not load admin data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authReady) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    if (user && !user.is_admin) {
      router.replace('/dashboard');
      return;
    }
    if (user?.is_admin) load();
  }, [authReady, isAuthenticated, user, router]);

  const resolve = async (orderId, decision) => {
    const label = decision === 'refund' ? 'refund the buyer' : 'release payment to the seller';
    if (!window.confirm(`Are you sure you want to ${label} for order #${orderId}?`)) return;
    const note = window.prompt('Admin resolution note (optional):') || '';
    setBusy(`dispute-${orderId}`);
    try {
      await resolveAdminDispute(orderId, { decision, note });
      toast.success('Dispute resolved');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not resolve dispute');
    } finally {
      setBusy('');
    }
  };

  const updateReport = async (reportId, status) => {
    const admin_notes = window.prompt('Add an admin note (optional):') || '';
    setBusy(`report-${reportId}`);
    try {
      await updateAdminCopyrightReport(reportId, { status, admin_notes });
      toast.success('Copyright report updated');
      await load();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Could not update report');
    } finally {
      setBusy('');
    }
  };

  if (!authReady || !isAuthenticated || !user?.is_admin) {
    return <main className="min-h-screen bg-bg pt-28 px-6 text-center text-white/50">Checking admin access…</main>;
  }

  const counts = overview?.counts || {};
  return (
    <main className="min-h-screen bg-bg text-white pt-24 pb-16 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-10">
          <div>
            <p className="text-xs uppercase tracking-widest text-white/40 mb-2">VORTEX administration</p>
            <h1 className="text-display text-5xl md:text-7xl">ADMIN DASHBOARD</h1>
            <p className="text-sm text-white/50 mt-2">Signed in as {user.username}. Review disputes and copyright reports.</p>
          </div>
          <button type="button" onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm hover:bg-white/5 disabled:opacity-50">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        <section className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-10">
          {[
            ['Users', counts.users], ['Active listings', counts.active_gigs],
            ['Orders', counts.orders], ['Open disputes', counts.disputes],
            ['Copyright queue', counts.copyright_reports],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-white/10 bg-card p-5">
              <p className="text-xs text-white/45">{label}</p>
              <p className="text-3xl font-semibold mt-2">{value ?? '—'}</p>
            </div>
          ))}
        </section>

        <section className="mb-12">
          <div className="flex items-center gap-2 mb-4">
            <Scale size={18} />
            <h2 className="text-xl font-semibold">Disputes</h2>
            <span className="text-xs text-white/40">Funds remain held until a decision</span>
          </div>
          {loading ? <p className="text-white/45 py-6">Loading disputes…</p> : disputes.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-card p-6 text-sm text-white/45">No open disputes.</div>
          ) : (
            <div className="space-y-3">
              {disputes.map((item) => (
                <article key={item.order_id} className="rounded-xl border border-white/10 bg-card p-5">
                  <div className="flex flex-wrap justify-between gap-3">
                    <div>
                      <h3 className="font-semibold">Order #{item.order_id} · {item.gig_title}</h3>
                      <p className="text-sm text-white/45 mt-1">Buyer: {item.buyer} · Seller: {item.seller} · ₹{item.amount}</p>
                    </div>
                    <span className="text-xs text-white/45">Escrow: {item.escrow_status}</span>
                  </div>
                  <div className="grid md:grid-cols-2 gap-4 mt-4 text-sm">
                    <div><p className="text-white/40 mb-1">Buyer claim</p><p className="whitespace-pre-wrap">{item.buyer_claim || 'No claim provided'}</p></div>
                    <div><p className="text-white/40 mb-1">Seller response</p><p className="whitespace-pre-wrap">{item.seller_response || 'Awaiting seller response'}</p></div>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-5">
                    <button type="button" disabled={busy === `dispute-${item.order_id}`} onClick={() => resolve(item.order_id, 'refund')} className="rounded-lg border border-white/20 px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-40">Refund buyer</button>
                    <button type="button" disabled={busy === `dispute-${item.order_id}`} onClick={() => resolve(item.order_id, 'release')} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-black disabled:opacity-40">Release to seller</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4">
            <FileWarning size={18} />
            <h2 className="text-xl font-semibold">Copyright reports</h2>
          </div>
          {loading ? <p className="text-white/45 py-6">Loading reports…</p> : reports.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-card p-6 text-sm text-white/45">No copyright reports.</div>
          ) : (
            <div className="space-y-3">
              {reports.map((report) => (
                <article key={report.id} className="rounded-xl border border-white/10 bg-card p-5">
                  <div className="flex flex-wrap justify-between gap-3">
                    <div>
                      <h3 className="font-semibold">Report #{report.id} · {report.gig_title}</h3>
                      <p className="text-sm text-white/45 mt-1">{report.claimant_name} · {report.contact_email}</p>
                    </div>
                    <span className="text-xs text-white/45">{report.status}</span>
                  </div>
                  <p className="text-sm whitespace-pre-wrap mt-4">{report.description}</p>
                  {report.evidence_url && <a href={report.evidence_url} target="_blank" rel="noreferrer" className="inline-block text-sm underline text-white/65 mt-3">Open evidence</a>}
                  {report.admin_notes && <p className="text-xs text-white/40 mt-3">Admin note: {report.admin_notes}</p>}
                  <div className="flex flex-wrap gap-2 mt-5">
                    <button type="button" disabled={busy === `report-${report.id}`} onClick={() => updateReport(report.id, 'under_review')} className="rounded-lg border border-white/20 px-3 py-2 text-xs hover:bg-white/5">Under review</button>
                    <button type="button" disabled={busy === `report-${report.id}`} onClick={() => updateReport(report.id, 'action_required')} className="rounded-lg border border-white/20 px-3 py-2 text-xs hover:bg-white/5">Request evidence</button>
                    <button type="button" disabled={busy === `report-${report.id}`} onClick={() => updateReport(report.id, 'removed')} className="rounded-lg border border-white/20 px-3 py-2 text-xs hover:bg-white/5">Remove listing</button>
                    <button type="button" disabled={busy === `report-${report.id}`} onClick={() => updateReport(report.id, 'rejected')} className="rounded-lg border border-white/20 px-3 py-2 text-xs hover:bg-white/5">Reject report</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
        <p className="text-xs text-white/30 mt-10 flex items-center gap-2"><ShieldCheck size={14} /> Admin actions are protected by the backend email allowlist.</p>
      </div>
    </main>
  );
}
