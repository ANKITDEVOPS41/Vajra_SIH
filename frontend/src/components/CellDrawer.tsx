import { X, ShieldAlert, Activity } from 'lucide-react';

interface CellDrawerProps {
  selectedCell: number | null;
  onClose: () => void;
}

export default function CellDrawer({ selectedCell, onClose }: CellDrawerProps) {
  
  if (selectedCell === null) return null;

  return (
    <div className="absolute right-0 top-0 bottom-0 w-96 bg-[#030712]/95 backdrop-blur-2xl border-l border-cyan-900/60 p-6 font-mono z-[1100] flex flex-col gap-6 text-slate-300 pointer-events-auto transform transition-transform duration-300 ease-out shadow-[-10px_0_30px_rgba(3,7,18,0.8)] pt-24">
      
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Selected Target</span>
          <h2 className="text-xl font-bold text-cyan-400 tracking-widest flex items-center gap-2 mt-1">
            <CrosshairIcon className="w-5 h-5" />
            CELL-UK0{selectedCell}
          </h2>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-cyan-400 transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <hr className="border-cyan-950" />

      {/* Radial Progress Rings */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-900/50 rounded-xl p-4 flex flex-col items-center border border-slate-800/80">
          <div className="relative w-24 h-24 mb-2">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="48" cy="48" r="40" className="stroke-slate-800" strokeWidth="6" fill="none" />
              <circle cx="48" cy="48" r="40" className="stroke-orange-500" strokeWidth="6" fill="none" strokeDasharray="251" strokeDashoffset="30" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center flex-col">
              <span className="text-xl font-bold text-slate-100">88%</span>
            </div>
          </div>
          <span className="text-[10px] uppercase tracking-widest text-slate-400 text-center">Hail Prob</span>
        </div>

        <div className="bg-slate-900/50 rounded-xl p-4 flex flex-col items-center border border-slate-800/80 shadow-[0_0_15px_rgba(217,70,239,0.1)]">
          <div className="relative w-24 h-24 mb-2">
            <svg className="w-full h-full transform -rotate-90">
              <circle cx="48" cy="48" r="40" className="stroke-slate-800" strokeWidth="6" fill="none" />
              <circle cx="48" cy="48" r="40" className="stroke-fuchsia-500 drop-shadow-[0_0_8px_rgba(217,70,239,0.5)]" strokeWidth="6" fill="none" strokeDasharray="251" strokeDashoffset="20" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center flex-col">
              <span className="text-xl font-bold text-fuchsia-400">92%</span>
            </div>
          </div>
          <span className="text-[10px] uppercase tracking-widest text-fuchsia-400 font-bold text-center">Cloudburst Risk</span>
        </div>
      </div>

      {/* Sparkline Graph */}
      <div className="flex flex-col gap-2 mt-2">
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400 uppercase tracking-widest"><Activity className="w-4 h-4 inline mr-1"/> Intensity Growth</span>
          <span className="text-cyan-500">+14 dBZ/hr</span>
        </div>
        <div className="h-16 w-full bg-slate-900/50 rounded border border-slate-800 relative overflow-hidden">
           <svg viewBox="0 0 200 60" className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
            <defs>
              <linearGradient id="sparkline-gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#06B6D4" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path className="sparkline-area" d="M0,50 L20,45 L40,40 L60,48 L80,30 L100,35 L120,20 L140,25 L160,10 L180,15 L200,5 L200,60 L0,60 Z" />
            <path className="sparkline-path" d="M0,50 L20,45 L40,40 L60,48 L80,30 L100,35 L120,20 L140,25 L160,10 L180,15 L200,5" />
           </svg>
        </div>
      </div>

      <div className="mt-auto">
        <button className="w-full bg-red-950/40 hover:bg-red-900/60 border border-red-500/50 text-red-400 p-4 rounded text-sm font-bold tracking-widest transition-all hover:shadow-[0_0_20px_rgba(239,68,68,0.3)] flex items-center justify-center gap-2 group">
          <ShieldAlert className="w-5 h-5 group-hover:scale-110 transition-transform" />
          GENERATE NDMA CAP 1.2 DISPATCH
        </button>
      </div>

    </div>
  );
}

function CrosshairIcon(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="22" x2="18" y1="12" y2="12"/>
      <line x1="6" x2="2" y1="12" y2="12"/>
      <line x1="12" x2="12" y1="6" y2="2"/>
      <line x1="12" x2="12" y1="22" y2="18"/>
    </svg>
  );
}
