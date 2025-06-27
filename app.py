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

# Replace this path with where wkhtmltopdf is installed on your system
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

API_KEY = "AIzaSyBnTIV206lefAQ9UZ5h2svdDOwRjg0S14s"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def extract_text_from_pdf(filepath):
    text = ""
    with fitz.open(filepath) as pdf:
        for page in pdf:
            text += page.get_text()
    return text.strip()

def clean_response_for_json(raw):
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = raw.replace('\r', '').replace('\t', ' ')
    raw = re.sub(r'\\(?!["\\/bfnrtu])', '', raw)  # Remove invalid escape characters
    raw = re.sub(r',(\s*[}\]])', r'\1', raw)  # Remove trailing commas
    raw = raw.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return raw

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['resume']
        if not file or not file.filename.endswith('.pdf'):
            return render_template('index.html', error="Please upload a valid PDF file.")

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        resume_text = extract_text_from_pdf(filepath)

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

        try:
            res = requests.post(url, json=payload)
            result_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            cleaned = clean_response_for_json(result_text)

            try:
                structured_data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                with open("bad_response.json", "w", encoding="utf-8") as f:
                    f.write(cleaned)
                return render_template("index.html", error=f"JSON parsing error: {e.msg} at line {e.lineno}, column {e.colno}. Raw response saved to bad_response.json")

            rendered_html = render_template("resume_template.html", data=structured_data)
            pdf = pdfkit.from_string(rendered_html, False, configuration=PDFKIT_CONFIG)
            return send_file(BytesIO(pdf), download_name="Formatted_Resume.pdf", as_attachment=False)

        except Exception as e:
            return render_template("index.html", error=f"Error parsing response: {str(e)}")

    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
