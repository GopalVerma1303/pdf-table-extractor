import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import queue
from pdf_table_extractor import PDFTableExtractor


class PDFTableExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Table Extractor")
        self.root.geometry("600x500")
        self.root.minsize(600, 500)

        self.setup_ui()

        # Queue for communication between threads
        self.queue = queue.Queue()
        self.processing = False

        # Start the queue processing
        self.process_queue()

    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Input", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="PDF File or Directory:").grid(
            row=0, column=0, sticky=tk.W, pady=5
        )

        self.input_path_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_path_var, width=50)
        input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        browse_btn = ttk.Button(
            input_frame, text="Browse File", command=self.browse_file
        )
        browse_btn.grid(row=0, column=2, padx=5, pady=5)

        browse_dir_btn = ttk.Button(
            input_frame, text="Browse Directory", command=self.browse_directory
        )
        browse_dir_btn.grid(row=0, column=3, padx=5, pady=5)

        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)

        self.recursive_var = tk.BooleanVar(value=False)
        recursive_check = ttk.Checkbutton(
            options_frame,
            text="Process subdirectories (for directory input)",
            variable=self.recursive_var,
        )
        recursive_check.grid(row=0, column=0, sticky=tk.W, pady=5)

        ttk.Label(options_frame, text="Output Directory:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )

        self.output_path_var = tk.StringVar()
        output_entry = ttk.Entry(
            options_frame, textvariable=self.output_path_var, width=50
        )
        output_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        output_browse_btn = ttk.Button(
            options_frame, text="Browse", command=self.browse_output_directory
        )
        output_browse_btn.grid(row=1, column=2, padx=5, pady=5)

        # Action buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)

        self.extract_btn = ttk.Button(
            buttons_frame, text="Extract Tables", command=self.start_extraction
        )
        self.extract_btn.pack(side=tk.RIGHT, padx=5)

        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create a scrolled text widget for logs
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(fill=tk.X, pady=5)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
        )
        if file_path:
            self.input_path_var.set(file_path)
            # Set default output directory to the same as input file
            if not self.output_path_var.get():
                self.output_path_var.set(os.path.dirname(file_path))

    def browse_directory(self):
        dir_path = filedialog.askdirectory(title="Select Directory with PDF Files")
        if dir_path:
            self.input_path_var.set(dir_path)
            # Set default output directory to the same as input directory
            if not self.output_path_var.get():
                self.output_path_var.set(dir_path)

    def browse_output_directory(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_path_var.set(dir_path)

    def log(self, message):
        self.queue.put(("log", message))

    def update_status(self, message):
        self.queue.put(("status", message))

    def update_progress(self, value):
        self.queue.put(("progress", value))

    def process_queue(self):
        try:
            while True:
                message_type, message = self.queue.get_nowait()

                if message_type == "log":
                    self.log_text.insert(tk.END, message + "\n")
                    self.log_text.see(tk.END)
                elif message_type == "status":
                    self.status_var.set(message)
                elif message_type == "progress":
                    self.progress_var.set(message)
                elif message_type == "complete":
                    self.processing = False
                    self.extract_btn.config(state=tk.NORMAL)
                    messagebox.showinfo("Complete", message)

                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            # Schedule to run again
            self.root.after(100, self.process_queue)

    def start_extraction(self):
        input_path = self.input_path_var.get().strip()
        output_path = self.output_path_var.get().strip()

        if not input_path:
            messagebox.showerror("Error", "Please select a PDF file or directory")
            return

        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Input path does not exist")
            return

        if not output_path:
            # Use input directory as default output
            if os.path.isfile(input_path):
                output_path = os.path.dirname(input_path)
            else:
                output_path = input_path
            self.output_path_var.set(output_path)

        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Disable the extract button during processing
        self.extract_btn.config(state=tk.DISABLED)
        self.processing = True

        # Clear log
        self.log_text.delete(1.0, tk.END)

        # Start extraction in a separate thread
        threading.Thread(target=self.extract_tables, daemon=True).start()

    def extract_tables(self):
        input_path = self.input_path_var.get().strip()
        output_path = self.output_path_var.get().strip()
        recursive = self.recursive_var.get()

        try:
            self.update_status("Processing...")
            self.log(f"Starting extraction from: {input_path}")
            self.log(f"Output directory: {output_path}")

            extractor = PDFTableExtractor()

            if os.path.isfile(input_path):
                # Process single file
                self.log(f"Processing file: {os.path.basename(input_path)}")
                output_file = os.path.join(
                    output_path,
                    f"{os.path.splitext(os.path.basename(input_path))[0]}_tables.xlsx",
                )
                self.update_progress(10)

                tables = extractor.extract_tables_from_pdf(input_path, output_file)

                self.update_progress(100)
                self.log(
                    f"Extraction complete. Extracted {len(tables)} tables to {output_file}"
                )
            else:
                # Process directory
                self.log(f"Processing directory: {input_path}")
                if recursive:
                    self.log("Including subdirectories")

                # Get list of PDF files
                pdf_files = []
                if recursive:
                    for root, _, files in os.walk(input_path):
                        for file in files:
                            if file.lower().endswith(".pdf"):
                                pdf_files.append(os.path.join(root, file))
                else:
                    pdf_files = [
                        os.path.join(input_path, f)
                        for f in os.listdir(input_path)
                        if f.lower().endswith(".pdf")
                        and os.path.isfile(os.path.join(input_path, f))
                    ]

                if not pdf_files:
                    self.log("No PDF files found")
                    self.queue.put(
                        ("complete", "No PDF files found in the selected directory")
                    )
                    return

                self.log(f"Found {len(pdf_files)} PDF files to process")

                # Process each file
                for i, pdf_file in enumerate(pdf_files):
                    progress = int((i / len(pdf_files)) * 100)
                    self.update_progress(progress)

                    rel_path = (
                        os.path.relpath(pdf_file, input_path)
                        if recursive
                        else os.path.basename(pdf_file)
                    )
                    base_name = os.path.splitext(rel_path)[0]
                    output_file = os.path.join(output_path, f"{base_name}_tables.xlsx")

                    self.log(f"Processing ({i+1}/{len(pdf_files)}): {rel_path}")

                    try:
                        extractor.extract_tables_from_pdf(pdf_file, output_file)
                        self.log(f"Completed: {rel_path}")
                    except Exception as e:
                        self.log(f"Error processing {rel_path}: {str(e)}")

                self.update_progress(100)
                self.log("Batch processing complete!")

            self.queue.put(("complete", "Table extraction completed successfully!"))

        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.queue.put(("complete", f"Error during extraction: {str(e)}"))
            self.update_progress(0)
            self.update_status("Error")


def main():
    root = tk.Tk()
    app = PDFTableExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
