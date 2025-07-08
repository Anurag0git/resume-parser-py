# Custom Template Guide

## Overview

The Resume Formatter now supports custom HTML templates, allowing you to create personalized resume layouts while maintaining the same high-quality AI-powered data extraction.

## How to Use Custom Templates

### 1. Enable Custom Template Mode
- Check the "Use Custom Template" checkbox on the upload form
- Upload your HTML template file (`.html` or `.htm` format)
- Upload your resume PDF(s) as usual
- Process as normal

### 2. Download Sample Template
- Click the "Download Sample Template" link in the custom template section
- Use this as a starting point for your own templates

## Template Variables

Your custom template can use the following Jinja2 variables:

### Main Data Object (`data`)
```html
{{ data.name }}              <!-- Full Name -->
{{ data.email }}             <!-- Email Address -->
{{ data.phone }}             <!-- Phone Number -->
{{ data.linkedin }}          <!-- LinkedIn URL -->
{{ data.github }}            <!-- GitHub URL -->
{{ data.otherInfo }}         <!-- Additional Information -->
```

### Work Experience (`data.workExperience`)
```html
{% for job in data.workExperience %}
    {{ job.title }}          <!-- Job Title -->
    {{ job.company }}        <!-- Company Name -->
    {{ job.location }}       <!-- Location -->
    {{ job.startDate }}      <!-- Start Date -->
    {{ job.endDate }}        <!-- End Date -->
    {{ job.description }}    <!-- Job Description -->
{% endfor %}
```

### Education (`data.education`)
```html
{% for edu in data.education %}
    {{ edu.degree }}         <!-- Degree -->
    {{ edu.major }}          <!-- Major/Field of Study -->
    {{ edu.collegeName }}    <!-- Institution Name -->
    {{ edu.cgpa }}           <!-- CGPA/GPA -->
    {{ edu.startDate }}      <!-- Start Date -->
    {{ edu.endDate }}        <!-- End Date -->
{% endfor %}
```

### Skills (`data.skills`)
```html
{% for skill in data.skills %}
    {{ skill }}              <!-- Individual Skill -->
{% endfor %}
```

### Projects (`data.projects`)
```html
{% for project in data.projects %}
    {{ project.name }}       <!-- Project Name -->
    {{ project.description }} <!-- Project Description -->
    {{ project.technologies }} <!-- Technologies Used -->
    {{ project.link }}       <!-- Project Link -->
{% endfor %}
```

### Achievements (`data.achievements`)
```html
{% for achievement in data.achievements %}
    {{ achievement }}        <!-- Individual Achievement -->
{% endfor %}
```

### Generated Fields
```html
{{ generated_professional_title }}  <!-- AI-generated professional title -->
{{ generated_profile_summary }}     <!-- AI-generated profile summary -->
{{ generated_soft_skills }}         <!-- AI-generated soft skills -->
```

## Template Structure Example

Here's a basic template structure:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ data.name }} - Resume</title>
    <style>
        /* Your CSS styles here */
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{{ data.name }}</h1>
        <p>{{ generated_professional_title }}</p>
        <p>{{ data.email }} | {{ data.phone }}</p>
    </div>

    <!-- Profile Summary -->
    {% if generated_profile_summary %}
    <div class="section">
        <h2>Profile Summary</h2>
        <p>{{ generated_profile_summary }}</p>
    </div>
    {% endif %}

    <!-- Work Experience -->
    {% if data.workExperience %}
    <div class="section">
        <h2>Work Experience</h2>
        {% for job in data.workExperience %}
        <div class="job">
            <h3>{{ job.title }} at {{ job.company }}</h3>
            <p>{{ job.startDate }} - {{ job.endDate }}</p>
            <p>{{ job.description }}</p>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <!-- Skills -->
    {% if data.skills %}
    <div class="section">
        <h2>Skills</h2>
        <ul>
        {% for skill in data.skills %}
            <li>{{ skill }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
</body>
</html>
```

## Best Practices

### 1. Use Conditional Rendering
Always check if data exists before displaying it:
```html
{% if data.workExperience %}
    <!-- Display work experience -->
{% endif %}
```

### 2. Provide Fallbacks
Use the `or` operator for default values:
```html
{{ data.name or 'Full Name' }}
{{ job.title or 'Job Title' }}
```

### 3. Responsive Design
Include CSS for both screen and print:
```css
@media print {
    /* Print-specific styles */
}
@page { margin: 0.5in; }
```

### 4. Error Handling
The system validates templates before processing. Common issues:
- Missing closing tags
- Invalid Jinja2 syntax
- Missing required variables

## Template Validation

The system automatically validates your template by:
1. Checking for valid HTML syntax
2. Testing with sample data
3. Ensuring all required variables are accessible

If validation fails, you'll receive a specific error message.

## Advanced Features

### Custom Styling
You can include any CSS in your template:
```html
<style>
    .custom-section {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
    }
</style>
```

### Conditional Formatting
```html
{% for skill in data.skills %}
    <span class="skill {% if 'Python' in skill %}highlight{% endif %}">
        {{ skill }}
    </span>
{% endfor %}
```

### Custom Sections
You can add sections not in the default template:
```html
{% if data.certifications %}
<div class="section">
    <h2>Certifications</h2>
    {% for cert in data.certifications %}
        <p>{{ cert.name }} - {{ cert.issuer }} ({{ cert.date }})</p>
    {% endfor %}
</div>
{% endif %}
```

## Troubleshooting

### Common Issues

1. **Template not rendering**: Check for syntax errors in Jinja2 variables
2. **Missing data**: Ensure you're using the correct variable names
3. **Styling issues**: Test your CSS in a browser first
4. **PDF generation fails**: Check for unsupported CSS properties

### Debug Tips

1. Start with the sample template and modify gradually
2. Test with simple data first
3. Use browser developer tools to preview HTML
4. Check the console for error messages

## Support

If you encounter issues with custom templates:
1. Verify your template syntax
2. Check that all variables are properly referenced
3. Ensure your HTML is valid
4. Test with the sample template first

The system maintains the same high accuracy in data extraction regardless of the template used. 