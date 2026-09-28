/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', "Liberation Mono", "Courier New", 'monospace'],
      },
      colors: {
        slate: {
          800: '#1e293b',
          900: '#0B0F19', // Obsidian Slate
        },
        cyan: {
          400: '#06B6D4', // Tactical Cyan
        }
      }
    },
  },
  plugins: [],
}
