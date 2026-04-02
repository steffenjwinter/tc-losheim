from flask import render_template, redirect, url_for
from flask_login import login_required
from . import booking_bp


@booking_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@booking_bp.route('/kalender')
@login_required
def calendar_view():
    return render_template('booking/calendar.html')
