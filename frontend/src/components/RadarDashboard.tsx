import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, ImageOverlay, ZoomControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Sleek Circular Progress Ring for Telemetry Specs utilizing dynamic SVG boundaries
const CircularProgress = ({ value, label }) => {
  const radius = 24;
  const circumference = 2 * Math.PI * radius;
  const safeVal = isNaN(value) ? 0 : value;
  const offset = circumference - (safeVal * circumference);
  
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div className="relative flex items-center justify-center w-14 h-14 shrink-0 transition-transform hover:scale-110 duration-500">
        <svg className="transform -rotate-90 w-14 h-14">
          <circle cx="28" cy="28" r={radius} stroke="currentColor" strokeWidth="2.5" fill="transparent" className="text-white/10" />
          <circle 
            cx="28" cy="28" r={radius} 
            stroke="currentColor" strokeWidth="3" fill="transparent" 
            strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
            className="text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)] transition-all duration-1000 ease-out" 
          />
        </svg>
        <span className="absolute text-emerald-300 font-mono text-xs font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.8)] tracking-tighter">
          {safeVal.toFixed(2)}
        </span>
      </div>
      <span className="text-[9px] text-slate-400 tracking-[0.2em] uppercase font-bold text-center mt-1 w-max">{label}</span>
    </div>
  );
};

const RadarDashboard = () => {
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [frameIndex, setFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameImages, setFrameImages] = useState([]);
  
  // Tactical Operational Map Bounds (Bhubaneswar Grid Coverage)
  const bounds = [
    [19.0, 84.0], 
    [21.5, 87.0]  
  ];

  // 1. Sync Radar Frames from Backend Pipeline
  useEffect(() => {
    const fetchNowcast = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/forecast/nowcast');
        if (!response.ok) throw new Error(`HTTP System Runtime Error: ${response.status}`);
        
        const data = await response.json();
        setForecastData(data);
        generateOverlayImages(data.grids);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };
    fetchNowcast();
  }, []);

  // 2. Headless GPU rendering via Canvas -> Base64
  const generateOverlayImages = (grids) => {
    const urls = [];
    const H = grids[0].length;
    const W = grids[0][0].length;
    
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    grids.forEach(grid => {
      ctx.clearRect(0, 0, W, H);
      const imageData = ctx.createImageData(W, H);
      let dataIndex = 0;

      for (let i = 0; i < H; i++) {
        for (let j = 0; j < W; j++) {
          const val = grid[i][j];
          let r = 0, g = 0, b = 0, a = 0; 
          
          // CRITICAL NOISE FILTER: Completely masks atmospheric background static
          if (val > 0.25) {
              if (val < 0.35)      { r = 0;   g = 180; b = 255; a = 160; } // Light Blue Margin
              else if (val < 0.50) { r = 0;   g = 255; b = 255; a = 190; } // Cyan
              else if (val < 0.65) { r = 0;   g = 255; b = 100; a = 210; } // Green Core
              else if (val < 0.85) { r = 255; g = 220; b = 0;   a = 240; } // Yellow Core
              else                 { r = 255; g = 30;  b = 40;  a = 255; } // Deep Red Hazard Core
          }
          
          imageData.data[dataIndex++] = r;
          imageData.data[dataIndex++] = g;
          imageData.data[dataIndex++] = b;
          imageData.data[dataIndex++] = a;
        }
      }
      ctx.putImageData(imageData, 0, 0);
      urls.push(canvas.toDataURL('image/png'));
    });
    setFrameImages(urls);
  };

  // 3. Extrapolation Automated Playback System (Tracking locked ~400ms)
  useEffect(() => {
    let interval = null;
    if (isPlaying && forecastData) {
      interval = setInterval(() => {
        setFrameIndex((prevIndex) => {
          if (prevIndex >= forecastData.forecast_sequence.total_frames - 1) return 0; 
          return prevIndex + 1;
        });
      }, 400); 
    } else if (!isPlaying && interval) {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying, forecastData]);

  // Cyberpunk Loading State Integration directly mapping Bento boundaries
  if (loading) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center relative overflow-hidden bg-black isolate rounded-[32px]">
        {/* Glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.1)_0%,transparent_60%)] pointer-events-none"></div>
        {/* Spinners */}
        <div className="relative flex items-center justify-center z-10 w-24 h-24">
            <div className="absolute w-full h-full border-[3px] border-slate-900 border-b-cyan-500 rounded-full animate-[spin_1.5s_linear_infinite] shadow-[0_0_15px_rgba(6,182,212,0.6)]"></div>
            <div className="absolute w-16 h-16 border-[3px] border-slate-900 border-t-emerald-400 rounded-full animate-[spin_2s_reverse_infinite] shadow-[0_0_15px_rgba(16,185,129,0.5)]"></div>
            <div className="absolute w-2 h-2 bg-white shadow-[0_0_15px_rgba(255,255,255,1)] animate-ping rounded-full"></div>
        </div>
        <div className="mt-8 text-cyan-400 font-mono text-[10px] tracking-[0.4em] font-extrabold uppercase">Synchronizing Array Pipelines...</div>
      </div>
    );
  }

  if (error) return (
     <div className="w-full h-full flex items-center justify-center p-8 bg-black">
        <div className="bg-red-950/30 border border-red-500/50 shadow-[0_0_40px_rgba(239,68,68,0.2)] rounded-2xl font-mono p-6 text-red-500 text-sm tracking-widest font-bold">
            UPLINK FAILURE: {error}
        </div>
     </div>
  );

  const { telemetry, forecast_sequence } = forecastData;

  return (
    <div className="w-full h-full relative group">
      
      {/* Dynamic CSS override mapping OpenStreetMap tiles into negative hue (Aesthetic Dark Mode requirement) */}
      <style>{`
        .bento-dark-map .leaflet-layer {
          filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
        }
      `}</style>
      
      {/* BASE MAP: LEAFLET FRAME */}
      <MapContainer 
        center={[20.2961, 85.8245]} 
        zoom={8} 
        zoomControl={false}
        className="absolute inset-0 w-full h-full z-0 font-sans bento-dark-map bg-black"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />
        <ZoomControl position="bottomright" />
        
        {/* Dynamic Canvas Image Proxy (Storm Projection Sequence) */}
        {frameImages.length > 0 && (
           <ImageOverlay 
              url={frameImages[frameIndex]} 
              bounds={bounds} 
              opacity={0.88} 
              className="drop-shadow-[0_0_8px_rgba(0,0,0,0.9)] filter saturate-[1.2]" 
           />
        )}
      </MapContainer>

      {/* TACTICAL MILITARY CROSSHAIRS (Map Center Coordinates) */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-[400] flex items-center justify-center group-hover:scale-[1.02] transition-transform duration-1000">
        <div className="w-[180px] h-[180px] border border-cyan-500/10 rounded-full absolute mix-blend-screen"></div>
        <div className="w-[80px] h-[80px] border border-cyan-400/20 rounded-full absolute"></div>
        <div className="w-[1px] h-[140px] bg-cyan-400/20 absolute"></div>
        <div className="h-[1px] w-[140px] bg-cyan-400/20 absolute"></div>
        <div className="w-1.5 h-1.5 bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,1)] rounded-full ring-2 ring-black/50"></div>
      </div>

      {/* FLOATING TELEMETRY WIDGET (Top Right Hover Module) */}
      <div className="absolute top-6 right-6 z-[1000] flex gap-4 pointer-events-none bg-black/40 backdrop-blur-2xl border border-white/10 p-5 rounded-3xl shadow-[0_8px_32px_rgba(0,0,0,0.5)] overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent pointer-events-none"></div>
        <div className="relative z-10 flex gap-6 px-2 py-1">
          <CircularProgress value={telemetry.csi_confidence_score} label="CSI Ratio" />
          <div className="w-[1px] bg-white/10 my-1"></div>
          <CircularProgress value={telemetry.pod_confidence_score} label="POD Prob" />
        </div>
      </div>

      {/* FLOATING PLAYBACK CONSOLE (Bottom Center Scrubber Overlay) */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000] w-[90%] max-w-xl bg-black/60 backdrop-blur-2xl border border-white/10 px-8 py-5 rounded-[32px] shadow-[0_20px_40px_rgba(0,0,0,0.6)] flex items-center gap-6 group/console hover:bg-black/70 hover:border-cyan-500/30 hover:shadow-[0_0_30px_rgba(6,182,212,0.1)] transition-all duration-500 cursor-auto">
        
        {/* Play/Pause Button Engine */}
        <button 
          onClick={(e) => {
            e.stopPropagation();
            setIsPlaying(!isPlaying);
          }}
          className={`shrink-0 flex items-center justify-center w-12 h-12 rounded-full outline-none transition-all duration-300 relative font-bold ${
            isPlaying 
            ? 'bg-red-500/10 text-red-500 border border-red-500/30 hover:bg-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.3)]' 
            : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/20 shadow-[0_0_20px_rgba(6,182,212,0.4)]'
          }`}
        >
          {isPlaying ? (
            <svg className="w-5 h-5 fill-current drop-shadow-[0_0_8px_currentColor]" viewBox="0 0 24 24"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg> 
          ) : (
            <svg className="w-5 h-5 fill-current ml-1 drop-shadow-[0_0_8px_currentColor]" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>

        {/* Dynamic Scrubbing Timeline Track */}
        <div className="flex-1 flex flex-col pt-1">
          <div className="flex justify-between items-end mb-2.5 px-0.5">
             <span className="text-cyan-400 font-mono text-[11px] font-extrabold tracking-widest drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">
                 T+{(frameIndex + 1) * 5} MIN
             </span>
             <span className="text-[9px] text-slate-500 font-mono tracking-[0.25em] uppercase font-bold">
                 Horizon Scan
             </span>
          </div>

          <div className="relative w-full flex items-center h-4 cursor-pointer">
            {/* Ambient track backbone */}
            <div className="absolute left-0 right-0 h-1.5 bg-black border border-white/5 rounded-full overflow-hidden pointer-events-none group-hover/console:border-white/10 transition-colors">
              <div 
                  className="h-full bg-gradient-to-r from-cyan-900 via-cyan-500 to-cyan-300 transition-all duration-[400ms] ease-linear shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                  style={{ width: `${(frameIndex / (forecastData.forecast_sequence.total_frames - 1)) * 100}%` }}
              ></div>
            </div>
            
            {/* HTML Slider Mapping dynamically */}
            <input 
              type="range" 
              min="0" 
              max={forecastData.forecast_sequence.total_frames - 1} 
              value={frameIndex}
              onChange={(e) => {
                e.stopPropagation();
                setFrameIndex(Number(e.target.value));
                setIsPlaying(false); 
              }}
              className="absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-cyan-500 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-[0_0_15px_rgba(34,211,238,1)] focus:outline-none"
            />
          </div>
        </div>
      </div>
      
    </div>
  );
};

export default RadarDashboard;
