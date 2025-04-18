from flask import Flask, request, render_template, redirect, url_for, session
from pydantic_ai.agent import Agent
from pydantic_core import to_jsonable_python
from pydantic import BaseModel
import fitz  # PyMuPDF
import os
import json
import nest_asyncio
import tempfile
import random
from dotenv import load_dotenv
load_dotenv('.gitignore\.env')

import os

os.environ['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'
nest_asyncio.apply()


class Quiz(BaseModel):
    '''questions : liste des questions : list[str]
    options : liste de listes des choix avec un tag True ou False pour chaque réponse : list[list[(str,bool)]]
    len(questions) == 10'''
    questions:list[str]
    options: list[list[tuple[str,bool]]]
# Agent Pydantic AI
agent = Agent(
    model='google-gla:gemini-2.0-flash',
    system_prompt="""
tu es un créateur de quiz . tu lis le cours et tu crées des questions à choix multiples sur le cours.pour chaque question tu proposes 4 options.Une seule réponse correcte par question.
""",output_type=Quiz)

def read_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    return "\n".join(page.get_text() for page in doc)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        pdf = request.files['pdf']
        if pdf:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.save(tmp.name)
                content = read_pdf(tmp.name)
                result = agent.run_sync('voici le contenu du document : ' + content)
                questions = result.output.questions
                options= result.output.options
            # Shuffle des options pour chaque question
            for opt_list in options:
                random.shuffle(opt_list)
                session['questions'] = questions
                session['options'] = options
                session['current_index'] = 0
                return redirect(url_for('quiz'))

    return render_template('index.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    questions = session.get('questions', [])
    options = session.get('options', [])
    index = session.get('current_index', 0)

    if request.method == 'POST':
        selected = int(request.form['answer'])
        
        is_correct = (options[index][selected][1] == True)
        session['last_result'] = {'selected': selected, 'correct': is_correct}
        return redirect(url_for('quiz'))

    if index >= len(questions):
        return "Quiz terminé ! 🎉"

    q = questions[index]
    
    last_result = session.pop('last_result', None)

    return render_template('quiz.html', question =q,options=options, index=index, total=len(questions), last_result=last_result)

@app.route('/next')
def next_question():
    session['current_index'] += 1
    return redirect(url_for('quiz'))

# Lancement
if __name__ == "__main__":
    app.run(debug=True)