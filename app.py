import json
import os
from flask import Flask, session, redirect, url_for, flash
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore


app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------------- FIREBASE INIT ----------------
if os.environ.get("FIREBASE_CONFIG"): 
    firebase_config = json.loads(os.environ.get("FIREBASE_CONFIG"))
    cred = credentials.Certificate(firebase_config)
else:
    cred = credentials.Certificate("firebase_config.json") 

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

app.db = db


# Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.lecturer import lecturer_bp
from routes.student import student_bp
from routes.courses import courses_bp


# ---------------- REGISTER BLUEPRINTS ----------------
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(lecturer_bp, url_prefix="/lecturer")
app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(courses_bp, url_prefix="/courses")


# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True) 
    
    


    