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
import platform


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size for batch processing

# Replace this path with where wkhtmltopdf is installed on your system
if platform.system() == "Windows":
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
else:
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY")

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

def infer_professional_title(data):
    # Use most recent work experience with both title and company if available
    if data.get("workExperience"):
        for job in data["workExperience"]:
            if job.get("title") and job.get("company"):
                return f"{job['title']} at {job['company']}"
        # Fallback: just title
        for job in data["workExperience"]:
            if job.get("title"):
                return job["title"]
    # Use most recent education if no work experience
    if data.get("education"):
        edu = data["education"][0]
        if edu.get("degree") and edu.get("major"):
            return f"Recent {edu['degree']} in {edu['major']} Graduate"
        elif edu.get("degree"):
            return f"Recent {edu['degree']} Graduate"
    # Use top skills
    if data.get("skills"):
        return f"Specialist in {', '.join([s for s in data['skills'][:2] if s])}"
    return "Professional Title"

def infer_profile_summary(data):
    title = data.get("title") or infer_professional_title(data)
    skills = data.get("skills", [])
    skills_str = ", ".join([s for s in skills[:4] if s]) if skills else ""
    years = ""
    # Try to infer years of experience from all work experiences
    if data.get("workExperience"):
        from datetime import datetime
        years_list = []
        for job in data["workExperience"]:
            start = job.get("startDate", "")
            end = job.get("endDate", "") or str(datetime.now().year)
            try:
                start_year = int(''.join(filter(str.isdigit, start))[:4])
                end_year = int(''.join(filter(str.isdigit, end))[:4])
                years_list.append(end_year - start_year)
            except Exception:
                continue
        if years_list:
            total_years = sum([y for y in years_list if y > 0])
            if total_years > 0:
                years = f" with {total_years} years of experience"
    elif data.get("education"):
        edu = data["education"][0]
        if edu.get("degree"):
            years = f", {edu['degree']} graduate"
    # Try to infer industry/technologies from work/project descriptions
    techs = set()
    for job in data.get("workExperience", []):
        desc = (job.get("description") or "").lower()
        for skill in skills:
            if skill and skill.lower() in desc:
                techs.add(skill)
    for proj in data.get("projects", []):
        desc = (proj.get("description") or "").lower()
        for skill in skills:
            if skill and skill.lower() in desc:
                techs.add(skill)
    techs_str = ", ".join([t for t in list(techs)[:3] if t])
    summary = f"I am {title}{years}"
    if techs_str:
        summary += f" with hands-on experience in {techs_str}"
    elif skills_str:
        summary += f" with expertise in {skills_str}"
    summary += "."
    return summary

def infer_soft_skills(data):
    soft_skills = set()
    # Combine all text sources
    achievements = " ".join([a for a in data.get("achievements", []) if a])
    projects = " ".join([p.get("description", "") or "" for p in data.get("projects", [])])
    work = " ".join([(w.get("description", "") or "") for w in data.get("workExperience", [])])
    job_titles = " ".join([(w.get("title", "") or "") for w in data.get("workExperience", [])])
    edu_text = " ".join([(e.get("degree", "") or "") + " " + (e.get("major", "") or "") for e in data.get("education", [])])
    text = f"{achievements} {projects} {work} {job_titles} {edu_text}".lower()
    # Keyword-based inference
    if any(word in text for word in ["lead", "led", "team", "collaborate", "mentored", "managed"]):
        soft_skills.add("Leadership")
        soft_skills.add("Collaboration")
    if any(word in text for word in ["presented", "communicated", "reported", "wrote", "documented"]):
        soft_skills.add("Presentation")
        soft_skills.add("Communication")
    if any(word in text for word in ["deadline", "fast-paced", "timely", "delivered", "prioritize", "organized"]):
        soft_skills.add("Time Management")
        soft_skills.add("Adaptability")
    if any(word in text for word in ["analyze", "solved", "troubleshoot", "problem", "critical thinking"]):
        soft_skills.add("Problem Solving")
        soft_skills.add("Analytical Thinking")
    if not soft_skills:
        soft_skills = {"Teamwork", "Communication", "Problem Solving"}
    return sorted([s for s in soft_skills if s])

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
            "phone": "Phone Number",
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

        # --- Fallback logic for missing fields ---
        # Professional Title
        if not structured_data.get("title"):
            structured_data["title"] = infer_professional_title(structured_data)
        generated_professional_title = structured_data["title"]

        # Profile Summary
        if not structured_data.get("profileSummary"):
            structured_data["profileSummary"] = infer_profile_summary(structured_data)
        generated_profile_summary = structured_data["profileSummary"]

        # Soft Skills
        if not structured_data.get("softSkills"):
            generated_soft_skills = infer_soft_skills(structured_data)
        else:
            generated_soft_skills = structured_data["softSkills"]

        # Generate PDF
        abs_img_path = os.path.abspath(os.path.join('templates', 'CV_Sample_files')).replace('\\', '/')
        print("ABS IMG PATH:", abs_img_path)
        rendered_html = render_template(
            "resume_template.html",
            data=structured_data,
            abs_img_path=abs_img_path,
            generated_profile_summary=generated_profile_summary,
            generated_professional_title=generated_professional_title,
            generated_soft_skills=generated_soft_skills
        )
        pdf_bytes = pdfkit.from_string(
            rendered_html, 
            False, 
            configuration=PDFKIT_CONFIG, 
            options={'enable-local-file-access': ''}
        )
        
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




