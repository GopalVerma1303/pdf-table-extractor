import os
import argparse
from pdf_table_extractor import PDFTableExtractor

def process_directory(input_dir, output_dir=None, recursive=False):
    """
    Process all PDF files in a directory
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save Excel files (defaults to input_dir)
        recursive: Whether to process subdirectories
    """
    if output_dir is None:
        output_dir = input_dir
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of PDF files
    pdf_files = []
    if recursive:
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    else:
        pdf_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                    if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(input_dir, f))]
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF file
    extractor = PDFTableExtractor()
    for pdf_file in pdf_files:
        # Determine output path
        rel_path = os.path.relpath(pdf_file, input_dir) if recursive else os.path.basename(pdf_file)
        base_name = os.path.splitext(rel_path)[0]
        output_path = os.path.join(output_dir, f"{base_name}_tables.xlsx")
        
        # Extract tables
        try:
              f"{base_name}_tables.xlsx")
        
        # Extract tables
        try:
            print(f"\nProcessing: {pdf_file}")
            extractor.extract_tables_from_pdf(pdf_file, output_path)
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
    
    print("\nBatch processing complete!")

def main():
    parser = argparse.ArgumentParser(description='Process multiple PDF files and extract tables')
    parser.add_argument('input_dir', help='Directory containing PDF files')
    parser.add_argument('--output-dir', '-o', help='Directory to save Excel files')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process subdirectories')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir, args.recursive)

if __name__ == "__main__":
    main()
