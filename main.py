import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

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
        
    def upload_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("STL files", "*.stl")]
        )
        if file_path:
            self.file_label.config(text=Path(file_path).name)
            self.convert_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Ready to convert!")
            
    def convert_to_lego(self):
        # This will be implemented later
        self.status_label.config(text="Conversion feature coming soon!")

if __name__ == "__main__":
    root = tk.Tk()
    app = LegoConverterGUI(root)
    root.mainloop()
