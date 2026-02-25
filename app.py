import json
import os
from flask import Flask, session, redirect, url_for, flash
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore


app = Flask(__name__) 
app.secret_key = "dev-secret-key"  # Replace with a secure key in production


# ---------------- FIREBASE INIT ----------------
# ---------------- FIREBASE INIT ----------------
import json
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    firebase_confifg = os.environ.get("FIREBASE_CONFIG")
    if not firebase_confifg:
        raise RuntimeError("missing FIREBASE_CONFIG")
    
    cred = credentials.Certificate(json.loads(firebase_confifg))
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
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1") 
