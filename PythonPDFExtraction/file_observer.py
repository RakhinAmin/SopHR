# Import necessary libraries
import fitz  # PyMuPDF - used for reading and extracting text from PDF files
import re  # Regular expressions - for pattern matching in strings
import time  # For adding delays, useful in retry loops
import shutil  # For copying files
import os  # For interacting with the operating system (like creating folders)
import portalocker  # For locking files during read/write to prevent access issues
from watchdog.events import FileSystemEventHandler  # Watches for file system events (like file creation)
from watchdog.observers import Observer  # Observes the filesystem for changes

# Define a class to handle PDF files when they appear in the watched folder
class PDFHandler(FileSystemEventHandler):
    def __init__(self, keywords):
        self.keywords = keywords  # Not used in this script, but ready for future enhancements
        # Define a temporary directory to safely copy and process PDFs
        self.temp_dir = r'C:\Users\Rakhin.Amin\Documents\PythonPDFExtraction\Temp'
        os.makedirs(self.temp_dir, exist_ok=True)  # Create the temp dir if it doesn't exist

    # This function is called whenever a new file is created in the watched folder
    def on_created(self, event):
        if event.is_directory:
            return  # Ignore folder creations
        if event.src_path.endswith('.pdf'):  # Only process PDF files
            print(f'New PDF detected: {event.src_path}')
            self.process_pdf(event.src_path)  # Start processing the new PDF

    # Function to process a PDF file
    def process_pdf(self, pdf_path):
        print(f"Processing new file: {pdf_path}")
        # Define the path in the temp directory for safe processing
        temp_pdf_path = os.path.join(self.temp_dir, os.path.basename(pdf_path))
        retry_count = 10  # Number of times to retry in case of failure (file might be in use)
        retry_delay = 1  # Delay between retries in seconds

        for attempt in range(retry_count):
            try:
                # Open destination file in write-binary mode and lock it
                with open(temp_pdf_path, 'wb') as dest_file:
                    portalocker.lock(dest_file, portalocker.LOCK_EX)  # Lock the file for exclusive access
                    shutil.copyfileobj(open(pdf_path, 'rb'), dest_file)  # Copy the PDF to the temp file

                # Open the copied PDF using fitz (PyMuPDF)
                document = fitz.open(temp_pdf_path)
                text = ""

                # Extract text from every page in the PDF
                for page_num in range(len(document)):
                    page = document.load_page(page_num)
                    text += page.get_text()

                # Define headers (for display purposes)
                headers = ["Units/Shares", "Price", "Value in Share Class Currency"]
                # Use a regex to extract data from the PDF text
                values = self.extract_table_data(text)

                # Output the extracted information
                print("Headers:", headers)
                print("Values:", values)

                # Delete the temp file after processing is done
                os.remove(temp_pdf_path)
                return  # Exit the loop and function after successful processing

            except Exception as e:
                # If there's an error, wait and retry
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(retry_delay)

        # If all retries fail, print an error message
        print(f"Failed to process {pdf_path} after {retry_count} attempts.")

    # Function to extract specific table data using a regular expression
    def extract_table_data(self, text):
        # Regex pattern to find: Units/Shares, Price, and Value in Share Class Currency
        pattern = r"Units/Shares\s+([\d,.]+)\s+Price\s+([\d.]+)\s+Value in Share Class Currency\s+([\w\s.,$]+)"
        match = re.search(pattern, text)  # Search for the pattern in the text
        if match:
            # If found, return the extracted values as a list
            units_shares = match.group(1).strip()
            price = match.group(2).strip()
            value_in_share_class_currency = match.group(3).strip()
            return [units_shares, price, value_in_share_class_currency]
        return None  # If pattern is not found, return None

# Main function to set up the folder watcher
def main(folder_to_watch, keywords):
    event_handler = PDFHandler(keywords)  # Create an instance of PDFHandler
    observer = Observer()  # Create an Observer to watch for file changes
    observer.schedule(event_handler, folder_to_watch, recursive=False)  # Watch the specified folder (non-recursive)
    observer.start()  # Start the observer

    try:
        while True:
            time.sleep(1)  # Keep the script running until manually stopped
    except KeyboardInterrupt:
        observer.stop()  # Stop watching if user presses Ctrl+C
    observer.join()  # Wait for the observer to finish

# Define the folder to monitor for new PDFs
folder_to_watch = r'C:\Users\Rakhin.Amin\Documents\PythonPDFExtraction'

# List of keywords (defined but not currently used)
keywords = [
    {'column': 'Revenue', 'synonyms': ['Revenue', 'Total Revenue', 'Sales']},
    {'column': 'Expenses', 'synonyms': ['Expenses', 'Total Expenses', 'Operating Expenses']},
    {'column': 'Net Income', 'synonyms': ['Net Income', 'Profit', 'Earnings']}
]

# Start the main program
main(folder_to_watch, keywords)
