"""
GUI application for md2docx converter.
Provides visual interface for file conversion with history tracking.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict
import threading

from md2docx import Converter


class Md2docxGUI:
    """Graphical user interface for md2docx converter."""
    
    def __init__(self, root):
        """Initialize GUI application."""
        self.root = root
        self.root.title("Markdown to Word Converter")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # History file path
        self.history_file = Path.home() / ".md2docx" / "history.json"
        self.history_file.parent.mkdir(exist_ok=True)
        
        # Load history
        self.history = self.load_history()
        
        # Setup UI
        self.setup_ui()
        
        # Load history into list
        self.refresh_history_list()
    
    def setup_ui(self):
        """Setup user interface components."""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="📄 Markdown to Word Converter",
            font=("Helvetica", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky=tk.W)
        
        # Conversion section
        self.setup_conversion_section(main_frame)
        
        # History section
        self.setup_history_section(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def setup_conversion_section(self, parent):
        """Setup file selection and conversion controls."""
        # Frame for conversion
        conv_frame = ttk.LabelFrame(parent, text="File Conversion", padding="10")
        conv_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        conv_frame.columnconfigure(1, weight=1)
        
        # Input file
        ttk.Label(conv_frame, text="Markdown File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_var = tk.StringVar()
        input_entry = ttk.Entry(conv_frame, textvariable=self.input_var, width=50)
        input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        browse_btn = ttk.Button(
            conv_frame, 
            text="Browse...", 
            command=self.browse_input_file,
            width=12
        )
        browse_btn.grid(row=0, column=2, padx=5)
        
        # Output file
        ttk.Label(conv_frame, text="Output File:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(conv_frame, textvariable=self.output_var, width=50)
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        output_btn = ttk.Button(
            conv_frame, 
            text="Save As...", 
            command=self.browse_output_file,
            width=12
        )
        output_btn.grid(row=1, column=2, padx=5)
        
        # Convert button
        convert_btn = ttk.Button(
            conv_frame,
            text="🔄 Convert to Word",
            command=self.convert_file,
            style="Accent.TButton"
        )
        convert_btn.grid(row=2, column=1, pady=(15, 0), sticky=tk.E)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            conv_frame, 
            mode='indeterminate',
            length=200
        )
        self.progress.grid(row=2, column=0, pady=(15, 0), sticky=(tk.W, tk.E))
    
    def setup_history_section(self, parent):
        """Setup history list display."""
        # Frame for history
        history_frame = ttk.LabelFrame(parent, text="Conversion History", padding="10")
        history_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        # Treeview for history
        columns = ("Time", "Input", "Output", "Status")
        self.history_tree = ttk.Treeview(
            history_frame,
            columns=columns,
            show="headings",
            height=10
        )
        
        # Configure columns
        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("Input", text="Input File")
        self.history_tree.heading("Output", text="Output File")
        self.history_tree.heading("Status", text="Status")
        
        self.history_tree.column("Time", width=150)
        self.history_tree.column("Input", width=250)
        self.history_tree.column("Output", width=250)
        self.history_tree.column("Status", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(
            history_frame,
            orient=tk.VERTICAL,
            command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Buttons
        btn_frame = ttk.Frame(history_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(
            btn_frame,
            text="🔄 Reload Selected",
            command=self.reload_from_history
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Clear History",
            command=self.clear_history
        ).pack(side=tk.LEFT, padx=5)
        
        # Double-click to load
        self.history_tree.bind("<Double-1>", lambda e: self.reload_from_history())
    
    def browse_input_file(self):
        """Open file dialog to select input Markdown file."""
        filename = filedialog.askopenfilename(
            title="Select Markdown File",
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.input_var.set(filename)
            # Auto-suggest output filename
            input_path = Path(filename)
            output_path = input_path.with_suffix('.docx')
            self.output_var.set(str(output_path))
    
    def browse_output_file(self):
        """Open file dialog to select output Word file."""
        filename = filedialog.asksaveasfilename(
            title="Save Word Document As",
            defaultextension=".docx",
            filetypes=[
                ("Word documents", "*.docx"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.output_var.set(filename)
    
    def convert_file(self):
        """Convert Markdown file to Word document."""
        input_file = self.input_var.get()
        output_file = self.output_var.get()
        
        # Validate inputs
        if not input_file:
            messagebox.showerror("Error", "Please select an input Markdown file.")
            return
        
        if not output_file:
            messagebox.showerror("Error", "Please specify an output file path.")
            return
        
        if not Path(input_file).exists():
            messagebox.showerror("Error", f"Input file not found:\n{input_file}")
            return
        
        # Run conversion in background thread
        thread = threading.Thread(target=self._do_conversion, args=(input_file, output_file))
        thread.daemon = True
        thread.start()
    
    def _do_conversion(self, input_file: str, output_file: str):
        """Perform actual conversion (runs in background thread)."""
        try:
            # Update UI
            self.root.after(0, self.progress.start)
            self.root.after(0, lambda: self.status_var.set("Converting..."))
            
            # Convert
            converter = Converter()
            converter.convert(input_file, output_file)
            
            # Add to history
            self.add_to_history(input_file, output_file, "Success")
            
            # Update UI
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.status_var.set(f"✓ Conversion successful: {output_file}"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"File converted successfully!\n\nOutput: {output_file}"
            ))
            self.root.after(0, self.refresh_history_list)
            
        except Exception as e:
            # Add to history with error
            self.add_to_history(input_file, output_file, f"Failed: {str(e)}")
            
            # Update UI
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.status_var.set(f"✗ Conversion failed"))
            self.root.after(0, lambda: messagebox.showerror(
                "Conversion Error",
                f"Failed to convert file:\n\n{str(e)}"
            ))
            self.root.after(0, self.refresh_history_list)
    
    def load_history(self) -> List[Dict]:
        """Load conversion history from JSON file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_history(self):
        """Save conversion history to JSON file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def add_to_history(self, input_file: str, output_file: str, status: str):
        """Add conversion record to history."""
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input": input_file,
            "output": output_file,
            "status": status
        }
        
        # Add to beginning of list (most recent first)
        self.history.insert(0, record)
        
        # Keep only last 100 records
        self.history = self.history[:100]
        
        # Save to file
        self.save_history()
    
    def refresh_history_list(self):
        """Refresh history display in treeview."""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Add history items
        for record in self.history:
            # Shorten file paths for display
            input_short = Path(record["input"]).name
            output_short = Path(record["output"]).name
            
            self.history_tree.insert(
                "",
                tk.END,
                values=(
                    record["time"],
                    input_short,
                    output_short,
                    record["status"]
                ),
                tags=(record["status"],)
            )
        
        # Configure tags for color coding
        self.history_tree.tag_configure("Success", foreground="green")
        self.history_tree.tag_configure("Failed", foreground="red")
    
    def reload_from_history(self):
        """Load selected history item into input fields."""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a history item first.")
            return
        
        # Get selected index
        item = selection[0]
        index = self.history_tree.index(item)
        
        if index < len(self.history):
            record = self.history[index]
            self.input_var.set(record["input"])
            self.output_var.set(record["output"])
            self.status_var.set(f"Loaded from history: {record['time']}")
    
    def clear_history(self):
        """Clear all conversion history."""
        if messagebox.askyesno(
            "Confirm Clear History",
            "Are you sure you want to clear all conversion history?"
        ):
            self.history = []
            self.save_history()
            self.refresh_history_list()
            self.status_var.set("History cleared")


def main():
    """Main entry point for GUI application."""
    root = tk.Tk()
    app = Md2docxGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
