#!/usr/bin/env python
# coding: utf-8

from google import genai
from google.genai import types
import pathlib
import httpx
import argparse
import os
from pypdf import PdfReader, PdfWriter
from io import BytesIO

# Load GEMINI_API_KEY from .env file
# Consider using python-dotenv if you want to load from a .env file automatically
# from dotenv import load_dotenv
# load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Gemini Client globally
# This requires GEMINI_API_KEY to be set before this script block is executed.
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it before running the script.")
client = genai.Client(api_key=GEMINI_API_KEY)

def parse_pages_string(pages_str, max_pages):
    """Parses a page string (e.g., "0,1,5-7,10" or "all") into a list of page indices."""
    if pages_str.lower() == "all":
        if max_pages == 0: return [] # Handle empty PDF case
        return list(range(max_pages))
    
    pages_to_send = set()
    parts = pages_str.split(',')
    for part_str in parts:
        part_str = part_str.strip()
        if '-' in part_str:
            try:
                start, end = map(int, part_str.split('-'))
                if not (0 <= start <= end < max_pages):
                    print(f"Warning: Invalid page range '{part_str}' (bounds: 0-{max_pages-1}), ignoring.")
                    continue
                pages_to_send.update(range(start, end + 1))
            except ValueError:
                print(f"Warning: Invalid page range format '{part_str}', ignoring.")
                continue
        else:
            try:
                page_num = int(part_str)
                if not (0 <= page_num < max_pages):
                    print(f"Warning: Invalid page number '{page_num}' (bounds: 0-{max_pages-1}), ignoring.")
                    continue
                pages_to_send.add(page_num)
            except ValueError:
                print(f"Warning: Invalid page number format '{part_str}', ignoring.")
                continue
    
    valid_pages = sorted(list(pages_to_send))
    if not valid_pages and pages_str.lower() != "all":
        print(f"Warning: No valid pages selected from input '{pages_str}'.")
    return valid_pages

def process_pdf_with_gemini(input_pdf_path, output_md_path, gemini_model_name, pages_to_extract_spec):
    """
    Processes a PDF file using the global Gemini client: extracts text from specified pages,
    and writes the output to a markdown file.
    """
    global client # Use the globally initialized client

    try:
        reader = PdfReader(input_pdf_path)
    except FileNotFoundError:
        print(f"Error: Input PDF file not found at '{input_pdf_path}'")
        return
    except Exception as e:
        print(f"Error reading PDF '{input_pdf_path}': {e}")
        return

    num_total_pdf_pages = len(reader.pages)
    if num_total_pdf_pages == 0:
        print(f"Error: No pages found in PDF '{input_pdf_path}'.")
        return
        
    page_indices_to_process = parse_pages_string(pages_to_extract_spec, num_total_pdf_pages)

    if not page_indices_to_process:
        print(f"No valid pages selected from spec '{pages_to_extract_spec}' for PDF with {num_total_pdf_pages} pages. Exiting.")
        return

    writer = PdfWriter()
    for idx in page_indices_to_process:
        writer.add_page(reader.pages[idx])

    pdf_subset_buffer = BytesIO()
    writer.write(pdf_subset_buffer)
    pdf_subset_buffer.seek(0)
    subset_pdf_bytes_data = pdf_subset_buffer.read()

    prompt_text = "Extract the full text of this document with figure/table descriptions. Render the text in markdown format, makeing sure to use LaTeX for equations. Also render any mathematical variables or expressions that are present in the text using inline LaTeX. Pay close attention to proper LaTeX formatting including bracket nesting, and understanding the difference between what is mathematical notation, and what is a text string within an equation. Make sure the latex snippets are properly enclosed using dollar signs so that both the inline LaTex and standalone equations are rendered correctly in markdown. Anything enclosed with $$ is a standalone equation, and anything enclosed with $ is an inline equation. Include full descriptions of any figures and tables in the appropriate places."

    print(f"Sending {len(page_indices_to_process)} pages (indices example: {page_indices_to_process[:10]}{'...' if len(page_indices_to_process) > 10 else ''}) to Gemini model '{gemini_model_name}'...")
    
    try:
        response = client.models.generate_content(
            model=gemini_model_name,
            contents=[
                types.Part.from_bytes(data=subset_pdf_bytes_data, mime_type="application/pdf"),
                prompt_text
            ]
        )
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"API Error Response: {e.response.text}")
        elif hasattr(e, 'message'):
             print(f"API Error Message: {e.message}")
        return

    print("\nFirst 500 characters of response from Gemini:")
    if hasattr(response, 'text') and response.text:
        generated_text_content = response.text
        print(generated_text_content[:500])
        
        output_directory = os.path.dirname(output_md_path)
        if output_directory and not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
                print(f"Created output directory: {output_directory}")
            except OSError as ose:
                print(f"Error creating output directory '{output_directory}': {ose}")
                return

        try:
            with open(output_md_path, "w", encoding='utf-8') as f:
                f.write(generated_text_content)
            print(f"\nFull response written to: {output_md_path}")
        except IOError as e_io:
            print(f"Error writing output file '{output_md_path}': {e_io}")
    elif hasattr(response, 'prompt_feedback'):
         print("Content generation possibly blocked or failed due to safety settings or other reasons.")
         print(f"Prompt Feedback: {response.prompt_feedback}")
    else:
        print("No text content in response or response structure unexpected.")
        print(f"Full response object: {response}")

def main():
    parser = argparse.ArgumentParser(
        description="Process a PDF with Gemini: extract text from specified pages to Markdown.",
        formatter_class=argparse.RawTextHelpFormatter, # Allows for better formatting of epilog
        epilog='''Usage examples:
  Process all pages of the default PDF and save to default output:
    python %(prog)s

  Process specific pages of a PDF:
    python %(prog)s -i my_document.pdf -o output.md -p "0,1,5-7,10"

  Process first 5 pages using a different model:
    python %(prog)s -i another.pdf -m "gemini-1.5-pro-latest" -p "0-4"

  Get help:
    python %(prog)s -h
'''
    )
    parser.add_argument(
        "-i", "--input_file",
        default="../papers/reasoning/202501/DeepSeek_R1.pdf",
        type=str,
        help="Path to the input PDF file. (default: %(default)s)"
    )
    parser.add_argument(
        "-o", "--output_file",
        default="../papers/cot/DeepSeek_R1.md",
        type=str,
        help="Path to the output Markdown file. (default: %(default)s)"
    )
    parser.add_argument(
        "-m", "--model_name",
        default="gemini-2.5-flash-preview-05-20", 
        type=str,
        help="Gemini model name to use (e.g., 'gemini-2.5-flash-latest'). (default: %(default)s)"
    )
    parser.add_argument(
        "-p", "--pages",
        default="all",
        type=str,
        help="Pages to process. Comma-separated, can include ranges (e.g., '0,1,5-7,10') or 'all'. (default: %(default)s)"
    )
    
    args = parser.parse_args()

    # API key and client are initialized globally. If client is None, it means API key was missing.
    if client is None:
        # The initial check for GEMINI_API_KEY should have caught this and raised ValueError.
        # This is an additional safeguard.
        print("Error: Gemini client not initialized. GEMINI_API_KEY might be missing or invalid.")
        return

    process_pdf_with_gemini(args.input_file, args.output_file, args.model_name, args.pages)

if __name__ == "__main__":
    main()
