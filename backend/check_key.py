import os
print('SET' if os.getenv('GROQ_API_KEY') else 'NOT SET')
