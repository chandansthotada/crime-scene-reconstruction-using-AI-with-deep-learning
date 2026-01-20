import React, { useState } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ImageUploader from './components/ImageUploader';
import { analyzeCrimeSceneImages } from './services/geminiService';
import { generateAndSendReport } from './services/reportService';
import { AnalysisStatus, CrimeSceneAnalysis, UserProfile } from './types';
import { ScanFace, LogOut, ShieldCheck } from 'lucide-react';

const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>(AnalysisStatus.IDLE);
  const [analysisData, setAnalysisData] = useState<CrimeSceneAnalysis | null>(null);
  const [uploadedImages, setUploadedImages] = useState<string[]>([]);

  const handleLogin = (userInfo: UserProfile) => {
    setUser(userInfo);
  };

  const handleLogout = () => {
    setUser(null);
    setAnalysisData(null);
    setUploadedImages([]);
    setStatus(AnalysisStatus.IDLE);
  };

  const handleUpload = async (files: File[]) => {
    setStatus(AnalysisStatus.UPLOADING);

    // Create blob URLs for preview
    const newImageUrls = files.map(file => URL.createObjectURL(file));
    setUploadedImages(prev => [...prev, ...newImageUrls]);

    // Artificial delay for UX
    await new Promise(resolve => setTimeout(resolve, 1000));

    setStatus(AnalysisStatus.ANALYZING);
    try {
      const data = await analyzeCrimeSceneImages(files);
      // Attach the image URLs to the data so modules can use them
      const dataWithImages = { ...data, imageUrls: newImageUrls };
      setAnalysisData(dataWithImages);
      setStatus(AnalysisStatus.COMPLETE);
    } catch (error) {
      console.error(error);
      setStatus(AnalysisStatus.ERROR);
      // Reset after error after a delay
      setTimeout(() => setStatus(AnalysisStatus.IDLE), 3000);
    }
  };

  const handleDownloadReport = async (email?: string) => {
    if (!analysisData || !user) return;

    const targetEmail = email || user.email;
    const success = await generateAndSendReport(analysisData, user, targetEmail);

    if (success) {
      alert(`Report encrypted and transmitted to secure SMTP gateway: ${targetEmail}`);
    } else {
      alert("Transmission failed. Check console for details.");
    }
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30">
      {/* Header / Navbar */}
      <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
            <ScanFace className="text-cyan-400" size={24} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">ForensicLens<span className="text-cyan-400">3D</span></h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">
              Classified • Clearance Level 5
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-sm font-medium text-white">{user.name}</span>
            <span className="text-xs text-slate-500 font-mono flex items-center gap-1">
              <ShieldCheck size={10} className="text-emerald-500" />
              ID: {user.badgeId}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-red-400"
            title="Secure Logout"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-slate-950 -z-10"></div>

        {status === AnalysisStatus.IDLE || status === AnalysisStatus.UPLOADING || status === AnalysisStatus.ANALYZING || status === AnalysisStatus.ERROR ? (
          <ImageUploader onUpload={handleUpload} status={status} />
        ) : (
          analysisData && (
            <Dashboard
              data={analysisData}
              onReset={() => {
                setAnalysisData(null);
                setUploadedImages([]);
                setStatus(AnalysisStatus.IDLE);
              }}
              onDownloadReport={handleDownloadReport}
              uploadedImages={uploadedImages}
            />
          )
        )}
      </main>
    </div>
  );
};

export default App;