export function renderVilGrid(canvas: HTMLCanvasElement, values: number[][]) {
  const height = values.length;
  const width = values[0]?.length ?? 0;
  if (!height || !width) return;

  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return;

  const image = context.createImageData(width, height);
  let pixel = 0;
  for (const row of values) {
    for (const value of row) {
      const [red, green, blue, alpha] = colorForVil(value);
      image.data[pixel++] = red;
      image.data[pixel++] = green;
      image.data[pixel++] = blue;
      image.data[pixel++] = alpha;
    }
  }
  context.putImageData(image, 0, 0);
}

function colorForVil(value: number): [number, number, number, number] {
  if (value < 16) return [2, 6, 23, 255];
  if (value < 64) return [8, 145, 178, 180];
  if (value < 112) return [0, 240, 255, 220];
  if (value < 160) return [57, 255, 20, 235];
  if (value < 208) return [250, 204, 21, 245];
  return [255, 0, 60, 255];
}
