# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class SignupForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password')])

    # Single select for Student / Lecturer / Admin
    role = SelectField(
        "Register as",
        choices=[
            ("student", "Student"),
            ("lecturer", "Lecturer"),
            ("admin", "Admin"),
        ],
        validators=[DataRequired()]
    )

    gender = SelectField(
        "Gender",
        choices=[("", "Select gender"), ("male","Male"), ("female","Female"), ("other","Other")],
        validators=[DataRequired(message="Please select gender.")]
    )

    date_of_birth = DateField("Date of birth", format="%Y-%m-%d", validators=[DataRequired(message="Please enter your date of birth.")])

    submit = SubmitField("Sign Up")
