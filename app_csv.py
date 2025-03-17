import streamlit as st
import os
import pandas as pd
import tempfile
import time
import base64
import io
import logging
import sys
import shutil
from pdf_table_extractor_csv import PDFTableExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="PDF Table Extractor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Create a persistent temporary directory for this session
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
    logger.info(f"Created persistent temporary directory: {st.session_state.temp_dir}")


def get_download_link(file_path, link_text):
    """Generate a download link for a file"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()

        # Determine MIME type based on file extension
        if file_path.endswith(".csv"):
            mime = "text/csv"
        elif file_path.endswith(".zip"):
            mime = "application/zip"
        else:
            mime = "application/octet-stream"

        href = f'<a href="data:{mime};base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
        return href
    except Exception as e:
        logger.error(f"Error creating download link for {file_path}: {str(e)}")
        return f"<span style='color:red'>Error creating download link: {str(e)}</span>"


def process_single_pdf(pdf_file):
    """Process a single PDF file and return the extracted tables"""
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(pdf_file.getbuffer())
        pdf_path = tmp_pdf.name

    # Use the persistent temporary directory
    output_dir = st.session_state.temp_dir

    # Create a unique subdirectory for this file
    file_dir = os.path.join(output_dir, f"extract_{int(time.time())}")
    os.makedirs(file_dir, exist_ok=True)

    # Extract tables
    extractor = PDFTableExtractor()
    extractor.debug = st.session_state.get("debug", False)

    try:
        # Add log capture
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.DEBUG if extractor.debug else logging.INFO)
        logger.addHandler(log_handler)

        # Extract tables
        results = extractor.extract_tables_from_pdf(pdf_path, file_dir)

        # Get logs
        log_handler.flush()
        logs = log_capture.getvalue()
        logger.removeHandler(log_handler)

        # Clean up the temporary PDF file
        os.unlink(pdf_path)

        # Verify files exist
        for result in results:
            if "path" in result:
                if not os.path.exists(result["path"]):
                    logger.error(f"File does not exist: {result['path']}")
                else:
                    logger.info(f"File exists: {result['path']}")

        return results, logs
    except Exception as e:
        # Clean up the temporary PDF file
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        logger.error(f"Error in process_single_pdf: {str(e)}")
        raise e


def main():
    st.title("PDF Table Extractor (CSV Version)")
    st.markdown(
        """
    Extract tables from PDFs without using Tabula, Camelot, or converting to images.
    This tool can handle tables with or without borders and irregular shapes.
    
    **This version saves tables as CSV files to avoid openpyxl dependency issues.**
    """
    )

    # Check for required packages
    missing_packages = []
    for package in ["pandas", "pdfplumber"]:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        st.error(f"Missing required packages: {', '.join(missing_packages)}")
        st.info("Please install the missing packages using pip:")
        st.code(f"pip install {' '.join(missing_packages)}")
        return

    # Display Python environment info
    with st.expander("Environment Information", expanded=False):
        st.write(f"Python version: {sys.version}")
        st.write(f"Pandas version: {pd.__version__}")
        try:
            import pdfplumber

            st.write(f"pdfplumber version: {pdfplumber.__version__}")
        except:
            st.write("pdfplumber: Not available")

        # Show temp directory
        st.write(f"Temporary directory: {st.session_state.temp_dir}")

    # Initialize session state for logs
    if "logs" not in st.session_state:
        st.session_state.logs = []

    # Sidebar options
    st.sidebar.header("Options")

    # Debug mode
    st.session_state.debug = st.sidebar.checkbox("Debug Mode", value=False)

    # Input method selection
    input_method = st.sidebar.radio(
        "Select Input Method", ["Upload PDF File", "Process Directory (Local)"]
    )

    # Main content area
    if input_method == "Upload PDF File":
        st.header("Upload PDF File")

        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")

            # Process button
            if st.button("Extract Tables"):
                with st.spinner("Extracting tables..."):
                    try:
                        # Process the PDF
                        results, logs = process_single_pdf(uploaded_file)

                        # Display logs
                        with st.expander("Processing Logs", expanded=False):
                            st.text(logs)

                        if results:
                            # Filter out the ZIP file
                            tables = [r for r in results if not r.get("is_zip", False)]
                            zip_file = next(
                                (r for r in results if r.get("is_zip", False)), None
                            )

                            st.success(f"Successfully extracted {len(tables)} tables!")

                            # Display download links
                            st.subheader("Download Options")

                            if zip_file:
                                if os.path.exists(zip_file["path"]):
                                    st.markdown(
                                        get_download_link(
                                            zip_file["path"],
                                            "📥 Download All Tables (ZIP)",
                                        ),
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.error(f"ZIP file not found: {zip_file['path']}")

                            for table_info in tables:
                                if "path" in table_info and os.path.exists(
                                    table_info["path"]
                                ):
                                    st.markdown(
                                        get_download_link(
                                            table_info["path"],
                                            f"📥 Download {table_info['name']} (CSV)",
                                        ),
                                        unsafe_allow_html=True,
                                    )
                                elif "path" in table_info:
                                    st.error(
                                        f"CSV file not found: {table_info['path']}"
                                    )

                            # Preview tables
                            st.subheader("Table Preview")
                            for i, table_info in enumerate(tables):
                                if "data" in table_info:
                                    with st.expander(
                                        f"Table {i+1}: {table_info['name']}",
                                        expanded=i == 0,
                                    ):
                                        st.dataframe(table_info["data"])
                        else:
                            st.warning("No tables were detected in the document.")
                            st.info(
                                "Try enabling Debug Mode in the sidebar for more information."
                            )
                    except Exception as e:
                        st.error(f"Error extracting tables: {str(e)}")
                        st.info(
                            "Check the Environment Information section to verify all required packages are installed."
                        )

    else:  # Process Directory
        st.header("Process Directory")

        # Directory path input
        dir_path = st.text_input("Enter directory path containing PDF files:")

        # Options
        col1, col2 = st.columns(2)
        with col1:
            recursive = st.checkbox("Process subdirectories", value=False)
        with col2:
            output_dir = st.text_input(
                "Output directory (leave empty to use input directory):"
            )

        if not output_dir:
            output_dir = None

        # Process button
        if st.button("Process Directory"):
            if not dir_path or not os.path.isdir(dir_path):
                st.error("Please enter a valid directory path.")
            else:
                st.warning(
                    "Directory processing is disabled in this version due to package compatibility issues."
                )
                st.info("Please process PDF files individually by uploading them.")

    # Tips section
    st.sidebar.header("Tips")
    st.sidebar.markdown(
        """
    - This version saves tables as CSV files to avoid Excel dependency issues
    - Enable Debug Mode to see detailed extraction logs
    - For bank statements, the tool has specialized extraction logic
    - Some PDFs may require pre-processing if they use unusual formatting
    """
    )


if __name__ == "__main__":
    main()
