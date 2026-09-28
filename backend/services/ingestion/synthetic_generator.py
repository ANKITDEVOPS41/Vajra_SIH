import numpy as np

class SyntheticGenerator:
    def __init__(self, grid_size=(256, 256)):
        self.grid_size = grid_size
        
        # Center coordinates mapping roughly to Uttarakhand/Himalayan belt footprint
        # Just an abstraction on a 256x256 pixel grid
        self.center_x = grid_size[0] // 2
        self.center_y = grid_size[1] // 2

    def generate_events(self, num_frames=18):
        """
        Generates 18 time slices covering T-3h to T+6h (if every frame is 30 mins, 18 frames=9 hours).
        Values in range 0 - 70 dBZ to mimic convection initiation.
        """
        frames = []
        for i in range(num_frames):
            frame = np.zeros(self.grid_size, dtype=np.float32)
            
            # Start with some ambient noise (0-10 dBZ)
            noise = np.random.uniform(0, 10, self.grid_size)
            frame += noise

            # Simulate a convective cell growing and moving across frames
            # Movement: to the North-East (increment x and y)
            offset_x = (i - num_frames//2) * 4
            offset_y = (i - num_frames//2) * 3

            cell_radius = 15 + i * 2 # cell grows over time
            intensity = min(70, 20 + i * 4) # tops out at 70 dBZ
            
            y, x = np.ogrid[-self.center_y:self.grid_size[0]-self.center_y, -self.center_x:self.grid_size[1]-self.center_x]
            
            # Shift the center to simulate movement
            mask = (x - offset_x)**2 + (y - offset_y)**2 <= cell_radius**2
            
            # Add Gaussian-like intense core
            core_dist = np.sqrt((x - offset_x)**2 + (y - offset_y)**2)
            cell_intensity = np.where(mask, intensity * (1 - core_dist / (cell_radius + 1e-5)), 0)
            
            frame = np.maximum(frame, cell_intensity)
            # Clip between 0 and 70 dBZ
            frame = np.clip(frame, 0, 70)
            frames.append(frame)
            
        return frames

if __name__ == "__main__":
    generator = SyntheticGenerator()
    frames = generator.generate_events()
    print(len(frames))
    print(frames[8].max())
