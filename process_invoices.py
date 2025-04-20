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

# Definicja promptu dla modelu AI
prompt = """You are an advanced AI assistant specializing in financial data extraction and processing. Your task is to create an accurate transaction history in CSV format based on the provided data. This task requires extreme precision and attention to detail.

You will be working with the following inputs:

1. A list of image files containing transaction data:
<image_files>
{{IMAGE_FILES}}
</image_files>

2. Parsed text data for comparison:
<parsed_text>
{{PARSED_TEXT}}
</parsed_text>

Your objective is to extract transaction data from the image files, compare it with the parsed text, and generate a CSV file with the transaction history. Follow these steps carefully:

1. Analyze the image files:
   - Extract all transaction details from each image file.
   - Be aware that a single transaction may span across multiple image files.
   - Pay close attention to dates, account numbers, amounts, and transaction descriptions.

2. Compare extracted data:
   - Carefully compare the data you've extracted from the images with the information in the parsed text.
   - If there are any discrepancies, use your judgment to determine which source is more likely to be accurate.

3. Prepare CSV data:
   - Create a list of transactions with the following columns in this exact order:
     a. data (date) always in format YYYY-MM-DD (eg. 2024-01-01)
     b. od (from)
     c. do (to)
     d. suma przelewu (transfer amount)
     e. saldo przed (balance before)
     f. saldo po (balance after)
     g. opis transakcji (transaction description)

4. Generate CSV output:
   - Present the final CSV data in <csv_output> tags. Use ',' as a separator.

Before providing your final output, wrap your thought process in <analysis> tags inside your thinking block. Include the following steps:

1. List each image file and the key transaction details extracted from it.
2. Create a comparison table showing the extracted data vs the parsed text data.
3. Note any discrepancies and explain your reasoning for resolving them.
4. Show a sample of how you're formatting the data for the CSV output.

This breakdown will help maintain the highest level of accuracy throughout the task. It's OK for this section to be quite long.

Example of the desired CSV output structure:

<csv_output>
data,od,do,suma przelewu,saldo przed,saldo po,opis transakcji
2023-05-01,123456789,987654321,1000.00,5000.00,4000.00,Payment for services
2023-05-02,987654321,123456789,500.00,4000.00,4500.00,Refund
</csv_output>

Remember to maintain the utmost accuracy and attention to detail throughout this process. Double-check your work to ensure all data has been correctly extracted, compared, and recorded in the CSV format as specified.

Your final output should consist only of the CSV data in the <csv_output> tags and should not duplicate or rehash any of the work you did in the analysis section.
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
                    text += f"[Strona {page_num+1}: Nie znaleziono tekstu lub strona jest obrazem]\n"
        return text
    except Exception as e:
        return f"Błąd podczas ekstrakcji tekstu: {str(e)}"

def convert_pdf_to_images(pdf_path, max_pages=100):
    try:
        # Konwertuj PDF na obrazy
        images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=max_pages)
        
        # Przygotuj nazwę bazową dla obrazów
        base_filename = os.path.splitext(pdf_path)[0]
        
        # Konwertuj obrazy do base64 i zapisz je na dysku
        image_base64_list = []
        for i, image in enumerate(images):
            # Zapisz obraz na dysku
            image_filename = f"{base_filename}_generated_{i+1}.jpg"
            image.save(image_filename, "JPEG", quality=85)
            print(f"Zapisano obraz: {image_filename}")
            
            # Kompresuj i konwertuj do base64 dla Claude
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            image_base64_list.append(img_base64)
            
            # Limit liczby stron
            if i >= max_pages - 1:
                break
                
        return image_base64_list
    except Exception as e:
        print(f"Błąd podczas konwersji PDF na obrazy: {str(e)}")
        return []

def send_to_claude(pdf_path, parsed_text, api_key):
    try:
        # Inicjalizacja klienta Anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Konwertuj PDF na obrazy
        print("Konwertowanie PDF na obrazy...")
        image_base64_list = convert_pdf_to_images(pdf_path)
        
        if not image_base64_list:
            # Jeśli konwersja się nie powiodła, zgłoś błąd i nie wysyłaj danych
            error_message = "Błąd: Konwersja PDF na obrazy nie powiodła się. Nie wysłano danych do Claude."
            print(error_message)
            return error_message
        
        # Przygotuj listę nazw plików obrazów
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        image_files_list = []
        for i in range(len(image_base64_list)):
            image_files_list.append(f"{base_filename}_generated_{i+1}.jpg")
        
        # Przygotuj prompt z listą plików obrazów
        image_files_text = "\n".join(image_files_list)
        modified_prompt = prompt.replace("{{IMAGE_FILES}}", image_files_text)
        modified_prompt = modified_prompt.replace("{{PARSED_TEXT}}", parsed_text)
        
        # Przygotuj zawartość wiadomości z tekstem i obrazami
        content = [{"type": "text", "text": modified_prompt}]
        
        # Dodaj obrazy jako załączniki w kolejności stron z PDF
        for i, img_base64 in enumerate(image_base64_list):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_base64
                }
            })
        
        # Wyświetl JSON wysyłany do Claude API
        print("\n===== JSON WYSYŁANY DO CLAUDE API =====")
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
        
        # Dodaj tekst do JSON
        request_json["messages"][0]["content"].append({"type": "text", "text": modified_prompt})
        
        # Dodaj obrazy do JSON (z obciętym base64)
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
        
        # Wyświetl JSON
        import json
        print(json.dumps(request_json, indent=2))
        print("===== KONIEC JSON =====\n")
        
        # Wyślij zapytanie do Claude
        print(f"Wysyłanie zapytania do Claude z {len(image_base64_list)} obrazami...")
        print(f"Lista plików obrazów: {', '.join(image_files_list)}")
        
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
        
        # Wyciągnij pełną odpowiedź z Claude
        response_text = ""
        for content_block in message.content:
            if content_block.type == "text":
                response_text += content_block.text
        
        # Wypisz całą odpowiedź
        print("\n===== PEŁNA ODPOWIEDŹ Z CLAUDE =====")
        print(response_text)
        print("===== KONIEC ODPOWIEDZI =====\n")
        
        # Wyciągnij CSV z odpowiedzi
        csv_output = extract_csv_from_response(response_text)
        return csv_output
    
    except Exception as e:
        error_message = f"Błąd podczas wysyłania zapytania do Claude: {str(e)}"
        print(error_message)
        return error_message

def extract_csv_from_response(response):
    # Wyciągnij zawartość między tagami <csv_output> i </csv_output>
    pattern = r'<csv_output>(.*?)</csv_output>'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return "Nie znaleziono danych CSV w odpowiedzi."

def main():
    parser = argparse.ArgumentParser(description='Przetwarzanie faktur z podanego folderu.')
    parser.add_argument('--folder', '-f', required=True, help='Nazwa folderu z fakturami')
    parser.add_argument('--api-key', '-k', required=True, help='Klucz API do przetwarzania faktur')
    
    args = parser.parse_args()
    folder_name = args.folder
    api_key = args.api_key
    
    if api_key:
        print(f"Użyto klucza API: {api_key[:5]}{'*' * 10}")
    else:
        print("Nie podano klucza API. Nie można przetworzyć plików.")
        sys.exit(1)
    
    # Sprawdzanie czy folder istnieje
    if not os.path.isdir(folder_name):
        print(f"Błąd: Folder '{folder_name}' nie istnieje!")
        sys.exit(1)
    
    print(f"Podany folder: {folder_name}")
    print(f"Folder istnieje i jest dostępny.")
    
    # Wypisywanie plików PDF
    print("\nZnalezione pliki PDF:")
    found_pdf = False
    
    for filename in os.listdir(folder_name):
        file_path = os.path.join(folder_name, filename)
        
        # Sprawdzanie tylko plików (pomijanie podfolderów)
        if os.path.isfile(file_path):
            if filename.lower().endswith('.pdf'):
                print(f"- {filename}")
                found_pdf = True
                
                # Ekstrakcja tekstu z PDF
                print(f"\nEkstrakcja tekstu z pliku: {filename}")
                parsed_text = extract_text_from_pdf(file_path)
                print("-" * 40)
                print(parsed_text[:50] + "..." if len(parsed_text) > 50 else parsed_text)
                print("-" * 40)
                
                # Wysyłanie do Claude
                print(f"\nWysyłanie pliku {filename} do Claude API...")
                csv_result = send_to_claude(file_path, parsed_text, api_key)
                
                # Zapisywanie wyniku do pliku CSV
                csv_filename = os.path.splitext(filename)[0] + ".csv"
                csv_path = os.path.join(folder_name, csv_filename)
                with open(csv_path, 'w', encoding='utf-8') as csv_file:
                    csv_file.write(csv_result)
                
                print(f"Zapisano wynik do pliku: {csv_filename}")
                print("-" * 40)
                print(csv_result[:1000] + "..." if len(csv_result) > 1000 else csv_result)
                print("-" * 40)
            else:
                print(f"Ignoruję plik: {filename} (nie jest plikiem PDF)")
    
    if not found_pdf:
        print("Nie znaleziono żadnych plików PDF w podanym folderze.")

if __name__ == "__main__":
    main()
