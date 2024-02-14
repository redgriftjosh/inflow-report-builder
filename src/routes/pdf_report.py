import pdfkit
import json
import sys

def get_payload():
    file_path = sys.argv[1]
    try:
        # Open and read the content of the temporary file
        with open(file_path, 'r') as file:
            data = json.load(file)
            html = data.get('html')  # Safely extract the HTML content
            
            if html is None:
                raise ValueError("HTML content is missing")
            return html
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

def start():
    html_json = get_payload()

    html = json.dumps(html_json)

    # Save the entire HTML data (dictionary) to a .txt file for inspection
    with open('html_data.txt', 'w') as output_file:
        output_file.write(html)

    # Debugging: Check the type and content
    print(f"Type of HTML content: {type(html)}")
    if isinstance(html, str):
        print("HTML content is a string.")
    else:
        print("HTML content is not a string.")
        sys.exit(1)  # Exit if html is not a string to avoid passing invalid data to pdfkit

    options = {
    'page-size': 'Letter',
    'margin-top': '0.75in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.75in',
    'encoding': "UTF-8",
    'no-outline': None,
    'disable-javascript': '',  # Uncomment if JavaScript is not needed
    'no-images': ''
}

    pdfkit.from_string(html, 'output.pdf', options=options)

start()