import numpy as np
from stl import mesh
from pathlib import Path

class STLReader:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.mesh = None
        self.scale = 1.0
        
    def read(self):
        """Read the STL file and return the mesh"""
        self.mesh = mesh.Mesh.from_file(str(self.file_path))
        return self.mesh
    
    def get_dimensions(self):
        """Get the dimensions of the mesh"""
        if self.mesh is None:
            self.read()
            
        minx = min(self.mesh.x.flatten())
        maxx = max(self.mesh.x.flatten())
        miny = min(self.mesh.y.flatten())
        maxy = max(self.mesh.y.flatten())
        minz = min(self.mesh.z.flatten())
        maxz = max(self.mesh.z.flatten())
        
        return {
            'x': (minx, maxx),
            'y': (miny, maxy),
            'z': (minz, maxz)
        }
    
    def calculate_optimal_voxel_resolution(self):
        """Calculate optimal voxel resolution based on model size"""
        dims = self.get_dimensions()
        
        # Calculate model dimensions
        size_x = dims['x'][1] - dims['x'][0]
        size_y = dims['y'][1] - dims['y'][0]
        size_z = dims['z'][1] - dims['z'][0]
        
        # Get the largest dimension
        max_size = max(size_x, size_y, size_z)
        
        # Calculate resolution based on model size
        # Increased base resolution for higher detail
        base_resolution = 128  # Increased from 64 to 128
        
        # Adjust based on model complexity with optimized factor
        vertex_count = len(self.mesh.vectors.reshape(-1, 3))
        complexity_factor = min(1.5, max(1.0, np.log10(vertex_count) / 5))  # Adjusted scaling factor
        
        target_resolution = int(base_resolution * complexity_factor)
        
        # Ensure resolution is even for better LEGO conversion later
        target_resolution = (target_resolution // 2) * 2
        
        # Calculate scale to achieve target size
        self.scale = target_resolution / max_size
        
        return target_resolution
