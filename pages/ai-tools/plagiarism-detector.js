import { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { detectPlagiarism } from '../../lib/api';
import toast from 'react-hot-toast';
import { useDropzone } from 'react-dropzone';
import { Shield, AlertTriangle, CheckCircle, ArrowLeft } from 'lucide-react';

export default function PlagiarismDetector() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const onDrop = async (files) => {
    const file = files[0];
    if (!file) return;
    setLoading(true);
    setReport(null);
    const fd = new FormData();
    fd.append(file.type.startsWith('video/') ? 'video' : 'image', file);
    try {
      const res = await detectPlagiarism(fd);
      setReport(res.data);
    } catch (e) {
      toast.error(e.response?.data?.error || 'Scan failed');
    } finally {
      setLoading(false);
    }
  };

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'video/*': [] },
    maxFiles: 1,
  });

  return (
    <>
      <Head><title>Stolen Edit Detector - VORTEX</title></Head>
      <main className="pt-24 pb-16 px-6">
        <div className="max-w-2xl mx-auto">
          <Link href="/ai-tools" className="inline-flex items-center gap-2 text-sm text-white/50 hover:text-white mb-6">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
          <h1 className="text-display text-4xl mb-2">STOLEN EDIT DETECTOR</h1>
          <p className="text-white/60 mb-8">AI fingerprint scan against marketplace archive (image + video)</p>

          <div {...getRootProps()} className="border-2 border-dashed border-white/20 rounded-2xl p-12 text-center cursor-pointer hover:border-purple-500/50">
            <input {...getInputProps()} />
            <Shield className="w-12 h-12 mx-auto mb-4 text-purple-400" />
            <p>{loading ? 'Scanning frames...' : 'Drop image or video to scan'}</p>
          </div>

          {report && (
            <div className={`mt-8 rounded-2xl p-6 border ${report.is_plagiarized ? 'border-red-500/50 bg-red-500/10' : 'border-green-500/50 bg-green-500/10'}`}>
              {report.is_plagiarized ? (
                <>
                  <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
                  <h2 className="text-xl font-bold text-red-400">Possible stolen edit</h2>
                  <p className="text-sm text-white/60 mt-2">
                    Confidence: {(report.confidence * 100).toFixed(0)}% · {report.media_type}
                  </p>
                  {report.original_gig && (
                    <p className="mt-4 text-sm">
                      Matches: <strong>{report.original_gig.title}</strong> by {report.original_gig.seller}
                    </p>
                  )}
                </>
              ) : (
                <>
                  <CheckCircle className="w-10 h-10 text-green-400 mb-3" />
                  <h2 className="text-xl font-bold text-green-400">No match found</h2>
                  <p className="text-sm text-white/60 mt-2">Content appears original in our archive.</p>
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
