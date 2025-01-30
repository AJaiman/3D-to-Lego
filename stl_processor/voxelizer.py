import numpy as np
from scipy import ndimage
from pathlib import Path
from stl import mesh

class Voxelizer:
    def __init__(self, mesh, resolution):
        self.mesh = mesh
        self.resolution = resolution
        self.voxels = None
        
    def voxelize(self):
        """Convert mesh to voxels using a surface-based approach"""
        # Create a 3D grid
        grid = np.zeros((self.resolution, self.resolution, self.resolution), dtype=bool)
        
        # Get all triangles from the mesh
        triangles = self.mesh.vectors
        
        # Get model bounds
        min_coords = triangles.min(axis=(0, 1))
        max_coords = triangles.max(axis=(0, 1))
        
        # Calculate scaling factor with additional padding
        scale = (self.resolution - 4) / np.max(max_coords - min_coords)  # Increased padding
        
        # Vectorized triangle processing
        verts = (triangles - min_coords) * scale
        verts = np.clip(verts, 0, self.resolution - 4)  # Adjusted clipping
        
        # Process triangles in smaller batches for better memory management
        batch_size = 500  # Reduced batch size for higher resolution
        for i in range(0, len(triangles), batch_size):
            batch_triangles = triangles[i:i + batch_size]
            batch_verts = verts[i:i + batch_size]
            
            # Get bounds for all triangles in batch
            mins = np.floor(np.min(batch_verts, axis=1)).astype(int)
            maxs = np.ceil(np.max(batch_verts, axis=1)).astype(int)
            
            # Process each triangle in batch
            for triangle, triangle_mins, triangle_maxs in zip(batch_triangles, mins, maxs):
                x_range = range(max(0, triangle_mins[0]), min(self.resolution - 1, triangle_maxs[0] + 1))
                y_range = range(max(0, triangle_mins[1]), min(self.resolution - 1, triangle_maxs[1] + 1))
                z_range = range(max(0, triangle_mins[2]), min(self.resolution - 1, triangle_maxs[2] + 1))
                
                if not (x_range and y_range and z_range):
                    continue
                
                # Create mesh grid for points with optimized sampling density
                x, y, z = np.meshgrid(x_range, y_range, z_range, indexing='ij')
                points = np.stack([x, y, z], axis=-1).reshape(-1, 3)
                
                # Optimized sub-voxel sampling points
                offsets = np.array([[dx, dy, dz] 
                                  for dx in [0.25, 0.5, 0.75]  # Simplified sampling points
                                  for dy in [0.25, 0.5, 0.75]
                                  for dz in [0.25, 0.5, 0.75]])
                
                points = points[:, None] + offsets
                points = points.reshape(-1, 3)
                
                # Convert to original coordinate system
                points = points / scale + min_coords
                
                # Vectorized point-triangle distance check
                mask = self._points_near_triangle_vectorized(points, triangle, threshold=0.25)  # Adjusted threshold
                mask = mask.reshape(-1, 27).any(axis=1)  # Adjusted for new sampling count
                
                if mask.any():
                    indices = (points[::27][mask] - min_coords) * scale
                    indices = np.clip(indices, 0, self.resolution - 1).astype(int)
                    grid[indices[:, 0], indices[:, 1], indices[:, 2]] = True
        
        # Enhanced surface processing and filling
        struct = np.ones((3, 3, 3))
        grid = ndimage.binary_dilation(grid, structure=struct, iterations=1)
        
        # Fill internal volumes
        filled_grid = ndimage.binary_fill_holes(grid)
        
        # Optimized smoothing passes
        for _ in range(2):
            filled_grid = ndimage.binary_closing(filled_grid, structure=struct, iterations=1)
            filled_grid = ndimage.binary_dilation(filled_grid, structure=struct, iterations=1)
            filled_grid = ndimage.binary_erosion(filled_grid, structure=struct, iterations=1)
        
        # Remove floating voxels
        self._remove_floating_voxels(filled_grid)
        
        self.voxels = filled_grid
        return self.voxels
    
    def _remove_floating_voxels(self, grid):
        """Remove voxels that aren't connected to the main structure"""
        # Label connected components
        labeled_array, num_features = ndimage.label(grid)
        
        if num_features == 0:
            return
        
        # Find the largest component
        sizes = np.bincount(labeled_array.ravel())
        sizes[0] = 0  # Ignore background
        largest_component = sizes.argmax()
        
        # Keep only the largest component
        grid[:] = (labeled_array == largest_component)

    def _points_near_triangle_vectorized(self, points, triangle, threshold=0.3):
        """Vectorized version of point-triangle distance check with adjusted threshold"""
        # Calculate triangle normal
        v1 = triangle[1] - triangle[0]
        v2 = triangle[2] - triangle[0]
        normal = np.cross(v1, v2)
        normal_length = np.linalg.norm(normal)
        
        if normal_length < 1e-10:
            return np.zeros(len(points), dtype=bool)
        
        normal = normal / normal_length
        
        # Calculate distances from points to triangle plane
        v = points - triangle[0]
        dists = np.abs(np.dot(v, normal))
        
        # Early exit for points too far from plane
        mask = dists <= threshold
        if not mask.any():
            return np.zeros(len(points), dtype=bool)
        
        # Project points onto triangle plane
        close_points = points[mask]
        proj = close_points - dists[mask, None] * normal
        
        # Check if projections are inside triangle or near edges
        edge0 = triangle[1] - triangle[0]
        edge1 = triangle[2] - triangle[1]
        edge2 = triangle[0] - triangle[2]
        
        C0 = proj - triangle[0]
        C1 = proj - triangle[1]
        C2 = proj - triangle[2]
        
        # Vectorized inside-triangle test
        inside = (np.dot(np.cross(edge0, C0), normal) >= -threshold) & \
                (np.dot(np.cross(edge1, C1), normal) >= -threshold) & \
                (np.dot(np.cross(edge2, C2), normal) >= -threshold)
        
        result = np.zeros(len(points), dtype=bool)
        result[mask] = inside
        return result
    
    def _create_cube_faces(self, x, y, z):
        """Create faces for a single voxel cube"""
        # Define the 8 vertices of a unit cube
        v = np.array([
            [x, y, z],         # 0
            [x+1, y, z],       # 1
            [x+1, y+1, z],     # 2
            [x, y+1, z],       # 3
            [x, y, z+1],       # 4
            [x+1, y, z+1],     # 5
            [x+1, y+1, z+1],   # 6
            [x, y+1, z+1]      # 7
        ], dtype=float)
        
        # Define the 12 triangles (6 faces, 2 triangles each)
        faces = np.array([
            [0,3,1], [1,3,2],  # bottom
            [0,1,5], [0,5,4],  # front
            [1,2,6], [1,6,5],  # right
            [2,3,7], [2,7,6],  # back
            [3,0,4], [3,4,7],  # left
            [4,5,6], [4,6,7]   # top
        ])
        
        return v, faces
    
    def save_to_file(self, output_path: str):
        """Save voxels as both NPY and voxelized STL"""
        if self.voxels is None:
            raise ValueError("Must voxelize before saving")
            
        output_path = Path(output_path)
        
        # Save NPY file
        np.save(output_path, self.voxels)
        
        # Create voxelized STL
        vertices_list = []
        faces_list = []
        vertex_count = 0
        
        # Convert each voxel to cube faces
        for z in range(self.resolution):
            for y in range(self.resolution):
                for x in range(self.resolution):
                    if self.voxels[x, y, z]:
                        v, f = self._create_cube_faces(x, y, z)
                        vertices_list.append(v)
                        faces_list.append(f + vertex_count)
                        vertex_count += len(v)
        
        if vertices_list:  # Only create STL if we have voxels
            # Combine all vertices and faces
            vertices = np.vstack(vertices_list)
            faces = np.vstack(faces_list)
            
            # Scale vertices back to original size
            scale = (self.mesh.vectors.max() - self.mesh.vectors.min()) / self.resolution
            vertices = vertices * scale + self.mesh.vectors.min()
            
            # Create mesh
            voxel_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
            for i, face in enumerate(faces):
                for j in range(3):
                    voxel_mesh.vectors[i][j] = vertices[face[j]]
            
            # Save voxelized STL
            stl_path = output_path.parent / f"{output_path.stem}_voxelized.stl"
            voxel_mesh.save(stl_path)
