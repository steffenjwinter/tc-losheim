from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from . import admin_bp
from ..extensions import db
from ..models import User, Court, Booking, PriceRule, CourtBlock
from datetime import date, datetime, timedelta


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ('admin', 'sportwart'):
            flash('Keine Berechtigung.', 'error')
            return redirect(url_for('booking.calendar_view'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    today = date.today()
    total_members = User.query.filter_by(is_active=True).count()
    today_bookings = Booking.query.filter_by(date=today, status='confirmed').count()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_bookings = Booking.query.filter(
        Booking.date.between(week_start, week_end),
        Booking.status == 'confirmed'
    ).count()

    recent_bookings = Booking.query.filter_by(status='confirmed').order_by(
        Booking.date.desc(), Booking.start_time.desc()
    ).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_members=total_members,
                           today_bookings=today_bookings,
                           week_bookings=week_bookings,
                           recent_bookings=recent_bookings)


@admin_bp.route('/mitglieder')
@login_required
@admin_required
def members_list():
    search = request.args.get('q', '').strip()
    query = User.query.order_by(User.last_name, User.first_name)
    if search:
        query = query.filter(
            db.or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
            )
        )
    members = query.all()
    return render_template('admin/members.html', members=members, search=search)


@admin_bp.route('/mitglieder/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def member_create():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('E-Mail existiert bereits.', 'error')
            return render_template('admin/member_form.html', member=None)

        user = User(
            email=email,
            first_name=request.form.get('first_name', '').strip(),
            last_name=request.form.get('last_name', '').strip(),
            role=request.form.get('role', 'mitglied'),
            member_number=request.form.get('member_number', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
        )
        user.set_password(request.form.get('password', 'tennis2026'))
        db.session.add(user)
        db.session.commit()
        flash(f'{user.full_name} wurde angelegt.', 'success')
        return redirect(url_for('admin.members_list'))

    return render_template('admin/member_form.html', member=None)


@admin_bp.route('/mitglieder/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def member_edit(user_id):
    member = User.query.get_or_404(user_id)
    if request.method == 'POST':
        member.first_name = request.form.get('first_name', '').strip()
        member.last_name = request.form.get('last_name', '').strip()
        member.email = request.form.get('email', '').strip().lower()
        member.role = request.form.get('role', 'mitglied')
        member.member_number = request.form.get('member_number', '').strip() or None
        member.phone = request.form.get('phone', '').strip() or None

        new_pw = request.form.get('password', '').strip()
        if new_pw:
            member.set_password(new_pw)

        db.session.commit()
        flash(f'{member.full_name} wurde aktualisiert.', 'success')
        return redirect(url_for('admin.members_list'))

    return render_template('admin/member_form.html', member=member)


@admin_bp.route('/mitglieder/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def member_toggle(user_id):
    member = User.query.get_or_404(user_id)
    member.is_active = not member.is_active
    db.session.commit()
    status = 'aktiviert' if member.is_active else 'deaktiviert'
    flash(f'{member.full_name} wurde {status}.', 'success')
    return redirect(url_for('admin.members_list'))


@admin_bp.route('/buchungen')
@login_required
@admin_required
def bookings_list():
    date_filter = request.args.get('date', '')
    court_filter = request.args.get('court', '')
    status_filter = request.args.get('status', 'confirmed')

    query = Booking.query.order_by(Booking.date.desc(), Booking.start_time.desc())

    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=d)
        except ValueError:
            pass

    if court_filter:
        query = query.filter_by(court_id=int(court_filter))

    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)

    bookings = query.limit(100).all()
    courts = Court.query.order_by(Court.sort_order).all()

    return render_template('admin/bookings.html',
                           bookings=bookings, courts=courts,
                           date_filter=date_filter, court_filter=court_filter,
                           status_filter=status_filter)


@admin_bp.route('/buchungen/<int:booking_id>/cancel', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'cancelled'
    booking.cancelled_at = datetime.utcnow()
    db.session.commit()
    flash('Buchung wurde storniert.', 'success')
    return redirect(url_for('admin.bookings_list'))


@admin_bp.route('/preise', methods=['GET', 'POST'])
@login_required
@admin_required
def prices_list():
    if current_user.role != 'admin':
        flash('Nur Admins können Preise ändern.', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        for rule in PriceRule.query.filter_by(is_active=True).all():
            field_name = f'price_{rule.id}'
            new_price = request.form.get(field_name, '')
            if new_price:
                try:
                    rule.price_cents = int(float(new_price.replace(',', '.')) * 100)
                except ValueError:
                    pass
        db.session.commit()
        flash('Preise wurden aktualisiert.', 'success')
        return redirect(url_for('admin.prices_list'))

    outdoor_rules = PriceRule.query.filter_by(court_type='outdoor', is_active=True).all()
    indoor_rules = PriceRule.query.filter_by(court_type='indoor', is_active=True).all()

    return render_template('admin/prices.html',
                           outdoor_rules=outdoor_rules,
                           indoor_rules=indoor_rules)


@admin_bp.route('/plaetze')
@login_required
@admin_required
def courts_list():
    courts = Court.query.order_by(Court.sort_order).all()
    return render_template('admin/courts.html', courts=courts)


@admin_bp.route('/plaetze/<int:court_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def court_edit(court_id):
    court = Court.query.get_or_404(court_id)
    if request.method == 'POST':
        court.name = request.form.get('name', court.name).strip()
        court.open_time = request.form.get('open_time', court.open_time).strip()
        court.close_time = request.form.get('close_time', court.close_time).strip()
        court.has_lighting = 'has_lighting' in request.form
        court.is_active = 'is_active' in request.form
        db.session.commit()
        flash(f'{court.name} wurde aktualisiert.', 'success')
        return redirect(url_for('admin.courts_list'))

    return render_template('admin/court_edit.html', court=court)


@admin_bp.route('/sperren', methods=['GET', 'POST'])
@login_required
def blocks_manage():
    if not current_user.is_trainer():
        flash('Keine Berechtigung.', 'error')
        return redirect(url_for('booking.calendar_view'))

    if request.method == 'POST':
        block = CourtBlock(
            court_id=int(request.form.get('court_id')),
            blocked_by_id=current_user.id,
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
            start_time=request.form.get('start_time'),
            end_time=request.form.get('end_time'),
            reason=request.form.get('reason', 'training'),
            description=request.form.get('description', '').strip() or None,
        )
        db.session.add(block)
        db.session.commit()
        flash('Platzsperrung angelegt.', 'success')
        return redirect(url_for('admin.blocks_manage'))

    courts = Court.query.filter_by(is_active=True).order_by(Court.sort_order).all()
    blocks = CourtBlock.query.filter(
        CourtBlock.date >= date.today()
    ).order_by(CourtBlock.date, CourtBlock.start_time).all()

    return render_template('admin/blocks.html', courts=courts, blocks=blocks)


@admin_bp.route('/sperren/<int:block_id>/delete', methods=['POST'])
@login_required
def block_delete(block_id):
    if not current_user.is_sportwart():
        flash('Keine Berechtigung.', 'error')
        return redirect(url_for('booking.calendar_view'))

    block = CourtBlock.query.get_or_404(block_id)
    db.session.delete(block)
    db.session.commit()
    flash('Sperrung gelöscht.', 'success')
    return redirect(url_for('admin.blocks_manage'))
