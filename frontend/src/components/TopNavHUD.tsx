import { useState, useEffect } from 'react';
import { Target, Radio, Satellite, CloudRain, Cpu } from 'lucide-react';

export default function TopNavHUD() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="absolute top-0 left-0 right-0 z-[1200] p-4 pointer-events-none">
      <div className="flex justify-between items-center bg-[#030712]/90 backdrop-blur-xl border-b border-x border-cyan-900/40 rounded-b-xl px-5 py-3 shadow-[0_4px_30px_rgba(6,182,212,0.15)] pointer-events-auto mt-[-16px]">
        
        {/* Left: Branding & Mode */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded flex items-center justify-center bg-cyan-950/50 border border-cyan-500/50 pt-[2px]">
            <Target className="w-6 h-6 text-cyan-400 animate-pulse drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-sm font-bold tracking-[0.2em] text-cyan-50 drop-shadow-[0_0_2px_rgba(255,255,255,1)]">VAJRA // SEVERE WEATHER COMMAND</h1>
            <div className="text-[10px] text-cyan-500 tracking-widest font-bold">MODE: DUAL REPLAY INFERENCE (T-3h TO T+6h)</div>
          </div>
        </div>

        {/* Center: Ingestion Latency Pills (Command Bridge style) */}
        <div className="hidden lg:flex gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700/80 px-2.5 py-1 rounded text-[10px] tracking-widest text-slate-400 shadow-inner">
            <Radio className="w-3.5 h-3.5 text-cyan-500" />
            <span>RADAR: <span className="text-cyan-400 font-bold">24ms (DWR-DEHRADUN)</span></span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700/80 px-2.5 py-1 rounded text-[10px] tracking-widest text-slate-400 shadow-inner">
            <Satellite className="w-3.5 h-3.5 text-emerald-500" />
            <span>MOSDAC: <span className="text-emerald-400 font-bold">SYNCED (TIR1)</span></span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700/80 px-2.5 py-1 rounded text-[10px] tracking-widest text-slate-400 shadow-inner">
            <CloudRain className="w-3.5 h-3.5 text-fuchsia-500" />
            <span>ERA5: <span className="text-fuchsia-400 font-bold">0.25° ACTIVE</span></span>
          </div>
        </div>

        {/* Right: Clock & Verification Button */}
        <div className="flex items-center gap-5">
          <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 px-3 py-1.5 rounded transition-all shadow-[0_0_15px_rgba(255,255,255,0.05)] hover:shadow-[0_0_20px_rgba(6,182,212,0.2)] text-[10px] font-bold text-slate-300 tracking-widest">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            SCIENTIFIC VERIFICATION (CSI / FSS)
          </button>
          
          <div className="flex flex-col items-end leading-tight border-l border-slate-700 pl-4">
            <div className="text-cyan-400 font-bold text-sm tracking-wider drop-shadow-[0_0_5px_rgba(6,182,212,0.5)]">
              {time.toISOString().substring(11, 19)} UTC
            </div>
            <div className="text-slate-500 text-[10px] font-bold tracking-widest">
              {(new Date(time.getTime() + 5.5 * 60 * 60 * 1000)).toISOString().substring(11, 19)} IST
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
