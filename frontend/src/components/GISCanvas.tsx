import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface GISCanvasProps {
  progress: number;
  selectedCell: number | null;
  setSelectedCell: (id: number | null) => void;
}

const CENTER: [number, number] = [30.3, 78.0];

// Refined target cells matching the ThreatSidebar
const mockCells = [
  { id: 1, name: "CELL-UK01", lat: 30.2, lng: 77.8, dbz: 62, direction: [0.1, 0.1], heading: "045°" },
  { id: 2, name: "CELL-UK02", lat: 30.4, lng: 78.2, dbz: 48, direction: [0.15, 0.05], heading: "080°" }
];

export default function GISCanvas({ progress, selectedCell, setSelectedCell }: GISCanvasProps) {
  
  // Progress offset sets simulation playback offset
  const offset = (progress - 50) * 0.005;

  return (
    <div className="absolute inset-0 z-0 bg-[#030712]">
      <MapContainer 
        center={CENTER} 
        zoom={9} 
        zoomControl={false}
        className="w-full h-full bg-[#030712] cursor-crosshair"
        scrollWheelZoom={true}
        style={{ background: '#030712' }}
      >
        <TileLayer
          attribution='&copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
        />

        {/* Global CSS tactical grid overlay */}
        <div className="absolute inset-0 pointer-events-none z-[400]" 
             style={{
               backgroundImage: `linear-gradient(rgba(6,182,212,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(6,182,212,0.15) 1px, transparent 1px)`,
               backgroundSize: '100px 100px',
               backgroundPosition: 'center center'
             }}>
        </div>

        {/* Tactical Crosshairs fixed on grid intersections */}
        <div className="absolute inset-0 pointer-events-none z-[400] flex justify-center items-center">
            <div className="w-full h-[1px] bg-cyan-500/20 absolute top-1/2"></div>
            <div className="h-full w-[1px] bg-cyan-500/20 absolute left-1/2"></div>
            {/* Spinning Radar Sweep */}
            <div className="radar-sweep absolute w-[800px] h-[800px] rounded-full border border-cyan-900/30 bg-[conic-gradient(from_0deg_at_50%_50%,rgba(6,182,212,0)_0deg,rgba(6,182,212,0.05)_270deg,rgba(6,182,212,0.4)_360deg)]"></div>
        </div>

        {mockCells.map(cell => {
          const currentLat = cell.lat + cell.direction[0] * offset;
          const currentLng = cell.lng + cell.direction[1] * offset;
          // Projected vector end point
          const projectedLat = currentLat + cell.direction[0] * 3;
          const projectedLng = currentLng + cell.direction[1] * 3;

          const isSelected = selectedCell === cell.id;

          return (
            <div key={cell.id}>
              {/* Multi-layered Realistic Radar Reflectivity Blur Canvas */}
              
              {/* Outer Fringe: 15-30 dBZ Light Rain */}
              <CircleMarker
                center={[currentLat, currentLng]}
                radius={40}
                pathOptions={{ fillOpacity: 0.25, fillColor: 'rgba(16, 185, 129, 1)', stroke: false }}
                pane="overlayPane"
              />
              
              {/* Moderate Storm: 35-45 dBZ */}
              {cell.dbz >= 35 && (
                <CircleMarker
                  center={[currentLat, currentLng]}
                  radius={25}
                  pathOptions={{ fillOpacity: 0.65, fillColor: 'rgba(245, 158, 11, 1)', stroke: false }}
                />
              )}
              
              {/* Severe Convection: 50-60 dBZ */}
              {cell.dbz >= 50 && (
                <CircleMarker
                  center={[currentLat, currentLng]}
                  radius={12}
                  pathOptions={{ fillOpacity: 0.85, fillColor: 'rgba(239, 68, 68, 1)', stroke: false }}
                />
              )}

              {/* Cloudburst Core: >65 dBZ */}
              {cell.dbz >= 65 && (
                <CircleMarker
                  center={[currentLat, currentLng]}
                  radius={6}
                  pathOptions={{ fillOpacity: 0.95, fillColor: 'rgba(217, 70, 239, 1)', stroke: false }}
                />
              )}

              {/* Velocity Vector Line */}
              <Polyline 
                positions={[
                  [currentLat, currentLng],
                  [projectedLat, projectedLng]
                ]}
                pathOptions={{
                  color: isSelected ? '#06B6D4' : '#334155',
                  weight: 2,
                  dashArray: '5 5'
                }}
              />

              {/* Glowing Target Centroid */}
              <CircleMarker
                center={[currentLat, currentLng]}
                radius={isSelected ? 6 : 4}
                className="animate-pulse-ring"
                pathOptions={{ color: '#06B6D4', stroke: true, weight: 2, fillOpacity: 0 }}
              />
              <CircleMarker
                center={[currentLat, currentLng]}
                radius={isSelected ? 6 : 4}
                pathOptions={{ color: '#06B6D4', fillColor: '#06B6D4', fillOpacity: 1, stroke: false }}
                eventHandlers={{
                  click: () => setSelectedCell(isSelected ? null : cell.id)
                }}
              >
                <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent={isSelected} className="bg-slate-900 border border-cyan-800 text-cyan-400 font-mono text-xs rounded shadow-[0_0_10px_rgba(6,182,212,0.3)]">
                  <div>TGT: {cell.name}</div>
                  <div>INT: {cell.dbz} dBZ</div>
                </Tooltip>
              </CircleMarker>

              {/* Target bracket [ ] simulated using text layer next to it, or CSS */}

            </div>
          );
        })}
      </MapContainer>
    </div>
  );
}
