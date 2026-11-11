import { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { greenScreen } from '../../lib/api';
import toast from 'react-hot-toast';
import { useDropzone } from 'react-dropzone';
import { Upload, Download, ArrowLeft } from 'lucide-react';

export default function GreenScreenTool() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tolerance, setTolerance] = useState(40);
  const [feather, setFeather] = useState(3);

  const onDrop = async (files) => {
    const file = files[0];
    if (!file) return;
    setLoading(true);
    const fd = new FormData();
    fd.append(file.type.startsWith('video/') ? 'video' : 'image', file);
    fd.append('tolerance', tolerance);
    fd.append('feather', feather);
    try {
      const res = await greenScreen(fd);
      setResult(res.data.processed_image);
      toast.success('Green screen removed');
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed — start app.py');
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
      <Head><title>Green Screen - VORTEX</title></Head>
      <main className="pt-24 pb-16 px-6">
        <div className="max-w-3xl mx-auto">
          <Link href="/ai-tools" className="inline-flex items-center gap-2 text-sm text-white/50 hover:text-white mb-6">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
          <h1 className="text-display text-4xl mb-8">GREEN SCREEN</h1>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <label className="text-xs text-white/50">Tolerance</label>
              <input type="range" min="10" max="80" value={tolerance} onChange={(e) => setTolerance(+e.target.value)} className="w-full" />
            </div>
            <div>
              <label className="text-xs text-white/50">Feather</label>
              <input type="range" min="0" max="10" value={feather} onChange={(e) => setFeather(+e.target.value)} className="w-full" />
            </div>
          </div>

          <div {...getRootProps()} className="border-2 border-dashed border-white/20 rounded-2xl p-12 text-center cursor-pointer hover:border-green-500/50">
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 mx-auto mb-4 text-green-400/60" />
            <p>{loading ? 'Processing...' : 'Upload green screen image or video'}</p>
          </div>

          {result && (
            <div className="mt-8">
              <img src={result} alt="" className="max-w-full rounded-xl" />
              <a href={result} download="vortex-greenscreen.png" className="inline-flex items-center gap-2 mt-4 px-6 py-3 rounded-lg bg-white text-black font-semibold">
                <Download className="w-4 h-4" /> Download
              </a>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
