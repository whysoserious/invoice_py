#!/usr/bin/env python3
import argparse
import sys
import os
import PyPDF2
import anthropic
import base64
import re
import io
from pdf2image import convert_from_path
from PIL import Image

# AI model prompt definition
prompt = """Extract bank transaction data from these inputs and generate a CSV file:

Images with transaction data:
<image_files>
{{IMAGE_FILES}}
</image_files>

Parsed text for verification:
<parsed_text>
{{PARSED_TEXT}}
</parsed_text>

Instructions:
- Extract transaction details from images and compare with the parsed text
- Create a list of transactions with these columns in this exact order:
  a. data (date) in YYYY-MM-DD format
  b. od (from account)
  c. do (to account)
  d. suma przelewu (transfer amount)
  e. saldo przed (balance before)
  f. saldo po (balance after)
  g. opis transakcji (transaction description)
- Present CSV data in <csv_output> tags with comma separators

Example output format:
<csv_output>
data,od,do,suma przelewu,saldo przed,saldo po,opis transakcji
2023-05-01,123456789,987654321,1000.00,5000.00,4000.00,Payment for services
</csv_output>

Return ONLY the CSV data in <csv_output> tags. Do not include any explanations.
"""

def extract_text_from_pdf(pdf_path):  
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    text += f"[Page {page_num+1}: No text found or page is an image]\n"
        return text
    except Exception as e:
        return f"Error during text extraction: {str(e)}"

def convert_pdf_to_images(pdf_path, max_pages=100):
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=max_pages)
        
        # Convert images to base64 without saving to disk
        image_base64_list = []
        for i, image in enumerate(images):
            # Compress and convert to base64 for Claude
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            image_base64_list.append(img_base64)
            
            # Limit number of pages
            if i >= max_pages - 1:
                break
                
        return image_base64_list
    except Exception as e:
        print(f"Error during PDF to image conversion: {str(e)}")
        return []

def send_to_claude(pdf_path, parsed_text, api_key):
    try:
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Convert PDF to images
        print("Converting PDF to images...")
        image_base64_list = convert_pdf_to_images(pdf_path)
        
        if not image_base64_list:
            # If conversion failed, report error and don't send data
            error_message = "Error: PDF to image conversion failed. No data sent to Claude."
            print(error_message)
            return error_message
        
        # Create virtual image references
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        image_files_list = []
        for i in range(len(image_base64_list)):
            image_files_list.append(f"{base_filename}_image_{i+1}.jpg")
        
        # Prepare prompt with list of virtual image files
        image_files_text = "\n".join(image_files_list)
        modified_prompt = prompt.replace("{{IMAGE_FILES}}", image_files_text)
        modified_prompt = modified_prompt.replace("{{PARSED_TEXT}}", parsed_text)
        
        # Prepare message content with text and images
        content = [{"type": "text", "text": modified_prompt}]
        
        # Add images as attachments in the order of PDF pages
        for i, img_base64 in enumerate(image_base64_list):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_base64
                }
            })
        
        # Display JSON being sent to Claude API
        print("\n===== JSON BEING SENT TO CLAUDE API =====")
        request_json = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 20000,
            "temperature": 1,
            "messages": [
                {
                    "role": "user",
                    "content": []
                }
            ]
        }
        
        # Add text to JSON
        request_json["messages"][0]["content"].append({"type": "text", "text": modified_prompt})
        
        # Add images to JSON (with truncated base64)
        for i, img_base64 in enumerate(image_base64_list):
            truncated_base64 = img_base64[:10] + "..."
            request_json["messages"][0]["content"].append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": truncated_base64
                }
            })
        
        # Display JSON
        import json
        print(json.dumps(request_json, indent=2))
        print("===== END OF JSON =====\n")
        
        # Send request to Claude
        print(f"Sending request to Claude with {len(image_base64_list)} images...")
        print(f"List of image files: {', '.join(image_files_list)}")
        
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=20000,
            temperature=1,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        
        # Extract full response from Claude
        response_text = ""
        for content_block in message.content:
            if content_block.type == "text":
                response_text += content_block.text
        
        # Print the entire response
        print("\n===== FULL RESPONSE FROM CLAUDE =====")
        print(response_text)
        print("===== END OF RESPONSE =====\n")
        
        # Extract CSV from response
        csv_output = extract_csv_from_response(response_text)
        return csv_output
    
    except Exception as e:
        error_message = f"Error during Claude API request: {str(e)}"
        print(error_message)
        return error_message

def extract_csv_from_response(response):
    # Extract content between <csv_output> and </csv_output> tags
    pattern = r'<csv_output>(.*?)</csv_output>'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return "No CSV data found in the response."

def main():
    parser = argparse.ArgumentParser(description='Process invoices from the specified files or folder.')
    parser.add_argument('--folder', '-f', help='Folder containing invoices')
    parser.add_argument('--file', help='Path to a specific PDF file to process')
    parser.add_argument('--files', nargs='+', help='List of PDF files to process')
    parser.add_argument('--api-key', '-k', required=True, help='API key for processing invoices')
    
    args = parser.parse_args()
    api_key = args.api_key
    
    if api_key:
        print(f"Using API key: {api_key[:5]}{'*' * 10}")
    else:
        print("No API key provided. Cannot process files.")
        sys.exit(1)
    
    # Process a single file
    if args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File '{args.file}' does not exist!")
            sys.exit(1)
        
        if not args.file.lower().endswith('.pdf'):
            print(f"Error: File '{args.file}' is not a PDF file!")
            sys.exit(1)
            
        process_file(args.file, api_key)
        return
    
    # Process a list of files
    if args.files:
        found_pdf = False
        for file_path in args.files:
            if not os.path.isfile(file_path):
                print(f"Warning: File '{file_path}' does not exist! Skipping.")
                continue
                
            if not file_path.lower().endswith('.pdf'):
                print(f"Warning: File '{file_path}' is not a PDF file! Skipping.")
                continue
                
            process_file(file_path, api_key)
            found_pdf = True
            
        if not found_pdf:
            print("No valid PDF files found in the provided list.")
        return
    
    # Process all files in a folder
    if args.folder:
        folder_name = args.folder
        
        # Check if folder exists
        if not os.path.isdir(folder_name):
            print(f"Error: Folder '{folder_name}' does not exist!")
            sys.exit(1)
        
        print(f"Specified folder: {folder_name}")
        print(f"Folder exists and is accessible.")
        
        # List PDF files
        print("\nFound PDF files:")
        found_pdf = False
        
        for filename in os.listdir(folder_name):
            file_path = os.path.join(folder_name, filename)
            
            # Check only files (skip subfolders)
            if os.path.isfile(file_path):
                if filename.lower().endswith('.pdf'):
                    print(f"- {filename}")
                    found_pdf = True
                    process_file(file_path, api_key)
                else:
                    print(f"Ignoring file: {filename} (not a PDF file)")
        
        if not found_pdf:
            print("No PDF files found in the specified folder.")
        return
    
    print("Error: You must specify either --folder, --file, or --files")
    sys.exit(1)
    
def process_file(file_path, api_key):
    filename = os.path.basename(file_path)
    folder_name = os.path.dirname(file_path)
    
    # Extract text from PDF
    print(f"\nExtracting text from file: {filename}")
    parsed_text = extract_text_from_pdf(file_path)
    print("-" * 40)
    print(parsed_text[:50] + "..." if len(parsed_text) > 50 else parsed_text)
    print("-" * 40)
    
    # Send to Claude
    print(f"\nSending file {filename} to Claude API...")
    csv_result = send_to_claude(file_path, parsed_text, api_key)
    
    # Save result to CSV file
    csv_filename = os.path.splitext(filename)[0] + ".csv"
    csv_path = os.path.join(folder_name, csv_filename)
    with open(csv_path, 'w', encoding='utf-8') as csv_file:
        csv_file.write(csv_result)
    
    print(f"Result saved to file: {csv_filename}")
    print("-" * 40)
    print(csv_result[:1000] + "..." if len(csv_result) > 1000 else csv_result)
    print("-" * 40)

if __name__ == "__main__":
    main()