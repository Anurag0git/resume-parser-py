import os
import fitz  
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
from jinja2 import Template
from docxtpl import DocxTemplate
import tempfile


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

def process_custom_template(template_file):
    """Process uploaded custom template and return template object"""
    try:
        # Read the template content
        template_content = template_file.read().decode('utf-8')
        template_file.seek(0)  # Reset file pointer for potential reuse
        
        # Create Jinja2 template object
        template = Template(template_content)
        
        # Basic validation - check if template has basic resume variables
        test_data = {
            "name": "Test Name",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "linkedin": "https://linkedin.com/in/test",
            "github": "https://github.com/test",
            "workExperience": [],
            "education": [],
            "skills": [],
            "projects": [],
            "achievements": [],
            "otherInfo": ""
        }
        
        # Try to render with test data to catch basic syntax errors
        try:
            template.render(
                data=test_data,
                abs_img_path="/test/path",
                generated_profile_summary="Test profile summary",
                generated_professional_title="Test Professional Title",
                generated_soft_skills=["Test Skill 1", "Test Skill 2"]
            )
        except Exception as e:
            return None, f"Template validation failed: {str(e)}"
        
        return template, None
        
    except Exception as e:
        return None, f"Error processing template: {str(e)}"

def process_docx_template(template_file):
    """Process uploaded DOCX template and return template object"""
    try:
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            template_file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Create DocxTemplate object
        doc = DocxTemplate(temp_path)
        
        # Basic validation - check if template has basic resume variables
        test_data = {
            "name": "Test Name",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "linkedin": "https://linkedin.com/in/test",
            "github": "https://github.com/test",
            "workExperience": [],
            "education": [],
            "skills": [],
            "projects": [],
            "achievements": [],
            "otherInfo": ""
        }
        
        # Try to render with test data to catch basic syntax errors
        try:
            test_context = {
                "data": test_data,
                "generated_profile_summary": "Test profile summary",
                "generated_professional_title": "Test Professional Title",
                "generated_soft_skills": ["Test Skill 1", "Test Skill 2"]
            }
            doc.render(test_context)
        except Exception as e:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            return None, f"DOCX template validation failed: {str(e)}"
        
        return doc, temp_path
        
    except Exception as e:
        # Clean up temp file if it exists
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass
        return None, f"Error processing DOCX template: {str(e)}"

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

def process_single_resume(filepath, custom_template=None, template_type="html"):
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

        # Generate output based on template type
        if custom_template:
            if template_type == "docx":
                # Use DOCX template
                try:
                    # Render the DOCX template
                    context = {
                        "data": structured_data,
                        "generated_profile_summary": generated_profile_summary,
                        "generated_professional_title": generated_professional_title,
                        "generated_soft_skills": generated_soft_skills
                    }
                    custom_template.render(context)
                    
                    # Save the rendered DOCX to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_docx:
                        custom_template.save(temp_docx.name)
                        docx_path = temp_docx.name
                    
                    # Read the DOCX bytes
                    with open(docx_path, 'rb') as f:
                        docx_bytes = f.read()
                    
                    # Clean up temporary file
                    try:
                        os.unlink(docx_path)
                    except:
                        pass
                    
                    return docx_bytes, 'docx'
                    
                except Exception as e:
                    return None, f"Error rendering DOCX template: {str(e)}"
            else:
                # Use HTML template
                try:
                    abs_img_path = os.path.abspath(os.path.join('templates', 'CV_Sample_files')).replace('\\', '/')
                    rendered_html = custom_template.render(
                        data=structured_data,
                        abs_img_path=abs_img_path,
                        generated_profile_summary=generated_profile_summary,
                        generated_professional_title=generated_professional_title,
                        generated_soft_skills=generated_soft_skills
                    )
                    
                    options = {
                        'enable-local-file-access': '',
                        'encoding': 'UTF-8',
                        'disable-smart-shrinking': '',
                        'zoom': '1.0',
                        'minimum-font-size': '12'
                    }
                    pdf_bytes = pdfkit.from_string(
                        rendered_html, 
                        False, 
                        configuration=PDFKIT_CONFIG, 
                        options=options
                    )
                    
                    return pdf_bytes, None
                    
                except Exception as e:
                    return None, f"Error rendering HTML template: {str(e)}"
        else:
            # Use default HTML template
            abs_img_path = os.path.abspath(os.path.join('templates', 'CV_Sample_files')).replace('\\', '/')
            rendered_html = render_template(
                "resume_template.html",
                data=structured_data,
                abs_img_path=abs_img_path,
                generated_profile_summary=generated_profile_summary,
                generated_professional_title=generated_professional_title,
                generated_soft_skills=generated_soft_skills
            )
            
            options = {
                'enable-local-file-access': '',
                'encoding': 'UTF-8',
                'disable-smart-shrinking': '',
                'zoom': '1.0',
                'minimum-font-size': '12'
            }
            pdf_bytes = pdfkit.from_string(
                rendered_html, 
                False, 
                configuration=PDFKIT_CONFIG, 
                options=options
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
            custom_template_mode = request.form.get('custom_template') == 'on'
            
            if not files or all(file.filename == '' for file in files):
                print("No files selected")
                return render_template('index.html', error="No files were selected.")
            
            # Filter PDF files
            pdf_files = [file for file in files if file.filename and file.filename.lower().endswith('.pdf')]
            if not pdf_files:
                return render_template('index.html', error="Please upload valid PDF files.")
            
            # Process custom template if provided
            custom_template = None
            template_type = "html"
            template_temp_path = None
            
            if custom_template_mode:
                if 'template' not in request.files:
                    return render_template('index.html', error="Custom template mode enabled but no template file uploaded.")
                
                template_file = request.files['template']
                if not template_file.filename:
                    return render_template('index.html', error="No template file selected.")
                
                # Check file extension
                file_extension = template_file.filename.lower()
                if file_extension.endswith(('.html', '.htm')):
                    custom_template, template_error = process_custom_template(template_file)
                    template_type = "html"
                elif file_extension.endswith('.docx'):
                    custom_template, template_temp_path = process_docx_template(template_file)
                    template_type = "docx"
                    if template_temp_path is None:
                        template_error = custom_template  # In this case, custom_template contains the error
                        custom_template = None
                    else:
                        template_error = None
                else:
                    return render_template('index.html', error="Please upload a valid HTML (.html/.htm) or DOCX (.docx) template file.")
                
                if template_error:
                    return render_template('index.html', error=template_error)
            
            print(f"Processing {len(pdf_files)} PDF files")
            
            # Single file processing
            if len(pdf_files) == 1 or not batch_mode:
                file = pdf_files[0]
                if not file.filename:
                    return render_template('index.html', error="Invalid filename.")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)
                
                pdf_bytes, error = process_single_resume(filepath, custom_template, template_type)
                if error:
                    return render_template('index.html', error=error)
                
                if isinstance(pdf_bytes, tuple) and pdf_bytes[1] == 'docx':
                    return send_file(BytesIO(pdf_bytes[0]), download_name="Formatted_Resume.docx", as_attachment=True)
                else:
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
                        
                        # Process the resume with custom template if provided
                        pdf_bytes, error = process_single_resume(filepath, custom_template, template_type)
                        
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
        finally:
            # Clean up DOCX template temporary file if it exists
            if template_temp_path and os.path.exists(template_temp_path):
                try:
                    os.unlink(template_temp_path)
                except:
                    pass

    print("GET request received")
    return render_template("index.html")

@app.route('/download-sample-template')
def download_sample_template():
    """Download the sample HTML template"""
    try:
        template_path = os.path.join('templates', 'sample_custom_template.html')
        return send_file(template_path, download_name="sample_custom_template.html", as_attachment=True)
    except Exception as e:
        return render_template('index.html', error=f"Error downloading template: {str(e)}")

@app.route('/download-sample-docx-template')
def download_sample_docx_template():
    """Download the sample DOCX template"""
    try:
        template_path = os.path.join('templates', 'sample_docx_template.docx')
        return send_file(template_path, download_name="sample_docx_template.docx", as_attachment=True)
    except Exception as e:
        return render_template('index.html', error=f"Error downloading template: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)




