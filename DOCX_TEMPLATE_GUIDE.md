# DOCX Template Guide

## Overview

The Resume Formatter now supports Microsoft Word (DOCX) templates, allowing you to create personalized resume layouts using familiar Word formatting while maintaining the same high-quality AI-powered data extraction.

## How to Use DOCX Templates

### 1. Enable Custom Template Mode
- Check the "Use Custom Template" checkbox on the upload form
- Upload your DOCX template file (`.docx` format)
- Upload your resume PDF(s) as usual
- Process as normal

### 2. Download Sample DOCX Template
- Click the "Download Sample DOCX Template" link in the custom template section
- Use this as a starting point for your own templates

## Creating DOCX Templates

### Step 1: Open Microsoft Word
- Create a new document or open an existing one
- Set up your desired formatting (fonts, colors, layout, etc.)

### Step 2: Add Placeholders
Use the following Jinja2-style placeholders in your Word document:

#### Basic Information
```
{{ data.name }}              <!-- Full Name -->
{{ data.email }}             <!-- Email Address -->
{{ data.phone }}             <!-- Phone Number -->
{{ data.linkedin }}          <!-- LinkedIn URL -->
{{ data.github }}            <!-- GitHub URL -->
{{ data.otherInfo }}         <!-- Additional Information -->
```

#### Professional Information
```
{{ generated_professional_title }}  <!-- AI-generated professional title -->
{{ generated_profile_summary }}     <!-- AI-generated profile summary -->
{{ generated_soft_skills }}         <!-- AI-generated soft skills -->
```

#### Work Experience
```
{% for job in data.workExperience %}
    {{ job.title }}          <!-- Job Title -->
    {{ job.company }}        <!-- Company Name -->
    {{ job.location }}       <!-- Location -->
    {{ job.startDate }}      <!-- Start Date -->
    {{ job.endDate }}        <!-- End Date -->
    {{ job.description }}    <!-- Job Description -->
{% endfor %}
```

#### Education
```
{% for edu in data.education %}
    {{ edu.degree }}         <!-- Degree -->
    {{ edu.major }}          <!-- Major/Field of Study -->
    {{ edu.collegeName }}    <!-- Institution Name -->
    {{ edu.cgpa }}           <!-- CGPA/GPA -->
    {{ edu.startDate }}      <!-- Start Date -->
    {{ edu.endDate }}        <!-- End Date -->
{% endfor %}
```

#### Skills
```
{% for skill in data.skills %}
    {{ skill }}              <!-- Individual Skill -->
{% endfor %}
```

#### Projects
```
{% for project in data.projects %}
    {{ project.name }}       <!-- Project Name -->
    {{ project.description }} <!-- Project Description -->
    {{ project.technologies }} <!-- Technologies Used -->
    {{ project.link }}       <!-- Project Link -->
{% endfor %}
```

#### Achievements
```
{% for achievement in data.achievements %}
    {{ achievement }}        <!-- Individual Achievement -->
{% endfor %}
```

## Template Structure Example

Here's a basic DOCX template structure:

### Header Section
```
[Your Name]                    {{ data.name }}
[Professional Title]           {{ generated_professional_title }}

Contact Information:
Email: {{ data.email }}
Phone: {{ data.phone }}
LinkedIn: {{ data.linkedin }}
GitHub: {{ data.github }}
```

### Profile Summary
```
PROFILE SUMMARY
{{ generated_profile_summary }}
```

### Skills Section
```
TECHNICAL SKILLS
{% for skill in data.skills %}
• {{ skill }}
{% endfor %}

SOFT SKILLS
{% for skill in generated_soft_skills %}
• {{ skill }}
{% endfor %}
```

### Work Experience
```
WORK EXPERIENCE
{% for job in data.workExperience %}
{{ job.title }} at {{ job.company }}
{{ job.startDate }} - {{ job.endDate }}
{{ job.description }}

{% endfor %}
```

### Education
```
EDUCATION
{% for edu in data.education %}
{{ edu.degree }} in {{ edu.major }}
{{ edu.collegeName }}
{{ edu.startDate }} - {{ edu.endDate }}
{% if edu.cgpa %}CGPA: {{ edu.cgpa }}{% endif %}

{% endfor %}
```

## Best Practices

### 1. Use Conditional Rendering
Always check if data exists before displaying it:
```
{% if data.workExperience %}
WORK EXPERIENCE
{% for job in data.workExperience %}
    {{ job.title }} at {{ job.company }}
{% endfor %}
{% endif %}
```

### 2. Provide Fallbacks
Use the `or` operator for default values:
```
{{ data.name or 'Full Name' }}
{{ job.title or 'Job Title' }}
```

### 3. Formatting Tips
- **Bold important information**: Use Word's bold formatting for names, titles, and section headers
- **Use consistent spacing**: Maintain consistent paragraph spacing throughout
- **Professional fonts**: Use professional fonts like Arial, Calibri, or Times New Roman
- **Page margins**: Set appropriate page margins (0.5-1 inch recommended)
- **Single page**: Design your template to fit on one page

### 4. Advanced Formatting
- **Tables**: You can use Word tables with placeholders in cells
- **Bullet points**: Use Word's bullet point feature for lists
- **Headers and footers**: Add placeholders in headers/footers if needed
- **Page breaks**: Use page breaks to control layout

## Template Validation

The system automatically validates your DOCX template by:
1. Checking for valid DOCX format
2. Testing with sample data
3. Ensuring all required variables are accessible

If validation fails, you'll receive a specific error message.

## Common Issues and Solutions

### 1. Template Not Rendering
- **Issue**: Template fails to render with data
- **Solution**: Check that all placeholders use correct Jinja2 syntax
- **Check**: Ensure no typos in variable names

### 2. Missing Data
- **Issue**: Some sections appear empty
- **Solution**: Use conditional rendering to check if data exists
- **Example**: `{% if data.skills %}...{% endif %}`

### 3. Formatting Issues
- **Issue**: PDF output doesn't match Word formatting
- **Solution**: Keep formatting simple and avoid complex Word features
- **Tip**: Test with the sample template first

### 4. File Size Issues
- **Issue**: Template file is too large
- **Solution**: Remove unnecessary images or complex formatting
- **Limit**: Keep template under 5MB

## Advanced Features

### Custom Sections
You can add sections not in the default template:
```
{% if data.certifications %}
CERTIFICATIONS
{% for cert in data.certifications %}
{{ cert.name }} - {{ cert.issuer }} ({{ cert.date }})
{% endfor %}
{% endif %}
```

### Conditional Formatting
```
{% for skill in data.skills %}
{% if 'Python' in skill %}
• {{ skill }} (Expert)
{% else %}
• {{ skill }}
{% endif %}
{% endfor %}
```

### Custom Variables
The system provides these additional variables:
- `generated_professional_title`: AI-generated professional title
- `generated_profile_summary`: AI-generated profile summary  
- `generated_soft_skills`: AI-generated soft skills list

## Troubleshooting

### Common Errors

1. **"Template validation failed"**: Check Jinja2 syntax and variable names
2. **"Error rendering DOCX template"**: Ensure template is valid DOCX format
3. **"File not found"**: Make sure you're uploading a .docx file
4. **"Conversion failed"**: Check if Word is properly installed on the system

### Debug Tips

1. Start with the sample DOCX template and modify gradually
2. Test with simple placeholders first
3. Use Word's spell check to catch typos in placeholders
4. Save your template frequently while editing

## Support

If you encounter issues with DOCX templates:
1. Verify your template syntax
2. Check that all variables are properly referenced
3. Ensure your DOCX file is valid and not corrupted
4. Test with the sample template first

The system maintains the same high accuracy in data extraction regardless of the template format used.

## Comparison: HTML vs DOCX Templates

| Feature | HTML Templates | DOCX Templates |
|---------|---------------|----------------|
| **Ease of Creation** | Requires HTML/CSS knowledge | Familiar Word interface |
| **Formatting Control** | Full CSS control | Word formatting features |
| **Complexity** | More complex for beginners | Easier for most users |
| **Customization** | Unlimited styling options | Limited to Word features |
| **File Size** | Usually smaller | Can be larger |
| **Compatibility** | Works on all systems | Requires Word or compatible software |

Choose the template format that best suits your needs and technical comfort level. 