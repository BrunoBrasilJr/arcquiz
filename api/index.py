import os
from app import app as flask_app

# Ajusta caminhos do Flask para a Vercel (garante templates/static)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

flask_app.template_folder = os.path.join(BASE_DIR, "templates")
flask_app.static_folder = os.path.join(BASE_DIR, "static")

app = flask_app
