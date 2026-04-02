from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from ..extensions import db
from ..models import User


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('booking.calendar_view'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash('E-Mail oder Passwort falsch.', 'error')
            return render_template('auth/login.html', email=email)

        if not user.is_active:
            flash('Dein Konto ist deaktiviert. Kontaktiere den Verein.', 'error')
            return render_template('auth/login.html', email=email)

        login_user(user, remember=True)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('booking.calendar_view'))

    return render_template('auth/login.html', email='')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/passwort-aendern', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Aktuelles Passwort ist falsch.', 'error')
        elif len(new_pw) < 6:
            flash('Neues Passwort muss mindestens 6 Zeichen haben.', 'error')
        elif new_pw != confirm_pw:
            flash('Passwörter stimmen nicht überein.', 'error')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Passwort erfolgreich geändert.', 'success')
            return redirect(url_for('booking.calendar_view'))

    return render_template('auth/change_password.html')
