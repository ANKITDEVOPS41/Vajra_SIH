export default function Legend() {
  return (
    <div className="absolute bottom-6 right-6 z-[1000] pointer-events-none">
      <div className="bg-slate-950/80 backdrop-blur-md border border-slate-800 p-3 rounded-lg shadow-[0_0_20px_rgba(3,7,18,0.9)] w-80">
        
        <div className="flex justify-between items-center text-[9px] text-slate-400 font-bold uppercase tracking-widest mb-1.5">
          <span>5 dBZ (Clear)</span>
          <span>75+ dBZ (Cloudburst)</span>
        </div>

        {/* Gradient Bar */}
        <div className="h-2.5 w-full rounded-sm bg-gradient-to-r from-emerald-500/20 via-emerald-500 to-amber-500 relative">
          <div className="absolute top-0 bottom-0 left-1/2 right-0 bg-gradient-to-r from-amber-500 via-red-500 to-fuchsia-600 rounded-r-sm"></div>
        </div>

        {/* Labels below */}
        <div className="flex justify-between items-center text-[8px] text-slate-500 uppercase tracking-widest mt-1.5">
          <span>Light Rain</span>
          <span className="ml-4">Severe</span>
          <span className="text-red-400">Hail</span>
          <span className="text-fuchsia-400">Extreme</span>
        </div>
        
      </div>
    </div>
  );
}
