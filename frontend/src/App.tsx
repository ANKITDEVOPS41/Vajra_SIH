import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, ImageOverlay, ZoomControl } from 'react-leaflet';
import { AreaChart, Area, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, ShieldAlert, Cpu, Zap, Terminal, Map as MapIcon, Database, Play, Pause, RefreshCw } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

export default function App() {
  const [csi, setCsi] = useState<number>(0.00);
  const [pod, setPod] = useState<number>(0.00);
  const [frameIndex, setFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [frameImages, setFrameImages] = useState<string[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [wsStatus, setWsStatus] = useState<'CONNECTING' | 'CONNECTED' | 'DISCONNECTED'>('CONNECTING');
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  
  const bounds: [number, number][] = [[19.0, 84.0], [21.5, 87.0]];

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const connectWebSocket = () => {
    if (wsRef.current) wsRef.current.close();
    setWsStatus('CONNECTING');
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] Initiating WebSocket Uplink...`]);

    const ws = new WebSocket('ws://127.0.0.1:8000/api/v1/forecast/ws/stream');
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('CONNECTED');
    };

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      if (payload.type === 'log') {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${payload.message}`]);
      } 
      else if (payload.type === 'telemetry') {
        setCsi(payload.csi);
        setPod(payload.pod);
        setTrendData([{ time: "T+0", confidence: 95 }]);
      } 
      else if (payload.type === 'heartbeat') {
        setTrendData(prev => [...prev.slice(-15), { time: payload.time, confidence: payload.confidence }]);
      }
      else if (payload.type === 'frame') {
        const grid = payload.data;
        const H = grid.length;
        const W = grid[0].length;
        const canvas = document.createElement('canvas');
        canvas.width = W; canvas.height = H;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            const imageData = ctx.createImageData(W, H);
            let idx = 0;
            for (let i = 0; i < H; i++) {
              for (let j = 0; j < W; j++) {
                  const val = grid[i][j];
                  let r = 0, g = 0, b = 0, a = 0;
                  if (val > 0.25) { 
                    if (val < 0.40)      { r = 14;  g = 165; b = 233; a = 120; } 
                    else if (val < 0.60) { r = 16;  g = 185; b = 129; a = 180; } 
                    else if (val < 0.80) { r = 234; g = 179; b = 8;   a = 220; } 
                    else                 { r = 239; g = 68;  b = 68;  a = 255; } 
                  }
                  imageData.data[idx++] = r; imageData.data[idx++] = g; imageData.data[idx++] = b; imageData.data[idx++] = a;
              }
            }
            ctx.putImageData(imageData, 0, 0);
            setFrameImages(prev => [...prev, canvas.toDataURL('image/png')]);
        }
      }
    };

    ws.onclose = () => setWsStatus('DISCONNECTED');
    ws.onerror = () => setWsStatus('DISCONNECTED');
  };

  // Robust mount/unmount handling
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (isPlaying && frameImages.length > 0) {
      interval = setInterval(() => {
        setFrameIndex(prev => prev >= frameImages.length - 1 ? 0 : prev + 1);
      }, 400);
    } else if (interval) {
      clearInterval(interval);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [isPlaying, frameImages]);

  return (
    <div className="flex h-screen bg-[#020202] text-slate-200 font-sans overflow-hidden selection:bg-cyan-500/30">
      
      {/* LEFT SIDEBAR */}
      <aside className="w-72 flex flex-col bg-[#050507] border-r border-white/5 z-20 shadow-2xl shrink-0">
        <div className="p-8 border-b border-white/5 bg-gradient-to-b from-cyan-950/20 to-transparent">
          <h1 className="text-4xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400 drop-shadow-[0_0_15px_rgba(6,182,212,0.3)]">
            VAJRA
          </h1>
          <p className="text-[10px] font-bold tracking-[0.3em] text-cyan-500/70 mt-2 uppercase">Spatiotemporal Engine</p>
        </div>
        
        <nav className="flex-1 p-6 space-y-2">
           <button className="w-full flex items-center gap-4 px-4 py-3.5 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20 shadow-[inset_0_0_20px_rgba(6,182,212,0.05)]">
             <MapIcon size={18} />
             <span className="text-sm font-bold tracking-wide">Tactical Radar</span>
           </button>
           <button className="w-full flex items-center gap-4 px-4 py-3.5 text-slate-400 hover:bg-white/[0.02] hover:text-slate-200 rounded-xl transition-all">
             <Activity size={18} />
             <span className="text-sm font-semibold tracking-wide">Model Telemetry</span>
           </button>
        </nav>
        
        <div className="p-6 border-t border-white/5 bg-black/40">
          {/* Dynamic Network Sensor */}
          <div className={`flex items-center justify-between px-4 py-3 rounded-lg mb-4 border ${
              wsStatus === 'CONNECTED' ? 'bg-emerald-500/10 border-emerald-500/30' : 
              wsStatus === 'CONNECTING' ? 'bg-yellow-500/10 border-yellow-500/30' : 
              'bg-red-500/10 border-red-500/30'
            }`}>
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full animate-pulse ${
                wsStatus === 'CONNECTED' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 
                wsStatus === 'CONNECTING' ? 'bg-yellow-400' : 'bg-red-400'
              }`}></div>
              <span className={`text-xs font-mono font-bold tracking-widest ${
                wsStatus === 'CONNECTED' ? 'text-emerald-400' : 
                wsStatus === 'CONNECTING' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {wsStatus}
              </span>
            </div>
            {wsStatus === 'DISCONNECTED' && (
              <button onClick={connectWebSocket} className="text-red-400 hover:text-white transition-colors">
                <RefreshCw size={14} />
              </button>
            )}
          </div>
          
          <div className="text-[10px] font-mono text-slate-500 space-y-1.5 uppercase tracking-widest">
            <p>SIH 2026 MVP Build</p>
            <p className="text-slate-400">C. V. Raman Global Univ.</p>
            <p className="text-cyan-500/80 font-bold mt-2 pt-2 border-t border-white/5">Lead: Ankit Dash</p>
          </div>
        </div>
      </aside>

      {/* MAIN WORKSPACE */}
      <main className="flex-1 p-6 flex flex-col gap-6 overflow-hidden bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-fixed relative">
        <div className="absolute inset-0 bg-gradient-to-br from-[#020202] via-[#050505]/95 to-[#0a0a0c] pointer-events-none -z-10"></div>
        
        {/* TOP ROW */}
        <div className="grid grid-cols-4 gap-6 shrink-0 z-10">
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-5 rounded-2xl flex items-center justify-between">
            <div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-1">CSI Metric</p>
              <p className="text-3xl font-mono font-light text-cyan-400">{csi.toFixed(2)}</p>
            </div>
            <div className="p-3 bg-cyan-500/10 rounded-xl"><Activity size={24} className="text-cyan-500" /></div>
          </div>
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-5 rounded-2xl flex items-center justify-between">
            <div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-1">POD Score</p>
              <p className="text-3xl font-mono font-light text-emerald-400">{pod.toFixed(2)}</p>
            </div>
            <div className="p-3 bg-emerald-500/10 rounded-xl"><ShieldAlert size={24} className="text-emerald-500" /></div>
          </div>
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-5 rounded-2xl flex items-center justify-between">
            <div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-1">Compute Core</p>
              <p className="text-lg font-mono font-bold text-slate-200 mt-1">ConvLSTM</p>
            </div>
            <div className="p-3 bg-purple-500/10 rounded-xl"><Cpu size={24} className="text-purple-500" /></div>
          </div>
          <div className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-5 rounded-2xl flex items-center justify-between">
            <div>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-1">Live Horizon</p>
              <p className="text-lg font-mono font-bold text-slate-200 mt-1">T+60 MIN</p>
            </div>
            <div className="p-3 bg-rose-500/10 rounded-xl"><Zap size={24} className="text-rose-500" /></div>
          </div>
        </div>

        {/* MIDDLE ROW */}
        <div className="flex-1 flex gap-6 min-h-0 z-10">
          
          {/* Tactical Map */}
          <div className="flex-[2] bg-white/[0.02] backdrop-blur-xl border border-white/5 rounded-2xl overflow-hidden relative shadow-2xl flex flex-col">
            <div className="absolute top-4 left-4 z-[1000] bg-black/60 backdrop-blur-md border border-white/10 px-4 py-2 rounded-lg flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
              </span>
              <span className="text-xs font-mono font-bold tracking-widest text-white uppercase">Live WebSocket Uplink</span>
            </div>

            <MapContainer center={[20.2961, 85.8245]} zoom={8} zoomControl={false} className="w-full h-full bg-[#1e1e1e]">
              <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}" />
              <ZoomControl position="topright" />
              {frameImages.length > 0 && frameImages[frameIndex] && (
                <ImageOverlay url={frameImages[frameIndex]} bounds={bounds} opacity={0.8} />
              )}
            </MapContainer>

            {/* Playback Controls */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] w-[80%] max-w-2xl bg-[#050507]/90 backdrop-blur-xl border border-cyan-500/30 p-4 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex items-center gap-6">
              <button 
                onClick={() => setIsPlaying(!isPlaying)}
                className={`w-14 h-14 shrink-0 flex items-center justify-center rounded-xl transition-all ${
                  isPlaying ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                }`}
              >
                {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" className="ml-1" />}
              </button>
              
              <div className="flex-1 flex flex-col gap-2">
                <div className="flex justify-between items-end">
                  <span className="text-cyan-400 font-mono text-sm font-bold tracking-widest">T+{(frameIndex + 1) * 5} MIN</span>
                </div>
                <input 
                  type="range" min="0" max={Math.max(0, frameImages.length - 1)} 
                  value={frameIndex} onChange={(e) => { setFrameIndex(Number(e.target.value)); setIsPlaying(false); }}
                  className="w-full h-2 bg-slate-800 rounded-full appearance-none cursor-pointer accent-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* Analytics & Logs */}
          <div className="flex-1 max-w-[400px] flex flex-col gap-6">
            
            {/* Live Chart */}
            <div className="flex-1 bg-white/[0.02] backdrop-blur-xl border border-white/5 rounded-2xl p-5 flex flex-col shadow-xl">
              <h3 className="text-[11px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                <Activity size={14} className="text-cyan-500" /> Live Trajectory Confidence
              </h3>
              <div className="flex-1 min-h-0 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="colorConf" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Tooltip contentStyle={{ backgroundColor: '#0a0a0c', borderColor: '#334155' }} itemStyle={{ color: '#22d3ee' }} />
                    <Area type="monotone" dataKey="confidence" stroke="#22d3ee" strokeWidth={2} fillOpacity={1} fill="url(#colorConf)" isAnimationActive={true} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Live Terminal */}
            <div className="h-48 bg-[#020202] border border-white/5 rounded-2xl p-5 font-mono text-[10px] shadow-inner flex flex-col overflow-hidden">
              <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                <Terminal size={12} /> WebSocket Stream Logs
              </h3>
              <div className="flex-1 overflow-y-auto space-y-1.5 text-slate-400 pr-2">
                {logs.map((log, i) => (
                  <p key={i} className={`${log.includes('complete') ? 'text-emerald-400' : log.includes('T+') ? 'text-cyan-400' : 'text-slate-400'}`}>
                    {log}
                  </p>
                ))}
                <div ref={logsEndRef} />
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
