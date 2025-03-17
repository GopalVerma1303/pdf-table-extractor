# PDF Table Extractor

A Python tool to detect and extract tables from system-generated PDFs, storing the extracted data in CSV files. This tool can handle tables with and without borders, as well as irregular shapes, without using Tabula, Camelot, or converting PDFs to images.

## Features

- Extract tables from PDFs using multiple detection algorithms
- Save extracted tables as CSV files (no Excel dependencies)
- Process single PDFs via a user-friendly web interface
- Preview extracted tables before downloading
- Download individual tables or all tables as a ZIP archive
- Special handling for bank statements and financial documents
- Debug mode for troubleshooting extraction issues

## Installation

### Prerequisites

- Python 3.7 or higher

### Setup

1. Clone the repository or download the source code:

```bash
git clone https://github.com/yourusername/pdf-table-extractor.git
cd pdf-table-extractor
```

2. Install the required dependencies:

```
pip install pandas pdfplumber streamlit
```

Thought for 1 second```markdown project="PDF Table Extractor" file="README.md"
...

````

2. Install the required dependencies:


```shellscript
pip install pandas pdfplumber streamlit
````

## Usage

### Web Interface (Recommended)

Run the Streamlit web application:

```shellscript
streamlit run streamlit_app_csv.py
```

This will open a web browser with the application interface where you can:

- Upload PDF files
- Extract tables
- Preview the extracted data
- Download tables as CSV files or as a ZIP archive

### Command Line

You can also use the tool from the command line:

```shellscript
python pdf_table_extractor_csv.py path/to/your/file.pdf --output-dir path/to/output
```

Options:

- `--output-dir` or `-o`: Directory to save the CSV files (optional)
- `--debug` or `-d`: Enable debug output (optional)

## Project Structure

- `pdf_table_extractor_csv.py`: Core extraction logic
- `streamlit_app_csv.py`: Web interface built with Streamlit

## Extraction Methods

The tool uses multiple methods to extract tables:

1. **Built-in pdfplumber extraction**: Uses pdfplumber's table extraction capabilities
2. **Bank statement detection**: Specialized extraction for financial documents
3. **Layout-based extraction**: Analyzes text layout and alignment
4. **Line-based extraction**: Looks for aligned text in lines
5. **Structured data extraction**: Fallback method for any structured data

## Troubleshooting

### Common Issues

1. **No tables detected**:

1. Enable Debug Mode in the sidebar
1. Check if the PDF has security restrictions
1. Try a different PDF to confirm the tool is working

1. **Missing dependencies**:

1. Ensure all required packages are installed:

```shellscript
pip install pandas pdfplumber streamlit
```

3. **File access errors**:

1. Make sure you have write permissions to the output directory
1. Check if any antivirus software is blocking file operations

### Debug Mode

Enable Debug Mode in the sidebar to see detailed logs of the extraction process. This can help identify why tables aren't being detected or extracted correctly.

## Important Commands

### Installation

```shellscript
# Install required packages
pip install pandas pdfplumber streamlit

# If you're using a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install pandas pdfplumber streamlit
```

### Running the Application

```shellscript
# Run the web interface
streamlit run streamlit_app_csv.py

# Run from command line
python pdf_table_extractor_csv.py input.pdf -o output_directory

# Run with debug output
python pdf_table_extractor_csv.py input.pdf -o output_directory -d
```

### Updating Dependencies

```shellscript
# Update all dependencies
pip install --upgrade pandas pdfplumber streamlit
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
