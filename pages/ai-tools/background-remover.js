import { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { removeBackground } from '../../lib/api';
import toast from 'react-hot-toast';
import { useDropzone } from 'react-dropzone';
import { Upload, Download, ArrowLeft } from 'lucide-react';

export default function BackgroundRemover() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState('');

  const onDrop = async (files) => {
    const file = files[0];
    if (!file) return;
    setFileName(file.name);
    setLoading(true);
    setResult(null);
    const fd = new FormData();
    const isVideo = file.type.startsWith('video/');
    if (isVideo) {
      fd.append('video', file);
      fd.append('type', 'video');
    } else {
      fd.append('image', file);
    }
    try {
      const res = await removeBackground(fd);
      setResult(res.data.processed_image);
      toast.success(`Done (${res.data.engine})`);
    } catch (e) {
      toast.error(e.response?.data?.error || 'Processing failed — is app.py running?');
    } finally {
      setLoading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'video/*': [] },
    maxFiles: 1,
  });

  return (
    <>
      <Head><title>Background Remover - VORTEX</title></Head>
      <main className="pt-24 pb-16 px-6">
        <div className="max-w-3xl mx-auto">
          <Link href="/ai-tools" className="inline-flex items-center gap-2 text-sm text-white/50 hover:text-white mb-6">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
          <h1 className="text-display text-4xl mb-2">BACKGROUND REMOVER</h1>
          <p className="text-white/60 mb-8">Upload image or video — AI removes background via server</p>

          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition ${
              isDragActive ? 'border-purple-500 bg-purple-500/10' : 'border-white/20 hover:border-white/40'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 mx-auto mb-4 text-white/40" />
            <p>{loading ? 'Processing...' : 'Drop image or video here'}</p>
            {fileName && <p className="text-sm text-white/40 mt-2">{fileName}</p>}
          </div>

          {result && (
            <div className="mt-8">
              <img src={result} alt="Result" className="max-w-full rounded-xl border border-white/10 bg-[#222]" />
              <a href={result} download="vortex-nobg.png" className="inline-flex items-center gap-2 mt-4 px-6 py-3 rounded-lg bg-white text-black font-semibold">
                <Download className="w-4 h-4" /> Download PNG
              </a>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
