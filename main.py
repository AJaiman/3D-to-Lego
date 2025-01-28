import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from stl_processor import STLReader, Voxelizer
import threading
import queue

class LegoConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STL to LEGO Converter")
        self.root.geometry("600x400")
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('Custom.TButton', padding=10)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            self.main_frame, 
            text="STL to LEGO Converter",
            font=('Helvetica', 16, 'bold')
        )
        title_label.pack(pady=20)
        
        # File selection frame
        self.file_frame = ttk.Frame(self.main_frame)
        self.file_frame.pack(fill=tk.X, pady=20)
        
        self.file_label = ttk.Label(
            self.file_frame,
            text="No file selected",
            font=('Helvetica', 10)
        )
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        self.upload_btn = ttk.Button(
            self.file_frame,
            text="Upload STL",
            style='Custom.TButton',
            command=self.upload_file
        )
        self.upload_btn.pack(side=tk.RIGHT, padx=5)
        
        # Convert button
        self.convert_btn = ttk.Button(
            self.main_frame,
            text="Convert to LEGO!",
            style='Custom.TButton',
            command=self.convert_to_lego,
            state=tk.DISABLED
        )
        self.convert_btn.pack(pady=20)
        
        # Status label
        self.status_label = ttk.Label(
            self.main_frame,
            text="",
            font=('Helvetica', 10)
        )
        self.status_label.pack(pady=10)
        
        self.stl_path = None
        self.processing_queue = queue.Queue()
        
    def upload_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("STL files", "*.stl")]
        )
        if file_path:
            self.stl_path = file_path
            self.file_label.config(text=Path(file_path).name)
            self.convert_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Ready to convert!")
            
    def process_in_background(self):
        try:
            # Read STL
            reader = STLReader(self.stl_path)
            mesh = reader.read()
            
            # Calculate optimal resolution
            resolution = reader.calculate_optimal_voxel_resolution()
            
            # Update status via queue
            self.processing_queue.put(("status", "Voxelizing model...\nThis may take a few minutes for large models."))
            
            # Voxelize
            voxelizer = Voxelizer(mesh, resolution)
            voxels = voxelizer.voxelize()
            
            # Save voxels
            output_path = Path(self.stl_path).with_suffix('.npy')
            voxelizer.save_to_file(output_path)
            
            # Signal completion
            self.processing_queue.put(("complete", f"Voxelization complete!\nSaved to: {output_path.name}"))
            
        except Exception as e:
            self.processing_queue.put(("error", str(e)))
    
    def check_queue(self):
        try:
            msg_type, message = self.processing_queue.get_nowait()
            
            if msg_type == "complete":
                self.status_label.config(text=message)
                self.progress_bar.stop()
                self.progress_bar.destroy()
                self.convert_btn.config(state=tk.NORMAL)
            elif msg_type == "error":
                self.status_label.config(text=f"Error: {message}")
                self.progress_bar.stop()
                self.progress_bar.destroy()
                self.convert_btn.config(state=tk.NORMAL)
            elif msg_type == "status":
                self.status_label.config(text=message)
                
        except queue.Empty:
            pass
        
        if hasattr(self, 'progress_bar'):
            self.root.after(100, self.check_queue)
            
    def convert_to_lego(self):
        if not self.stl_path:
            return
            
        # Disable convert button during processing
        self.convert_btn.config(state=tk.DISABLED)
        
        # Add progress bar
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            orient='horizontal',
            length=300,
            mode='indeterminate'
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()
        
        self.status_label.config(text="Reading STL file...")
        
        # Start processing in background thread
        processing_thread = threading.Thread(
            target=self.process_in_background,
            daemon=True
        )
        processing_thread.start()
        
        # Start checking for updates
        self.root.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = LegoConverterGUI(root)
    root.mainloop()
