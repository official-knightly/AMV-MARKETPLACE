import Head from 'next/head';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

const tools = [
  { href: '/ai-tools/background-remover', title: 'Background Remover', desc: 'Remove background from images & video frames with AI', emoji: '✂️' },
  { href: '/ai-tools/green-screen', title: 'Green Screen', desc: 'Chroma key removal for photos and video', emoji: '🎬' },
  { href: '/ai-tools/plagiarism-detector', title: 'Stolen Edit Detector', desc: 'Scan image or video against marketplace fingerprints', emoji: '🛡️' },
];

export default function AITools() {
  return (
    <>
      <Head><title>AI Tools - VORTEX</title></Head>
      <main className="pt-24 pb-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-display text-5xl mb-4">AI TOOLS</h1>
          <p className="text-white/60 mb-12">Powered by your Flask server (app.py)</p>
          <div className="grid gap-6">
            {tools.map((t) => (
              <Link key={t.href} href={t.href} className="flex items-center gap-6 bg-[#131313] border border-white/10 rounded-2xl p-6 hover:border-white/20 transition group">
                <span className="text-4xl">{t.emoji}</span>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold group-hover:text-purple-400 transition">{t.title}</h2>
                  <p className="text-sm text-white/50">{t.desc}</p>
                </div>
                <ArrowRight className="w-5 h-5 text-white/30 group-hover:text-white" />
              </Link>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
