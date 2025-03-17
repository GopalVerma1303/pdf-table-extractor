# PDF Table Extractor

A tool to detect and extract tables from system-generated PDFs without using Tabula, Camelot, or converting the PDF into images. The extracted tables are stored in Excel sheets.

## Features

- Extracts tables from PDFs with or without borders
- Handles irregular-shaped tables
- Supports bank statements and other document types
- Exports tables to Excel format
- Provides both command-line and Streamlit web interfaces
- Batch processing capability for multiple PDFs

## Requirements

- Python 3.7 or higher
- Required Python packages:
  - pdfplumber
  - pandas
  - openpyxl
  - streamlit (for web interface)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install pdfplumber pandas openpyxl streamlit
```

