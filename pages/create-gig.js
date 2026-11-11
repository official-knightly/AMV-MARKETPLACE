import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '../lib/store';
import { Upload, Video, Image as ImageIcon, Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../lib/api';

export default function CreateGig() {
  const router = useRouter();
  const { user, authReady } = useAuthStore();
  const [step, setStep] = useState(1); // 1: Upload, 2: Details, 3: AI Check, 4: Publish
  
  // Step 1: Video Upload
  const [videoFile, setVideoFile] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);
  const [thumbnailFile, setThumbnailFile] = useState(null);
  const [thumbnailPreview, setThumbnailPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const videoInputRef = useRef(null);
  const thumbnailInputRef = useRef(null);
  
  // Step 2: Gig Details
  const [form, setForm] = useState({
    title: '',
    description: '',
    category: 'amv',
    price: '',
    delivery_days: '3',
    tags: '',
  });
  
  // Step 3: AI Analysis
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  
  // Step 4: Publishing
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (authReady && !user) router.replace('/login');
  }, [authReady, user, router]);

  if (!authReady || !user) return null;

  const handleVideoSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Check file type
    if (!file.type.startsWith('video/')) {
      toast.error('Please select a video file');
      return;
    }
    
    // Check file size (max 100MB)
    if (file.size > 100 * 1024 * 1024) {
      toast.error('Video file must be less than 100MB');
      return;
    }
    
    setVideoFile(file);
    setVideoPreview(URL.createObjectURL(file));
    toast.success('Video selected! Now add a thumbnail.');
  };

  const handleThumbnailSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Check file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }
    
    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Thumbnail must be less than 5MB');
      return;
    }
    
    setThumbnailFile(file);
    setThumbnailPreview(URL.createObjectURL(file));
    toast.success('Thumbnail selected!');
  };

  const uploadFiles = async () => {
    if (!videoFile || !thumbnailFile) {
      toast.error('Please select both video and thumbnail');
      return;
    }
    
    setUploading(true);
    try {
      // Upload video
      const videoFormData = new FormData();
      videoFormData.append('video', videoFile);
      
      const videoRes = await api.post('/upload/video', videoFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 minutes
      });
      
      // Upload thumbnail
      const thumbnailFormData = new FormData();
      thumbnailFormData.append('image', thumbnailFile);
      
      const thumbnailRes = await api.post('/upload/image', thumbnailFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      setForm({
        ...form,
        video_url: videoRes.data.url,
        thumbnail: thumbnailRes.data.url,
      });
      
      toast.success('Files uploaded successfully!');
      setStep(2);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDetailsSubmit = (e) => {
    e.preventDefault();
    
    if (!form.title || !form.description || !form.price) {
      toast.error('Please fill all required fields');
      return;
    }
    
    setStep(3);
    runAIAnalysis();
  };

  const runAIAnalysis = async () => {
    setAnalyzing(true);
    try {
      const response = await api.post('/ai/analyze-gig', {
        title: form.title,
        description: form.description,
        category: form.category,
        video_url: form.video_url,
        thumbnail: form.thumbnail,
        price: parseFloat(form.price),
      });
      
      setAiAnalysis(response.data);
      
      if (response.data.is_fake || response.data.quality_score < 5) {
        toast.error('AI detected issues with your gig. Please review and fix.');
      } else if (response.data.quality_score >= 8) {
        toast.success('Excellent! Your gig passed AI verification!');
      } else {
        toast('Your gig is good, but could be improved. Check AI suggestions.', {
          icon: '💡',
        });
      }
    } catch (error) {
      toast.error('AI analysis failed. You can still publish.');
      setAiAnalysis({
        passed: true,
        quality_score: 7,
        is_fake: false,
        suggestions: ['AI analysis unavailable'],
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const handlePublish = async () => {
    if (aiAnalysis && aiAnalysis.is_fake) {
      toast.error('Cannot publish: AI detected fake/low-quality content');
      return;
    }
    
    setPublishing(true);
    try {
      await api.post('/gigs', {
        title: form.title,
        description: form.description,
        category: form.category,
        price: parseFloat(form.price),
        delivery_days: parseInt(form.delivery_days, 10),
        thumbnail: form.thumbnail,
        video_url: form.video_url,
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      
      toast.success('🎉 Gig published successfully!');
      router.push('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to publish gig');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white pt-20 pb-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Create New Gig
          </h1>
          <p className="text-gray-400">Upload your AMV and let AI verify the quality</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-12">
          {[
            { num: 1, label: 'Upload Video' },
            { num: 2, label: 'Add Details' },
            { num: 3, label: 'AI Check' },
            { num: 4, label: 'Publish' },
          ].map((s, idx) => (
            <div key={s.num} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    step >= s.num
                      ? 'bg-gradient-to-r from-purple-600 to-pink-600'
                      : 'bg-gray-800'
                  }`}
                >
                  {step > s.num ? <CheckCircle className="w-5 h-5" /> : s.num}
                </div>
                <span className="text-xs mt-2 text-gray-400">{s.label}</span>
              </div>
              {idx < 3 && (
                <div
                  className={`flex-1 h-1 mx-2 ${
                    step > s.num ? 'bg-purple-600' : 'bg-gray-800'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Upload Video */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
              <h2 className="text-2xl font-bold mb-6">Upload Your AMV</h2>
              
              {/* Video Upload */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-3">Video File *</label>
                <input
                  ref={videoInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleVideoSelect}
                  className="hidden"
                />
                
                {!videoPreview ? (
                  <button
                    type="button"
                    onClick={() => videoInputRef.current?.click()}
                    className="w-full border-2 border-dashed border-gray-700 rounded-xl p-12 hover:border-purple-500 transition-colors"
                  >
                    <Video className="w-16 h-16 mx-auto mb-4 text-gray-500" />
                    <p className="text-lg font-semibold mb-2">Click to select video</p>
                    <p className="text-sm text-gray-400">MP4, MOV, AVI (Max 100MB)</p>
                  </button>
                ) : (
                  <div className="relative">
                    <video
                      src={videoPreview}
                      controls
                      className="w-full rounded-xl"
                      style={{ maxHeight: '400px' }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setVideoFile(null);
                        setVideoPreview(null);
                      }}
                      className="absolute top-4 right-4 bg-red-600 hover:bg-red-700 p-2 rounded-lg"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Thumbnail Upload */}
              <div>
                <label className="block text-sm font-medium mb-3">Thumbnail Image *</label>
                <input
                  ref={thumbnailInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleThumbnailSelect}
                  className="hidden"
                />
                
                {!thumbnailPreview ? (
                  <button
                    type="button"
                    onClick={() => thumbnailInputRef.current?.click()}
                    className="w-full border-2 border-dashed border-gray-700 rounded-xl p-12 hover:border-purple-500 transition-colors"
                  >
                    <ImageIcon className="w-16 h-16 mx-auto mb-4 text-gray-500" />
                    <p className="text-lg font-semibold mb-2">Click to select thumbnail</p>
                    <p className="text-sm text-gray-400">JPG, PNG (Max 5MB)</p>
                  </button>
                ) : (
                  <div className="relative">
                    <img
                      src={thumbnailPreview}
                      alt="Thumbnail"
                      className="w-full rounded-xl"
                      style={{ maxHeight: '300px', objectFit: 'cover' }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setThumbnailFile(null);
                        setThumbnailPreview(null);
                      }}
                      className="absolute top-4 right-4 bg-red-600 hover:bg-red-700 p-2 rounded-lg"
                    >
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>

              <button
                onClick={uploadFiles}
                disabled={!videoFile || !thumbnailFile || uploading}
                className="w-full mt-6 bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload Files
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Add Details */}
        {step === 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">Gig Details</h2>
            
            <form onSubmit={handleDetailsSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Title *</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g., Epic Anime AMV - Professional Editing"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Description *</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Describe your AMV editing service, what you offer, your style, etc."
                  rows={6}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Category *</label>
                  <select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="amv">AMV</option>
                    <option value="gaming">Gaming</option>
                    <option value="tiktok">TikTok</option>
                    <option value="motion">Motion Graphics</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Price (₹) *</label>
                  <input
                    type="number"
                    value={form.price}
                    onChange={(e) => setForm({ ...form, price: e.target.value })}
                    placeholder="500"
                    min="100"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Delivery Days *</label>
                  <input
                    type="number"
                    value={form.delivery_days}
                    onChange={(e) => setForm({ ...form, delivery_days: e.target.value })}
                    min="1"
                    max="30"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Tags (comma separated)</label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  placeholder="anime, amv, editing, naruto, action"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 py-3 rounded-lg font-semibold"
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-3 rounded-lg font-semibold"
                >
                  Continue to AI Check
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Step 3: AI Analysis */}
        {step === 3 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">AI Quality Check</h2>
            
            {analyzing ? (
              <div className="text-center py-12">
                <Loader2 className="w-16 h-16 animate-spin text-purple-500 mx-auto mb-4" />
                <p className="text-lg font-semibold mb-2">AI is analyzing your gig...</p>
                <p className="text-sm text-gray-400">Checking quality, authenticity, and content</p>
              </div>
            ) : aiAnalysis ? (
              <div className="space-y-6">
                {/* Quality Score */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold">Quality Score</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-3xl font-bold">{aiAnalysis.quality_score || 0}</span>
                      <span className="text-gray-400">/10</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        aiAnalysis.quality_score >= 8
                          ? 'bg-green-500'
                          : aiAnalysis.quality_score >= 6
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${(aiAnalysis.quality_score / 10) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Verification Status */}
                <div className={`rounded-xl p-6 ${
                  aiAnalysis.is_fake
                    ? 'bg-red-500/10 border border-red-500'
                    : aiAnalysis.passed
                    ? 'bg-green-500/10 border border-green-500'
                    : 'bg-yellow-500/10 border border-yellow-500'
                }`}>
                  <div className="flex items-start gap-4">
                    {aiAnalysis.is_fake ? (
                      <XCircle className="w-8 h-8 text-red-500 flex-shrink-0" />
                    ) : aiAnalysis.passed ? (
                      <CheckCircle className="w-8 h-8 text-green-500 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-8 h-8 text-yellow-500 flex-shrink-0" />
                    )}
                    <div>
                      <h3 className="text-lg font-bold mb-2">
                        {aiAnalysis.is_fake
                          ? 'Content Rejected'
                          : aiAnalysis.passed
                          ? 'AI Verified ✓'
                          : 'Needs Improvement'}
                      </h3>
                      <p className="text-sm text-gray-300">
                        {aiAnalysis.is_fake
                          ? 'AI detected fake or low-quality content. Please review the issues below.'
                          : aiAnalysis.passed
                          ? 'Your gig meets quality standards and is ready to publish!'
                          : 'Your gig is acceptable but could be improved. Check suggestions below.'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* AI Suggestions */}
                {aiAnalysis.suggestions && aiAnalysis.suggestions.length > 0 && (
                  <div className="bg-gray-800 rounded-xl p-6">
                    <h3 className="text-lg font-bold mb-4">AI Suggestions</h3>
                    <ul className="space-y-3">
                      {aiAnalysis.suggestions.map((suggestion, idx) => (
                        <li key={idx} className="flex items-start gap-3">
                          <span className="text-purple-400 mt-1">•</span>
                          <span className="text-gray-300">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Issues Found */}
                {aiAnalysis.reasons && aiAnalysis.reasons.length > 0 && (
                  <div className="bg-red-500/10 border border-red-500 rounded-xl p-6">
                    <h3 className="text-lg font-bold mb-4 text-red-400">Issues Detected</h3>
                    <ul className="space-y-3">
                      {aiAnalysis.reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start gap-3">
                          <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                          <span className="text-gray-300">{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-4">
                  <button
                    onClick={() => setStep(2)}
                    className="flex-1 bg-gray-800 hover:bg-gray-700 py-3 rounded-lg font-semibold"
                  >
                    Edit Details
                  </button>
                  <button
                    onClick={() => setStep(4)}
                    disabled={aiAnalysis.is_fake}
                    className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {aiAnalysis.is_fake ? 'Cannot Publish' : 'Continue to Publish'}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Step 4: Publish */}
        {step === 4 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
            <h2 className="text-2xl font-bold mb-6">Ready to Publish</h2>
            
            <div className="bg-gray-800 rounded-xl p-6 mb-6">
              <h3 className="text-lg font-bold mb-4">Gig Preview</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <img
                    src={thumbnailPreview}
                    alt="Thumbnail"
                    className="w-full rounded-lg mb-4"
                  />
                  <video
                    src={videoPreview}
                    controls
                    className="w-full rounded-lg"
                  />
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-400">Title</p>
                    <p className="font-semibold">{form.title}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Description</p>
                    <p className="text-sm">{form.description}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-400">Price</p>
                      <p className="font-semibold">₹{form.price}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">Delivery</p>
                      <p className="font-semibold">{form.delivery_days} days</p>
                    </div>
                  </div>
                  {aiAnalysis && (
                    <div>
                      <p className="text-sm text-gray-400">AI Quality Score</p>
                      <p className="font-semibold text-green-400">{aiAnalysis.quality_score}/10</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => setStep(3)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 py-3 rounded-lg font-semibold"
              >
                Back
              </button>
              <button
                onClick={handlePublish}
                disabled={publishing}
                className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 py-3 rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {publishing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Publishing...
                  </>
                ) : (
                  '🚀 Publish Gig'
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
