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
        
        # Calculate scaling factor
        scale = (self.resolution - 1) / np.max(max_coords - min_coords)
        
        # Process each triangle with higher sampling
        for triangle in triangles:
            # Scale and translate vertices to voxel coordinates
            verts = (triangle - min_coords) * scale
            verts = np.clip(verts, 0, self.resolution - 1)
            
            # Get triangle bounds with padding for better surface capture
            mins = np.min(verts, axis=0).astype(int) - 1
            maxs = np.max(verts, axis=0).astype(int) + 2
            
            # Sample points more densely around the triangle
            for x in range(max(0, mins[0]), min(self.resolution, maxs[0])):
                for y in range(max(0, mins[1]), min(self.resolution, maxs[1])):
                    for z in range(max(0, mins[2]), min(self.resolution, maxs[2])):
                        # Check multiple points within each voxel for better surface detection
                        for dx in [0.25, 0.75]:
                            for dy in [0.25, 0.75]:
                                for dz in [0.25, 0.75]:
                                    point = np.array([x + dx, y + dy, z + dz]) / scale + min_coords
                                    if self._point_near_triangle(point, triangle, threshold=0.4):
                                        grid[x, y, z] = True
        
        # Connect nearby voxels and smooth the surface
        struct = np.ones((3, 3, 3))
        
        # Multiple passes of dilation and erosion to better capture rounded surfaces
        grid = ndimage.binary_dilation(grid, structure=struct, iterations=1)
        grid = ndimage.binary_fill_holes(grid)
        grid = ndimage.binary_closing(grid, structure=struct, iterations=1)
        
        # Remove floating voxels
        self._remove_floating_voxels(grid)
        
        self.voxels = grid
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

    def _point_near_triangle(self, point, triangle, threshold=0.4):
        """Check if a point is near a triangle"""
        # Calculate triangle normal
        v1 = triangle[1] - triangle[0]
        v2 = triangle[2] - triangle[0]
        normal = np.cross(v1, v2)
        normal_length = np.linalg.norm(normal)
        
        if normal_length < 1e-10:
            return False
        
        normal = normal / normal_length
        
        # Calculate distance from point to triangle plane
        v = point - triangle[0]
        dist = abs(np.dot(v, normal))
        
        if dist > threshold:
            return False
        
        # Project point onto triangle plane
        proj = point - dist * normal
        
        # Check if projection is inside triangle or near edges
        edge0 = triangle[1] - triangle[0]
        edge1 = triangle[2] - triangle[1]
        edge2 = triangle[0] - triangle[2]
        C0 = proj - triangle[0]
        C1 = proj - triangle[1]
        C2 = proj - triangle[2]
        
        # Check if point is inside triangle or close to edges
        if (np.dot(np.cross(edge0, C0), normal) >= -threshold and
            np.dot(np.cross(edge1, C1), normal) >= -threshold and
            np.dot(np.cross(edge2, C2), normal) >= -threshold):
            return True
        
        # Check distance to edges
        for i in range(3):
            p1 = triangle[i]
            p2 = triangle[(i + 1) % 3]
            edge = p2 - p1
            edge_length = np.linalg.norm(edge)
            if edge_length > 0:
                t = max(0, min(1, np.dot(point - p1, edge) / edge_length**2))
                closest = p1 + t * edge
                if np.linalg.norm(point - closest) < threshold:
                    return True
        
        return False
    
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
