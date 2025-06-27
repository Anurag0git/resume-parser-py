import os
import fitz  # PyMuPDF
import requests
from flask import Flask, render_template, request, send_file
import pdfkit
from io import BytesIO
import json
import re
import zipfile
from datetime import datetime
from dotenv import load_dotenv


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size for batch processing

# Replace this path with where wkhtmltopdf is installed on your system
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")

print("Loaded API KEY:", API_KEY)

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

def process_single_resume(filepath):
    """Process a single resume and return the formatted PDF"""
    try:
        # Extract text from PDF
        resume_text = extract_text_from_pdf(filepath)
        if not resume_text.strip():
            return None, "Could not extract text from the PDF. Please ensure it's not password protected or corrupted."

        # Send to AI API
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
            return None, f"API Error: {res.status_code} - {res.text}"
        
        result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned = clean_response_for_json(result_text)

        try:
            structured_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return None, f"JSON parsing error: {e.msg} at line {e.lineno}, column {e.colno}"

        # Generate PDF
        rendered_html = render_template("resume_template.html", data=structured_data)
        pdf_bytes = pdfkit.from_string(rendered_html, False, configuration=PDFKIT_CONFIG)  # type: ignore
        
        return pdf_bytes, None
        
    except Exception as e:
        return None, f"Error processing resume: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("POST request received")
        try:
            # Check if files were uploaded
            if 'resume' not in request.files:
                print("No 'resume' field in request.files")
                return render_template('index.html', error="No files were uploaded.")
            
            files = request.files.getlist('resume')
            batch_mode = request.form.get('batch_mode') == 'on'
            
            if not files or all(file.filename == '' for file in files):
                print("No files selected")
                return render_template('index.html', error="No files were selected.")
            
            # Filter PDF files
            pdf_files = [file for file in files if file.filename and file.filename.lower().endswith('.pdf')]
            if not pdf_files:
                return render_template('index.html', error="Please upload valid PDF files.")
            
            print(f"Processing {len(pdf_files)} PDF files")
            
            # Single file processing
            if len(pdf_files) == 1 or not batch_mode:
                file = pdf_files[0]
                if not file.filename:
                    return render_template('index.html', error="Invalid filename.")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)
                
                pdf_bytes, error = process_single_resume(filepath)
                if error:
                    return render_template('index.html', error=error)
                
                return send_file(BytesIO(pdf_bytes), download_name="Formatted_Resume.pdf", as_attachment=False)  # type: ignore
            
            # Batch processing
            else:
                print("Starting batch processing...")
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    successful_count = 0
                    failed_count = 0
                    
                    for i, file in enumerate(pdf_files):
                        if not file.filename:
                            continue
                        print(f"Processing file {i+1}/{len(pdf_files)}: {file.filename}")
                        
                        # Save file temporarily
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                        file.save(filepath)
                        
                        # Process the resume
                        pdf_bytes, error = process_single_resume(filepath)
                        
                        if pdf_bytes:
                            # Add to zip with a clean filename
                            clean_name = os.path.splitext(file.filename)[0].replace(' ', '_')
                            zip_file.writestr(f"{clean_name}_Formatted.pdf", pdf_bytes)  # type: ignore
                            successful_count += 1
                        else:
                            # Add error log to zip
                            zip_file.writestr(f"{file.filename}_ERROR.txt", f"Failed to process: {error}")  # type: ignore
                            failed_count += 1
                        
                        # Clean up temporary file
                        try:
                            os.remove(filepath)
                        except:
                            pass
                
                zip_buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return send_file(
                    zip_buffer, 
                    download_name=f"Formatted_Resumes_{timestamp}.zip", 
                    as_attachment=True,
                    mimetype='application/zip'
                )

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return render_template("index.html", error=f"Unexpected error: {str(e)}")

    print("GET request received")
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)




