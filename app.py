import os
import fitz  # PyMuPDF
import requests
from flask import Flask, render_template, request, send_file
import pdfkit
from io import BytesIO
import json
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Replace this path with where wkhtmltopdf is installed on your system
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

API_KEY = "AIzaSyBnTIV206lefAQ9UZ5h2svdDOwRjg0S14s"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def extract_text_from_pdf(filepath):
    text = ""
    doc = fitz.open(filepath)
    for page in doc:
        text += page.get_text()  # type: ignore
    doc.close()
    return text.strip()

def clean_response_for_json(raw):
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = raw.replace('\r', '').replace('\t', ' ')
    
    # Remove invalid control characters
    raw = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', raw)
    
    # Remove invalid escape characters
    raw = re.sub(r'\\(?!["\\/bfnrtu])', '', raw)
    
    # Remove trailing commas
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)
    
    # Fix smart quotes and apostrophes
    raw = raw.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
    
    # Remove any leading/trailing whitespace and newlines
    raw = raw.strip()
    
    return raw

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("POST request received")
        try:
            # Check if file was uploaded
            if 'resume' not in request.files:
                print("No 'resume' field in request.files")
                return render_template('index.html', error="No file was uploaded.")
            
            file = request.files['resume']
            print(f"File received: {file.filename}")
            
            # Check if file is empty
            if file.filename == '':
                print("Empty filename")
                return render_template('index.html', error="No file was selected.")
            
            # Check if file is a PDF
            if not file.filename or not file.filename.lower().endswith('.pdf'):
                print(f"Invalid file type: {file.filename}")
                return render_template('index.html', error="Please upload a valid PDF file.")
            
            # Save the file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)  # type: ignore
            print(f"Saving file to: {filepath}")
            file.save(filepath)
            
            # Check if file was saved successfully
            if not os.path.exists(filepath):
                print("File was not saved successfully")
                return render_template('index.html', error="Failed to save the uploaded file.")
            
            print("File saved successfully, extracting text...")
            
            # Extract text from PDF
            try:
                resume_text = extract_text_from_pdf(filepath)
                if not resume_text.strip():
                    print("No text extracted from PDF")
                    return render_template('index.html', error="Could not extract text from the PDF. Please ensure it's not password protected or corrupted.")
                print(f"Extracted {len(resume_text)} characters from PDF")
            except Exception as e:
                print(f"Error reading PDF: {str(e)}")
                return render_template('index.html', error=f"Error reading PDF: {str(e)}")

            print("Sending to AI API...")
            prompt = f"""
            Extract the following information from the resume text provided below.
            Structure the output as a JSON object with this schema:
            {{
                "name": "Full Name",
                "email": "Email Address",
                "linkedin": "LinkedIn Profile URL",
                "github": "GitHub Profile URL",
                "education": [{{"degree": "", "major": "", "collegeName": "", "cgpa": "", "startDate": "", "endDate": ""}}],
                "workExperience": [{{"title": "", "company": "", "location": "", "startDate": "", "endDate": "", "description": ""}}],
                "projects": [{{"name": "", "description": "", "technologies": "", "link": ""}}],
                "skills": [],
                "achievements": [],
                "otherInfo": ""
            }}
            Resume Text:
            \"\"\"{resume_text}\"\"\"
            """

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }

            res = requests.post(url, json=payload)
            
            if res.status_code != 200:
                print(f"API Error: {res.status_code} - {res.text}")
                return render_template('index.html', error=f"API Error: {res.status_code} - {res.text}")
            
            print("AI response received, processing...")
            result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Raw AI response length: {len(result_text)}")
            
            cleaned = clean_response_for_json(result_text)
            print(f"Cleaned response length: {len(cleaned)}")

            try:
                structured_data = json.loads(cleaned)
                print("JSON parsed successfully")
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Error at line {e.lineno}, column {e.colno}")
                print(f"Character position: {e.pos}")
                
                # Save both raw and cleaned responses for debugging
                with open("bad_response_raw.json", "w", encoding="utf-8") as f:
                    f.write(result_text)
                with open("bad_response_cleaned.json", "w", encoding="utf-8") as f:
                    f.write(cleaned)
                
                # Try to show the problematic area
                start = max(0, e.pos - 50)
                end = min(len(cleaned), e.pos + 50)
                print(f"Problematic area: {cleaned[start:end]}")
                
                return render_template("index.html", error=f"JSON parsing error: {e.msg} at line {e.lineno}, column {e.colno}. Raw response saved to bad_response_raw.json, cleaned response saved to bad_response_cleaned.json")

            print("Generating PDF...")
            rendered_html = render_template("resume_template.html", data=structured_data)
            pdf_bytes = pdfkit.from_string(rendered_html, False, configuration=PDFKIT_CONFIG)  # type: ignore
            print("PDF generated successfully")
            return send_file(BytesIO(pdf_bytes), download_name="Formatted_Resume.pdf", as_attachment=False)  # type: ignore

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return render_template("index.html", error=f"Unexpected error: {str(e)}")

    print("GET request received")
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)




