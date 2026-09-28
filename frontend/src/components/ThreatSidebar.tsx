import { AlertTriangle, Crosshair, Wind, Thermometer, CloudLightning } from 'lucide-react';

export default function ThreatSidebar() {
  return (
    <div className="absolute left-0 top-0 bottom-0 w-80 bg-slate-950/85 backdrop-blur-xl border-r border-cyan-900/40 p-5 font-mono z-[1000] flex flex-col gap-6 pt-24 text-slate-300 pointer-events-auto overflow-y-auto overflow-x-hidden shadow-[4px_0_24px_rgba(6,182,212,0.1)]">
      
      {/* DEFCON Threat Level */}
      <div className="flex flex-col gap-2">
        <div className="px-3 py-2 bg-red-950/50 border border-red-500/50 rounded flex items-center justify-between text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 animate-pulse" />
            <span className="text-sm font-bold tracking-wider">DEFCON 2</span>
          </div>
          <span className="text-xs animate-pulse">SEVERE</span>
        </div>
        <div className="text-[10px] uppercase text-red-400/80 tracking-widest pl-1">
          THREAT LEVEL: SEVERE CONVECTIVE ALERT
        </div>
      </div>

      <hr className="border-cyan-900/30" />

      {/* Target Cell Tracker */}
      <div className="flex flex-col gap-3">
        <h2 className="text-xs font-bold text-cyan-500 tracking-widest flex items-center gap-2">
          <Crosshair className="w-4 h-4" />
          ACTIVE TARGET CELLS
        </h2>
        
        {/* Cell 1 */}
        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded hover:border-cyan-700/50 transition-colors cursor-pointer group">
          <div className="flex justify-between items-center mb-2">
            <span className="text-cyan-400 font-bold text-sm tracking-widest group-hover:text-cyan-300">CELL-UK01</span>
            <span className="text-xs text-red-400 font-bold bg-red-950/30 px-1.5 py-0.5 rounded border border-red-900/50">62 dBZ</span>
          </div>
          <div className="flex flex-col gap-1 text-[11px] text-slate-400">
            <div className="flex justify-between">
              <span>HDG: 045° (NE)</span>
              <span>SPD: 48 km/h</span>
            </div>
            <div className="flex justify-between text-orange-300">
              <span>ETA RISHIKESH:</span>
              <span className="font-bold -tracking-tighter">-24 MINS</span>
            </div>
          </div>
        </div>

        {/* Cell 2 */}
        <div className="p-3 bg-slate-900/60 border border-slate-800 rounded hover:border-cyan-700/50 transition-colors cursor-pointer group">
          <div className="flex justify-between items-center mb-2">
            <span className="text-cyan-400 font-bold text-sm tracking-widest group-hover:text-cyan-300">CELL-UK02</span>
            <span className="text-xs text-orange-400 font-bold bg-orange-950/30 px-1.5 py-0.5 rounded border border-orange-900/50">48 dBZ</span>
          </div>
          <div className="flex flex-col gap-1 text-[11px] text-slate-400">
            <div className="flex justify-between">
              <span>HDG: 080° (E)</span>
              <span>SPD: 32 km/h</span>
            </div>
            <div className="flex justify-between text-cyan-300">
              <span>ETA DEHRADUN:</span>
              <span className="font-bold -tracking-tighter">-45 MINS</span>
            </div>
          </div>
        </div>
      </div>

      <hr className="border-cyan-900/30" />

      {/* Atmospheric Telemetry */}
      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-bold text-cyan-500 tracking-widest flex items-center gap-2">
          <CloudLightning className="w-4 h-4" />
          ATMOSPHERIC TELEMETRY
        </h2>
        
        <div className="grid grid-cols-2 gap-3 text-[11px]">
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800 flex flex-col items-center">
            <Wind className="w-4 h-4 text-slate-400 mb-1" />
            <span className="text-slate-500">CAPE</span>
            <span className="text-cyan-400 font-bold tracking-wider text-sm mt-1">2,850</span>
            <span className="text-[9px]">J/kg</span>
          </div>
          
          <div className="bg-slate-900/80 p-2 rounded border border-slate-800 flex flex-col items-center">
            <CloudLightning className="w-4 h-4 text-slate-400 mb-1" />
            <span className="text-slate-500">VIL</span>
            <span className="text-cyan-400 font-bold tracking-wider text-sm mt-1">42</span>
            <span className="text-[9px]">kg/m²</span>
          </div>

          <div className="col-span-2 bg-slate-900/80 p-2 rounded border border-slate-800 flex justify-between items-center px-4">
            <div className="flex items-center gap-2">
              <Thermometer className="w-4 h-4 text-slate-400" />
              <span className="text-slate-500">CLOUD-TOP</span>
            </div>
            <span className="text-cyan-400 font-bold tracking-wider">-64°C</span>
          </div>
        </div>
      </div>

    </div>
  );
}
