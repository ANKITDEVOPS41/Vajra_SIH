import { useEffect, useMemo, useState } from "react";
import { ImageOverlay } from "react-leaflet";
import type { RadarFrame } from "../types/workspaces";

function rasterUrl(frame: RadarFrame): string {
  const canvas = document.createElement("canvas");
  canvas.width = frame.width;
  canvas.height = frame.height;
  const context = canvas.getContext("2d");
  if (!context) return "";
  const image = context.createImageData(frame.width, frame.height);
  frame.values.forEach((row, y) => row.forEach((value, x) => {
    const index = (y * frame.width + x) * 4;
    if (value < 10) return;
    const color = value >= 50 ? [232, 82, 93] : value >= 40 ? [242, 171, 75] : value >= 30 ? [76, 212, 173] : [56, 168, 220];
    image.data.set([...color, Math.min(220, Math.round(value * 3.5))], index);
  }));
  context.putImageData(image, 0, 0);
  return canvas.toDataURL("image/png");
}

export function useRadarFrame(offsetMinutes: number | null) {
  const [frame, setFrame] = useState<RadarFrame | null>(null);
  const [status, setStatus] = useState("LOADING");
  useEffect(() => {
    if (offsetMinutes === null) return;
    let cancelled = false;
    fetch(`/api/v1/replay/observed-radar/${offsetMinutes}`)
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 404 ? "NO OBSERVATION AT THIS LEAD" : "RADAR REPLAY UNAVAILABLE");
        return response.json() as Promise<RadarFrame>;
      })
      .then((data) => { if (!cancelled) { setFrame(data); setStatus("SIMULATED REPLAY"); } })
      .catch((error: unknown) => { if (!cancelled) { setFrame(null); setStatus(error instanceof Error ? error.message : "RADAR REPLAY UNAVAILABLE"); } });
    return () => { cancelled = true; };
  }, [offsetMinutes]);
  return { frame, status };
}

export function RadarFieldLayer({ frame, opacity }: { frame: RadarFrame | null; opacity: number }) {
  const url = useMemo(() => frame ? rasterUrl(frame) : "", [frame]);
  if (!frame || !url) return null;
  return <ImageOverlay url={url} bounds={[[frame.southwest.lat, frame.southwest.lon], [frame.northeast.lat, frame.northeast.lon]]} opacity={opacity} />;
}
