import streamlit as st
import os
import pandas as pd
import tempfile
import time
import base64
import io
import logging
from pdf_table_extractor import PDFTableExtractor

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


def get_download_link(file_path, link_text):
    """Generate a download link for a file"""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
    return href


def process_single_pdf(pdf_file, output_dir=None):
    """Process a single PDF file and return the path to the Excel file"""
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(pdf_file.getbuffer())
        pdf_path = tmp_pdf.name

    # Determine output path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"{os.path.splitext(pdf_file.name)[0]}_tables.xlsx"
        )
    else:
        # Create a temporary file for the Excel output
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
            output_path = tmp_excel.name

    # Extract tables
    extractor = PDFTableExtractor()
    extractor.debug = st.session_state.get("debug", False)

    try:
        # Add log capture
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.DEBUG if extractor.debug else logging.INFO)
        logger.addHandler(log_handler)

        tables = extractor.extract_tables_from_pdf(pdf_path, output_path)

        # Get logs
        log_handler.flush()
        logs = log_capture.getvalue()
        logger.removeHandler(log_handler)

        # Clean up the temporary PDF file
        os.unlink(pdf_path)

        return output_path, tables, logs
    except Exception as e:
        # Clean up the temporary PDF file
        os.unlink(pdf_path)
        raise e


def process_directory(input_dir, output_dir=None, recursive=False):
    """Process all PDF files in a directory"""
    if output_dir is None:
        output_dir = input_dir

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get list of PDF files
    pdf_files = []
    if recursive:
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
    else:
        pdf_files = [
            os.path.join(input_dir, f)
            for f in os.listdir(input_dir)
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(input_dir, f))
        ]

    if not pdf_files:
        st.warning(f"No PDF files found in {input_dir}")
        return []

    st.info(f"Found {len(pdf_files)} PDF files to process")

    # Process each PDF file
    results = []
    extractor = PDFTableExtractor()
    extractor.debug = st.session_state.get("debug", False)

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, pdf_file in enumerate(pdf_files):
        # Update progress
        progress = int((i / len(pdf_files)) * 100)
        progress_bar.progress(progress)
        status_text.text(
            f"Processing {i+1}/{len(pdf_files)}: {os.path.basename(pdf_file)}"
        )

        # Determine output path
        rel_path = (
            os.path.relpath(pdf_file, input_dir)
            if recursive
            else os.path.basename(pdf_file)
        )
        base_name = os.path.splitext(rel_path)[0]
        output_path = os.path.join(output_dir, f"{base_name}_tables.xlsx")

        # Extract tables
        try:
            # Add log capture
            log_capture = io.StringIO()
            log_handler = logging.StreamHandler(log_capture)
            log_handler.setLevel(logging.DEBUG if extractor.debug else logging.INFO)
            logger.addHandler(log_handler)

            tables = extractor.extract_tables_from_pdf(pdf_file, output_path)

            # Get logs
            log_handler.flush()
            logs = log_capture.getvalue()
            logger.removeHandler(log_handler)

            results.append(
                {
                    "pdf_file": pdf_file,
                    "output_file": output_path,
                    "tables": tables,
                    "logs": logs,
                    "success": True,
                }
            )
        except Exception as e:
            results.append({"pdf_file": pdf_file, "error": str(e), "success": False})

    # Complete progress
    progress_bar.progress(100)
    status_text.text("Processing complete!")

    return results


def main():
    st.title("PDF Table Extractor")
    st.markdown(
        """
    Extract tables from PDFs without using Tabula, Camelot, or converting to images.
    This tool can handle tables with or without borders and irregular shapes.
    """
    )

    # Initialize session state for logs
    if "logs" not in st.session_state:
        st.session_state.logs = []

    # Sidebar options
    st.sidebar.header("Options")

    # Debug mode
    st.session_state.debug = st.sidebar.checkbox("Debug Mode", value=False)

    # Extraction aggressiveness
    extraction_mode = st.sidebar.radio(
        "Extraction Mode",
        ["Standard", "Aggressive", "Very Aggressive"],
        index=2,  # Default to Very Aggressive
    )

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
                        output_path, tables, logs = process_single_pdf(uploaded_file)

                        # Display logs
                        with st.expander("Processing Logs", expanded=False):
                            st.text(logs)

                        if tables:
                            st.success(f"Successfully extracted {len(tables)} tables!")

                            # Display download link
                            st.markdown(
                                get_download_link(
                                    output_path, "📥 Download Excel File"
                                ),
                                unsafe_allow_html=True,
                            )

                            # Preview tables
                            st.header("Table Preview")
                            for i, table in enumerate(tables):
                                with st.expander(
                                    f"Table {i+1}: {table['name']}", expanded=i == 0
                                ):
                                    st.dataframe(table["data"])
                        else:
                            st.warning("No tables were detected in the document.")
                            st.info(
                                "Try adjusting the extraction mode to 'Very Aggressive' in the sidebar."
                            )
                    except Exception as e:
                        st.error(f"Error extracting tables: {str(e)}")

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
                with st.spinner("Processing PDF files..."):
                    try:
                        results = process_directory(dir_path, output_dir, recursive)

                        if results:
                            # Count successes and failures
                            successes = sum(1 for r in results if r["success"])
                            failures = len(results) - successes

                            st.success(
                                f"Processed {len(results)} PDF files: {successes} successful, {failures} failed."
                            )

                            # Display results
                            st.header("Results")

                            for i, result in enumerate(results):
                                if result["success"]:
                                    with st.expander(
                                        f"✅ {os.path.basename(result['pdf_file'])}"
                                    ):
                                        st.write(
                                            f"Output file: {result['output_file']}"
                                        )
                                        st.write(
                                            f"Tables extracted: {len(result['tables'])}"
                                        )

                                        # Add download link
                                        st.markdown(
                                            get_download_link(
                                                result["output_file"],
                                                "📥 Download Excel File",
                                            ),
                                            unsafe_allow_html=True,
                                        )

                                        # Show logs
                                        if "logs" in result:
                                            with st.expander("Processing Logs"):
                                                st.text(result["logs"])
                                else:
                                    with st.expander(
                                        f"❌ {os.path.basename(result['pdf_file'])}"
                                    ):
                                        st.error(f"Error: {result['error']}")
                        else:
                            st.warning("No PDF files were processed.")
                    except Exception as e:
                        st.error(f"Error processing directory: {str(e)}")

    # Tips section
    st.sidebar.header("Tips")
    st.sidebar.markdown(
        """
    - If tables aren't detected, try the 'Very Aggressive' extraction mode
    - Enable Debug Mode to see detailed extraction logs
    - For bank statements, the tool has specialized extraction logic
    - Some PDFs may require pre-processing if they use unusual formatting
    """
    )


if __name__ == "__main__":
    main()
