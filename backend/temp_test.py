import httpx
from pathlib import Path

p = Path('sample_resume.txt')
p.write_text('John Doe\nPython, React, AWS\nProject: Built app with Python and AWS\n')

with httpx.Client() as c:
    r = c.post(
        'http://127.0.0.1:8000/analyze',
        files={'resume': ('sample_resume.txt', p.read_bytes(), 'text/plain')},
        data={'job_description': 'Python, AWS, React'}
    )
    print(r.status_code)
    print(r.text)
