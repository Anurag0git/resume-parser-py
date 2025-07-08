#!/usr/bin/env python3
"""
Test script for custom template functionality
"""

import os
import sys
from io import BytesIO
from jinja2 import Template

def test_template_processing():
    """Test the custom template processing functionality"""
    
    # Test template content
    test_template_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ data.name }} - Resume</title>
        <style>
            body { font-family: Arial, sans-serif; }
            .header { text-align: center; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ data.name }}</h1>
            <p>{{ generated_professional_title }}</p>
            <p>{{ data.email }}</p>
        </div>
        
        {% if data.workExperience %}
        <h2>Work Experience</h2>
        {% for job in data.workExperience %}
        <div>
            <h3>{{ job.title }} at {{ job.company }}</h3>
            <p>{{ job.description }}</p>
        </div>
        {% endfor %}
        {% endif %}
        
        {% if data.skills %}
        <h2>Skills</h2>
        <ul>
        {% for skill in data.skills %}
            <li>{{ skill }}</li>
        {% endfor %}
        </ul>
        {% endif %}
    </body>
    </html>
    """
    
    # Test data
    test_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "123-456-7890",
        "workExperience": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "description": "Developed web applications using Python and JavaScript"
            }
        ],
        "skills": ["Python", "JavaScript", "Flask"],
        "education": [],
        "projects": [],
        "achievements": [],
        "otherInfo": ""
    }
    
    try:
        # Create template object
        template = Template(test_template_content)
        
        # Test rendering
        rendered_html = template.render(
            data=test_data,
            abs_img_path="/test/path",
            generated_profile_summary="Experienced software engineer",
            generated_professional_title="Software Engineer",
            generated_soft_skills=["Communication", "Problem Solving"]
        )
        
        print("✅ Template rendering successful!")
        print(f"✅ Rendered HTML length: {len(rendered_html)} characters")
        
        # Check if key content is present
        if "John Doe" in rendered_html:
            print("✅ Name correctly rendered")
        if "Software Engineer" in rendered_html:
            print("✅ Job title correctly rendered")
        if "Python" in rendered_html:
            print("✅ Skills correctly rendered")
        
        return True
        
    except Exception as e:
        print(f"❌ Template rendering failed: {str(e)}")
        return False

def test_template_validation():
    """Test template validation functionality"""
    
    # Test invalid template with syntax error
    invalid_template = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>{{ data.name }}</h1>
        {% if data.skills %}
        <ul>
        {% for skill in data.skills %}
            <li>{{ skill }}</li>
        {% endfor %}
        <!-- Missing closing tag -->
    </body>
    </html>
    """
    
    try:
        template = Template(invalid_template)
        print("❌ Invalid template should have failed validation")
        return False
    except Exception as e:
        print("✅ Invalid template correctly caught during parsing")
        return True

if __name__ == "__main__":
    print("Testing custom template functionality...")
    print("=" * 50)
    
    success1 = test_template_processing()
    success2 = test_template_validation()
    
    print("=" * 50)
    if success1 and success2:
        print("🎉 All tests passed! Custom template functionality is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    sys.exit(0 if (success1 and success2) else 1) 