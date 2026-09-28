import { Play, Pause, FastForward } from 'lucide-react';

interface TimelineScrubberProps {
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
  speed: 1 | 2;
  setSpeed: (speed: 1 | 2) => void;
  progress: number;
  setProgress: (progress: number) => void;
}

export default function TimelineScrubber({
  isPlaying, setIsPlaying, speed, setSpeed, progress, setProgress
}: TimelineScrubberProps) {
  
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProgress(Number(e.target.value));
  };
  
  // Calculate relative time string based on progress (-3h to +6h)
  // Total span is 9 hours
  const totalHours = 9;
  const currentOffset = (progress / 100) * totalHours - 3;
  
  const sign = currentOffset >= 0 ? '+' : '-';
  const hours = Math.floor(Math.abs(currentOffset));
  const mins = Math.floor((Math.abs(currentOffset) - hours) * 60);
  const timeString = `T${sign}${hours}h ${mins > 0 ? `${mins}m` : '00m'}`;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] w-11/12 max-w-4xl">
      <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-xl p-4 flex flex-col gap-3 shadow-2xl shadow-cyan-900/20">
        
        <div className="flex justify-between items-center px-1 font-mono text-xs font-bold text-slate-400">
          <span>T-3h</span>
          <span className="text-cyan-400 text-sm bg-slate-950 px-2 py-1 rounded border border-slate-800">
            {timeString}
          </span>
          <span>T+6h</span>
        </div>
        
        <input 
          type="range" 
          min="0" 
          max="100" 
          step="0.5"
          value={progress}
          onChange={handleSliderChange}
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
        />

        <div className="flex justify-center items-center gap-4 mt-1">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center justify-center w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 border border-slate-600 text-cyan-400 transition-colors"
          >
            {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
          </button>
          
          <button 
            onClick={() => setSpeed(speed === 1 ? 2 : 1)}
            className={`flex items-center justify-center px-3 h-8 rounded-md font-mono text-sm transition-colors border ${
              speed === 2 
                ? 'bg-cyan-900/50 border-cyan-500 text-cyan-400' 
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <FastForward className="w-3 h-3 mr-1" />
            {speed}x
          </button>
        </div>

      </div>
    </div>
  );
}
