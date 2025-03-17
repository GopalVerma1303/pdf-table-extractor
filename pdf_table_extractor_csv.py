import pdfplumber
import pandas as pd
import re
import os
from collections import defaultdict
import logging
import zipfile
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PDFTableExtractor:
    def __init__(self):
        self.debug = False

    def extract_tables_from_pdf(self, pdf_path, output_dir=None):
        """
        Extract tables from a PDF file and save to CSV files

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save the CSV files (optional)

        Returns:
            List of dictionaries with table info and paths to CSV files
        """
        if self.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        # Determine output directory
        if output_dir is None:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_dir = os.path.dirname(pdf_path)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"Processing PDF: {pdf_path}")
        logger.info(f"Output will be saved to: {output_dir}")

        # Extract all tables from the PDF
        all_tables = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} pages")

                # Try multiple extraction methods
                all_tables = self._try_multiple_extraction_methods(pdf)

                # If no tables found, try more aggressive methods
                if not all_tables:
                    logger.info(
                        "No tables found with standard methods, trying aggressive extraction..."
                    )
                    all_tables = self._aggressive_table_extraction(pdf)
        except Exception as e:
            logger.error(f"Error opening or processing PDF: {str(e)}")
            raise

        # Save all tables to CSV files if any were found
        result = []
        if all_tables:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]

            # Save each table to a CSV file
            for i, table in enumerate(all_tables):
                # Create a safe filename
                safe_name = re.sub(r"[\\/*\[\]:?]", "_", table["name"])
                csv_path = os.path.join(output_dir, f"{base_name}_{safe_name}.csv")

                # Save to CSV
                table["data"].to_csv(csv_path, index=False)
                logger.info(f"Saved table to {csv_path}")

                # Add to result
                result.append(
                    {"name": table["name"], "path": csv_path, "data": table["data"]}
                )

            logger.info(
                f"Successfully extracted {len(all_tables)} tables to CSV files in {output_dir}"
            )

            # Create a ZIP file with all CSV files
            zip_path = os.path.join(output_dir, f"{base_name}_tables.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for table_info in result:
                    if os.path.exists(table_info["path"]):
                        zipf.write(
                            table_info["path"], os.path.basename(table_info["path"])
                        )
                    else:
                        logger.error(
                            f"File not found when creating ZIP: {table_info['path']}"
                        )

            logger.info(f"Created ZIP archive at {zip_path}")

            # Verify ZIP file exists
            if os.path.exists(zip_path):
                # Add ZIP path to result
                result.append(
                    {"name": "All Tables (ZIP)", "path": zip_path, "is_zip": True}
                )
            else:
                logger.error(f"ZIP file was not created: {zip_path}")
        else:
            logger.warning("No tables were detected in the document")

        return result

    def _try_multiple_extraction_methods(self, pdf):
        """Try multiple methods to extract tables"""
        all_tables = []

        # Method 1: Try pdfplumber's built-in table extraction
        logger.info("Trying pdfplumber's built-in table extraction...")
        tables = self._extract_with_pdfplumber(pdf)
        if tables:
            all_tables.extend(tables)
            logger.info(
                f"Found {len(tables)} tables with pdfplumber's built-in extractor"
            )

        # Method 2: Try to detect if this is a bank statement
        if not all_tables:
            logger.info("Checking if document is a bank statement...")
            if self._is_bank_statement(pdf):
                logger.info(
                    "Document appears to be a bank statement, using specialized extraction..."
                )
                tables = self._extract_bank_statement_tables(pdf)
                if tables:
                    all_tables.extend(tables)
                    logger.info(
                        f"Found {len(tables)} tables with bank statement extractor"
                    )

        # Method 3: Try layout-based extraction
        if not all_tables:
            logger.info("Trying layout-based table extraction...")
            tables = self._extract_tables_by_layout(pdf)
            if tables:
                all_tables.extend(tables)
                logger.info(f"Found {len(tables)} tables with layout-based extractor")

        return all_tables

    def _aggressive_table_extraction(self, pdf):
        """More aggressive methods to extract tables when standard methods fail"""
        all_tables = []

        # Method 4: Try line-based extraction (looking for aligned text)
        logger.info("Trying line-based table extraction...")
        tables = self._extract_tables_by_lines(pdf)
        if tables:
            all_tables.extend(tables)
            logger.info(f"Found {len(tables)} tables with line-based extractor")

        # Method 5: Try to extract any structured data
        if not all_tables:
            logger.info("Trying to extract any structured data...")
            tables = self._extract_any_structured_data(pdf)
            if tables:
                all_tables.extend(tables)
                logger.info(
                    f"Found {len(tables)} tables with structured data extractor"
                )

        return all_tables

    def _extract_with_pdfplumber(self, pdf):
        """Extract tables using pdfplumber's built-in table extraction"""
        tables = []

        for i, page in enumerate(pdf.pages):
            try:
                # Try with default settings
                page_tables = page.extract_tables()

                if not page_tables:
                    # Try with more lenient settings
                    page_tables = page.extract_tables(
                        table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "intersection_tolerance": 5,
                            "join_tolerance": 3,
                        }
                    )

                if page_tables:
                    for j, table_data in enumerate(page_tables):
                        # Filter out empty rows
                        filtered_data = [
                            row
                            for row in table_data
                            if any(cell and str(cell).strip() for cell in row)
                        ]

                        if filtered_data:
                            # Determine headers (first row or create generic headers)
                            headers = filtered_data[0] if filtered_data else []

                            # If headers are empty or None, create generic headers
                            if not headers or all(not h for h in headers):
                                max_cols = max(len(row) for row in filtered_data)
                                headers = [f"Column_{k+1}" for k in range(max_cols)]
                                data_rows = filtered_data
                            else:
                                data_rows = filtered_data[1:]

                            # Create DataFrame
                            df = pd.DataFrame(data_rows, columns=headers)

                            # Clean up DataFrame - replace applymap with map for each column
                            for col in df.columns:
                                df[col] = df[col].map(
                                    lambda x: str(x).strip() if x is not None else ""
                                )

                            tables.append(
                                {"name": f"Page_{i+1}_Table_{j+1}", "data": df}
                            )

                            logger.debug(
                                f"Extracted table {j+1} from page {i+1} with dimensions {df.shape}"
                            )
            except Exception as e:
                logger.warning(f"Error extracting tables from page {i+1}: {str(e)}")

        return tables

    # The rest of the methods remain the same as in your original code
    # I'm omitting them here for brevity, but they should be included in the actual file

    def _is_bank_statement(self, pdf):
        """Detect if the document is a bank statement"""
        keywords = [
            "account",
            "statement",
            "balance",
            "transaction",
            "credit",
            "debit",
            "bank",
            "deposit",
            "withdrawal",
            "opening balance",
            "closing balance",
            "date",
            "description",
            "amount",
            "reference",
            "branch",
        ]

        # Check first few pages for keywords
        pages_to_check = min(3, len(pdf.pages))

        for i in range(pages_to_check):
            try:
                text = pdf.pages[i].extract_text().lower()
                matches = sum(1 for keyword in keywords if keyword in text)

                if matches >= 3:
                    return True
            except:
                continue

        return False

    def _extract_bank_statement_tables(self, pdf):
        """Extract tables from bank statement PDFs"""
        all_tables = []
        transaction_data = []

        # Extract header information
        header_info = {}

        try:
            header_info = self._extract_bank_statement_header(pdf.pages[0])
        except Exception as e:
            logger.warning(f"Error extracting bank statement header: {str(e)}")

        # Process each page to extract transaction data
        for i, page in enumerate(pdf.pages):
            try:
                page_transactions = self._extract_bank_statement_transactions(page)
                if page_transactions:
                    transaction_data.extend(page_transactions)
                    logger.debug(
                        f"Extracted {len(page_transactions)} transactions from page {i+1}"
                    )
            except Exception as e:
                logger.warning(
                    f"Error extracting transactions from page {i+1}: {str(e)}"
                )

        if transaction_data:
            # Create a DataFrame from the transaction data
            df = pd.DataFrame(transaction_data)

            # Add header information as metadata
            metadata_df = pd.DataFrame([header_info])

            all_tables.append({"name": "Account_Information", "data": metadata_df})
            all_tables.append({"name": "Transactions", "data": df})

        return all_tables

    def _extract_bank_statement_header(self, page):
        """Extract header information from a bank statement page"""
        text = page.extract_text()
        header_info = {}

        # Extract common bank statement header fields
        patterns = {
            "bank_name": r"(?:BANK|Bank)\s*(?:NAME|Name)\s*:?\s*([^\n]+)",
            "branch_name": r"(?:BRANCH|Branch)\s*(?:NAME|Name)\s*:?\s*([^\n]+)",
            "account_no": r"(?:Account|A/C)\s*(?:No|Number|#)\s*:?\s*([^\n]+)",
            "account_name": r"(?:A/C|Account)\s*(?:Name|Holder)\s*:?\s*([^\n]+)",
            "address": r"(?:Address|ADDR)\s*:?\s*([^\n]+)",
            "statement_period": r"(?:Statement|Period)(?:\s*for)?\s*:?\s*([^\n]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header_info[key] = match.group(1).strip()

        return header_info

    def _extract_bank_statement_transactions(self, page):
        """Extract transaction data from a bank statement page"""
        text = page.extract_text()
        transactions = []

        # Skip pages without transaction data
        date_patterns = [
            r"\d{2}-[A-Za-z]{3}-\d{4}",  # 01-Jan-2023
            r"\d{2}/\d{2}/\d{4}",  # 01/01/2023
            r"\d{2}-\d{2}-\d{4}",  # 01-01-2023
            r"\d{2}\.\d{2}\.\d{4}",  # 01.01.2023
        ]

        has_dates = any(re.search(pattern, text) for pattern in date_patterns)
        if not has_dates:
            return []

        # Split the text into lines
        lines = text.split("\n")

        # Find the transaction section
        transaction_start = False
        transaction_headers = [
            "date",
            "description",
            "amount",
            "balance",
            "debit",
            "credit",
            "particulars",
            "withdrawal",
            "deposit",
            "transaction",
            "reference",
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if this line might be a header row
            if not transaction_start:
                header_matches = sum(
                    1 for header in transaction_headers if header in line_lower
                )
                if header_matches >= 2:
                    transaction_start = True
                    continue

            # Check for transaction data patterns once we're in the transaction section
            if transaction_start or any(
                re.search(pattern, line) for pattern in date_patterns
            ):
                # Skip lines that are likely headers or footers
                if re.search(
                    r"Page\s+\d+|BANK NAME|BRANCH NAME|IFSC Code|MICR Code",
                    line,
                    re.IGNORECASE,
                ):
                    continue

                # Try to parse transaction line
                transaction = self._parse_transaction_line(line)
                if transaction:
                    transactions.append(transaction)
                    transaction_start = True  # We found a transaction, so we're definitely in the transaction section

        return transactions

    def _parse_transaction_line(self, line):
        """Parse a single transaction line from bank statement"""
        # Different patterns for transaction lines
        patterns = [
            # Pattern 1: Date, Transaction Type, Description, Debit, Credit, Balance
            r"(\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{2})\s+([A-Z])?\s*(.{10,50}?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)?(?:\s+|\s*-\s*)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)?(?:\s+|\s*-\s*)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:Dr|Cr)?)",
            # Pattern 2: Date, Description, Amount, Balance
            r"(\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{2})\s+(.{10,60}?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:Dr|Cr)?)",
            # Pattern 3: Simple pattern with just date, description and numbers
            r"(\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{2})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            # Pattern 4: Date at start, numbers at end (flexible middle)
            r"(\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{2})(.+?)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                # Create transaction dictionary based on the pattern matched
                if len(groups) == 6:  # Pattern 1
                    return {
                        "date": groups[0],
                        "type": groups[1] if groups[1] else "",
                        "description": groups[2].strip(),
                        "debit": groups[3] if groups[3] else "",
                        "credit": groups[4] if groups[4] else "",
                        "balance": groups[5],
                    }
                elif len(groups) == 4:  # Pattern 2 or 3
                    # For Pattern 2, check if balance contains Dr/Cr
                    if "Dr" in groups[3] or "Cr" in groups[3]:
                        return {
                            "date": groups[0],
                            "description": groups[1].strip(),
                            "amount": groups[2],
                            "balance": groups[3],
                        }
                    else:  # Pattern 3
                        return {
                            "date": groups[0],
                            "description": groups[1].strip(),
                            "debit_or_credit": groups[2],
                            "balance": groups[3],
                        }
                elif len(groups) == 3:  # Pattern 4
                    return {
                        "date": groups[0],
                        "description": groups[1].strip(),
                        "amount": groups[2],
                    }

        # Try to extract just the date and any numbers
        date_match = re.search(
            r"(\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{2}[-/.]\d{2}[-/.]\d{2})",
            line,
        )
        amount_matches = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", line)

        if date_match and amount_matches and len(amount_matches) >= 1:
            # Extract the text between date and first amount as description
            date_end = date_match.end()
            description_text = line[
                date_end : line.find(amount_matches[0], date_end)
            ].strip()

            return {
                "date": date_match.group(1),
                "description": description_text,
                "amount": amount_matches[0],
                "other_amounts": (
                    ",".join(amount_matches[1:]) if len(amount_matches) > 1 else ""
                ),
            }

        return None

    def _extract_tables_by_layout(self, pdf):
        """Extract tables by analyzing text layout and alignment"""
        tables = []

        for i, page in enumerate(pdf.pages):
            try:
                # Get all text characters with their positions
                chars = page.chars

                if not chars:
                    continue

                # Group characters into lines based on y-position
                lines_by_y = defaultdict(list)
                for char in chars:
                    # Round y-position to group nearby lines
                    y_rounded = round(char["y"])
                    lines_by_y[y_rounded].append(char)

                # Sort lines by y-position
                sorted_lines = []
                for y in sorted(lines_by_y.keys()):
                    line_chars = sorted(lines_by_y[y], key=lambda c: c["x"])
                    sorted_lines.append(line_chars)

                # Analyze lines to find potential table rows
                table_rows = self._identify_table_rows(sorted_lines)

                if table_rows:
                    # Convert table rows to a DataFrame
                    headers = [cell.strip() for cell in table_rows[0]]
                    data_rows = [
                        [cell.strip() for cell in row] for row in table_rows[1:]
                    ]

                    # Ensure all rows have the same number of columns
                    max_cols = max(len(row) for row in table_rows)
                    headers.extend([""] * (max_cols - len(headers)))

                    for i in range(len(data_rows)):
                        data_rows[i].extend([""] * (max_cols - len(data_rows[i])))

                    df = pd.DataFrame(data_rows, columns=headers)

                    tables.append({"name": f"Page_{i+1}_Layout_Table", "data": df})

                    logger.debug(
                        f"Extracted layout-based table from page {i+1} with dimensions {df.shape}"
                    )
            except Exception as e:
                logger.warning(
                    f"Error extracting layout-based table from page {i+1}: {str(e)}"
                )

        return tables

    def _identify_table_rows(self, sorted_lines):
        """Identify table rows from sorted lines of characters"""
        if not sorted_lines:
            return []

        # Find x-positions that appear consistently across multiple lines
        x_positions = []
        for line in sorted_lines:
            if len(line) > 3:  # Only consider lines with enough characters
                x_positions.extend([char["x"] for char in line])

        if not x_positions:
            return []

        # Find clusters of x-positions (potential column boundaries)
        x_clusters = self._cluster_positions(x_positions)

        if len(x_clusters) < 2:  # Need at least 2 columns
            return []

        # Use x-clusters to split lines into columns
        table_rows = []
        for line in sorted_lines:
            if not line:
                continue

            # Skip lines that are too short
            if len(line) < 3:
                continue

            # Extract text between column boundaries
            row = []
            for i in range(len(x_clusters) - 1):
                start_x = x_clusters[i]
                end_x = x_clusters[i + 1]

                # Get characters in this column
                col_chars = [c for c in line if start_x <= c["x"] < end_x]

                if col_chars:
                    col_text = "".join(
                        c["text"]
                        for c in sorted(col_chars, key=lambda c: (c["x"], c["y"]))
                    )
                    row.append(col_text)
                else:
                    row.append("")

            # Add the last column
            last_chars = [c for c in line if c["x"] >= x_clusters[-1]]
            if last_chars:
                last_text = "".join(
                    c["text"]
                    for c in sorted(last_chars, key=lambda c: (c["x"], c["y"]))
                )
                row.append(last_text)
            else:
                row.append("")

            # Only add rows that have content in multiple columns
            if sum(1 for cell in row if cell.strip()) >= 2:
                table_rows.append(row)

        return table_rows

    def _cluster_positions(self, positions, tolerance=5):
        """Cluster x-positions to find column boundaries"""
        if not positions:
            return []

        # Sort positions
        sorted_pos = sorted(positions)

        # Find clusters
        clusters = []
        current_cluster = [sorted_pos[0]]

        for pos in sorted_pos[1:]:
            if pos - current_cluster[-1] <= tolerance:
                current_cluster.append(pos)
            else:
                # Calculate the average position for this cluster
                clusters.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [pos]

        # Add the last cluster
        if current_cluster:
            clusters.append(sum(current_cluster) / len(current_cluster))

        # Ensure we have the start and end positions
        if len(clusters) < 2:
            # If only one cluster, add a second one
            if clusters:
                min_pos = min(sorted_pos)
                max_pos = max(sorted_pos)
                clusters = [min_pos, max_pos]
            else:
                return []

        return clusters

    def _extract_tables_by_lines(self, pdf):
        """Extract tables by analyzing text lines and their alignment"""
        tables = []

        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")

                # Find potential table sections
                table_sections = self._identify_table_sections(lines)

                for j, section in enumerate(table_sections):
                    if len(section) < 3:  # Need at least 3 lines for a table
                        continue

                    # Process the table section
                    processed_table = self._process_table_section(section)

                    if processed_table and processed_table["rows"]:
                        # Convert to DataFrame
                        headers = processed_table["headers"]
                        data_rows = processed_table["rows"]

                        # Ensure all rows have the same number of columns
                        max_cols = max(len(headers), max(len(row) for row in data_rows))
                        headers.extend([""] * (max_cols - len(headers)))

                        for k in range(len(data_rows)):
                            data_rows[k].extend([""] * (max_cols - len(data_rows[k])))

                        df = pd.DataFrame(data_rows, columns=headers)

                        tables.append({"name": f"Page_{i+1}_Section_{j+1}", "data": df})

                        logger.debug(
                            f"Extracted line-based table from page {i+1}, section {j+1} with dimensions {df.shape}"
                        )
            except Exception as e:
                logger.warning(
                    f"Error extracting line-based table from page {i+1}: {str(e)}"
                )

        return tables

    def _identify_table_sections(self, lines):
        """Identify sections of text that might contain tables"""
        table_sections = []
        current_section = []
        in_table = False

        # Heuristics to detect table start/end
        for line in lines:
            # Skip empty lines
            if not line.strip():
                if in_table and current_section:
                    # Empty line might indicate end of table
                    table_sections.append(current_section)
                    current_section = []
                    in_table = False
                continue

            # Check if line might be part of a table
            if self._is_potential_table_row(line):
                if not in_table:
                    in_table = True
                    current_section = []
                current_section.append(line)
            else:
                if in_table and len(current_section) >= 2:
                    # Non-table line after table lines indicates end of table
                    table_sections.append(current_section)
                    current_section = []
                in_table = False

        # Don't forget the last section
        if in_table and len(current_section) >= 2:
            table_sections.append(current_section)

        # If no tables found, try a more aggressive approach
        if not table_sections:
            # Look for any consecutive lines with similar structure
            for i in range(len(lines) - 2):
                if (
                    self._line_similarity(lines[i], lines[i + 1]) > 0.5
                    and self._line_similarity(lines[i + 1], lines[i + 2]) > 0.5
                ):
                    # Found 3 consecutive similar lines, likely a table
                    end_idx = i + 3
                    while (
                        end_idx < len(lines)
                        and self._line_similarity(lines[i], lines[end_idx]) > 0.3
                    ):
                        end_idx += 1

                    table_sections.append(lines[i:end_idx])
                    i = end_idx - 1

        return table_sections

    def _line_similarity(self, line1, line2):
        """Calculate similarity between two lines based on their structure"""
        # Compare the pattern of spaces, digits, and letters
        pattern1 = "".join(
            "S" if c.isspace() else ("D" if c.isdigit() else "L") for c in line1
        )
        pattern2 = "".join(
            "S" if c.isspace() else ("D" if c.isdigit() else "L") for c in line2
        )

        # Calculate similarity as the ratio of matching characters
        min_len = min(len(pattern1), len(pattern2))
        if min_len == 0:
            return 0

        matches = sum(1 for i in range(min_len) if pattern1[i] == pattern2[i])
        return matches / min_len

    def _is_potential_table_row(self, line):
        """Check if a line might be part of a table"""
        # Check for consistent spacing patterns
        spaces = [m.start() for m in re.finditer(r"\s{2,}", line)]
        if len(spaces) >= 2:
            return True

        # Check for common delimiters
        delimiters = ["|", "\t", ";", ","]
        for delimiter in delimiters:
            if line.count(delimiter) >= 2:
                return True

        # Check for aligned numbers (common in financial tables)
        numbers = re.findall(r"\d+(?:\.\d+)?", line)
        if len(numbers) >= 2:
            return True

        # Check for date patterns (common in transaction tables)
        date_patterns = [
            r"\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}",  # 01-Jan-2023
            r"\d{2}/\d{2}/\d{4}",  # 01/01/2023
            r"\d{2}-\d{2}-\d{4}",  # 01-01-2023
        ]
        if any(re.search(pattern, line) for pattern in date_patterns):
            return True

        return False

    def _process_table_section(self, section):
        """Process a potential table section to extract rows and columns"""
        if not section:
            return None

        # Try multiple column detection methods
        methods = [
            self._detect_column_boundaries_by_spaces,
            self._detect_column_boundaries_by_alignment,
            self._detect_column_boundaries_by_delimiters,
        ]

        for method in methods:
            column_boundaries = method(section)
            if column_boundaries and len(column_boundaries) > 1:
                break

        if not column_boundaries or len(column_boundaries) < 2:
            return None

        # Extract headers (assume first row contains headers)
        headers = self._extract_columns(section[0], column_boundaries)

        # Extract rows
        rows = []
        for line in section[1:]:
            row = self._extract_columns(line, column_boundaries)
            if row:
                rows.append(row)

        # Clean up headers and rows
        headers = [h.strip() for h in headers]
        for i in range(len(rows)):
            rows[i] = [cell.strip() for cell in rows[i]]

        # If headers are all empty, use first row as headers
        if all(not h for h in headers) and rows:
            headers = rows[0]
            rows = rows[1:]

        # If headers are still all empty, create generic headers
        if all(not h for h in headers):
            max_cols = max(len(row) for row in rows) if rows else len(headers)
            headers = [f"Column_{k+1}" for k in range(max_cols)]

        return {"headers": headers, "rows": rows}

    def _detect_column_boundaries_by_spaces(self, section):
        """Detect column boundaries by analyzing spacing patterns"""
        # Count space frequencies at each position
        space_freq = defaultdict(int)
        max_line_length = 0

        for line in section:
            max_line_length = max(max_line_length, len(line))
            for i, char in enumerate(line):
                if char.isspace():
                    space_freq[i] += 1

        # Find positions with high frequency of spaces
        threshold = (
            len(section) * 0.6
        )  # At least 60% of lines have space at this position
        potential_boundaries = [
            i for i, freq in space_freq.items() if freq >= threshold
        ]

        # Group adjacent positions
        boundaries = []
        if potential_boundaries:
            current_group = [potential_boundaries[0]]

            for i in range(1, len(potential_boundaries)):
                if potential_boundaries[i] - potential_boundaries[i - 1] <= 1:
                    current_group.append(potential_boundaries[i])
                else:
                    # Use the middle of the group as the boundary
                    boundaries.append(sum(current_group) // len(current_group))
                    current_group = [potential_boundaries[i]]

            # Add the last group
            if current_group:
                boundaries.append(sum(current_group) // len(current_group))

        # Add start and end positions
        boundaries = [0] + boundaries + [max_line_length]

        return boundaries

    def _detect_column_boundaries_by_alignment(self, section):
        """Detect column boundaries by analyzing character alignment"""
        # Look for aligned characters (especially numbers and dates)
        number_positions = []

        for line in section:
            # Find positions of numbers and dates
            for match in re.finditer(
                r"\d+(?:\.\d+)?|\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}/\d{2}/\d{4}", line
            ):
                number_positions.append(match.start())

        if not number_positions:
            return None

        # Cluster the positions
        clusters = self._cluster_positions(number_positions)

        # Add start and end positions
        max_line_length = max(len(line) for line in section)
        boundaries = [0] + clusters + [max_line_length]

        return boundaries

    def _detect_column_boundaries_by_delimiters(self, section):
        """Detect column boundaries by looking for delimiters"""
        # Check for common delimiters
        delimiters = ["|", "\t", ";", ","]

        for delimiter in delimiters:
            if all(delimiter in line for line in section[: min(3, len(section))]):
                # Use delimiter positions as boundaries
                boundaries = [0]

                # Use the first line as reference
                for i, char in enumerate(section[0]):
                    if char == delimiter:
                        boundaries.append(i)

                # Add end position
                max_line_length = max(len(line) for line in section)
                boundaries.append(max_line_length)

                return boundaries

        return None

    def _extract_columns(self, line, boundaries):
        """Extract column values based on detected boundaries"""
        if len(line) < boundaries[-1]:
            line = line + " " * (boundaries[-1] - len(line))

        columns = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]

            if start < len(line) and end <= len(line):
                columns.append(line[start:end])
            else:
                columns.append("")

        return columns

    def _extract_any_structured_data(self, pdf):
        """Extract any structured data from the PDF as a last resort"""
        tables = []

        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")

                # Filter out very short lines and headers/footers
                filtered_lines = [
                    line
                    for line in lines
                    if len(line) > 10 and not re.search(r"Page \d+|^\s*\d+\s*$", line)
                ]

                if len(filtered_lines) < 3:
                    continue

                # Try to identify any structure in the data
                data_rows = []

                for line in filtered_lines:
                    # Extract all numbers from the line
                    numbers = re.findall(r"\d+(?:\.\d+)?", line)

                    # Extract dates
                    dates = re.findall(
                        r"\d{2}[-/.][A-Za-z]{3}[-/.]\d{4}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}",
                        line,
                    )

                    # If line has numbers or dates, consider it as data
                    if numbers or dates:
                        # Split the line into chunks
                        chunks = re.split(r"\s{2,}", line)
                        if len(chunks) >= 2:
                            data_rows.append(chunks)

                if data_rows:
                    # Determine the number of columns
                    max_cols = max(len(row) for row in data_rows)

                    # Create headers
                    headers = [f"Column_{k+1}" for k in range(max_cols)]

                    # Ensure all rows have the same number of columns
                    for i in range(len(data_rows)):
                        data_rows[i].extend([""] * (max_cols - len(data_rows[i])))

                    # Create DataFrame
                    df = pd.DataFrame(data_rows, columns=headers)

                    tables.append({"name": f"Page_{i+1}_Structured_Data", "data": df})

                    logger.debug(
                        f"Extracted structured data from page {i+1} with dimensions {df.shape}"
                    )
            except Exception as e:
                logger.warning(
                    f"Error extracting structured data from page {i+1}: {str(e)}"
                )

        return tables


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract tables from PDF files")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output-dir", "-o", help="Directory to save the CSV files")
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug output"
    )

    args = parser.parse_args()

    extractor = PDFTableExtractor()
    extractor.debug = args.debug
    extractor.extract_tables_from_pdf(args.pdf_path, args.output_dir)


if __name__ == "__main__":
    main()
