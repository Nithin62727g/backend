import os
import sys

# Add backend to path so we can import app
sys.path.insert(0, os.path.abspath('.'))

from main import create_app
app = create_app()
from core.database import get_db

with app.app_context():
    # We need a token or we can just mock the user
    # Let's hit the function directly if we bypass @require_auth, but wait, it's easier to just mock g.current_user
    import json
    from flask import g
    
    with app.test_request_context('/api/v1/quizzes/generate', method='POST', json={'topic': 'Docker', 'difficulty': 'Beginner', 'question_count': 3}):
        g.current_user = {'id': 1, 'email': 'test@example.com'}
        from api.quizzes import generate_quiz
        
        response = generate_quiz()
        
        if isinstance(response, tuple):
            print("Status Code:", response[1])
            print("Response:", response[0].get_data(as_text=True))
        else:
            print("Response:", response.get_data(as_text=True))
