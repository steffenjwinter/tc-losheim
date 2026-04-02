"""
JSON API Endpoints für den Kalender.
"""
from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, date
from . import api_bp
from ..extensions import db
from ..models import Court, Booking
from ..booking.helpers import (
    get_weekly_slots, validate_booking, calculate_price,
    can_cancel_booking, format_date_long_de
)


@api_bp.route('/slots')
@login_required
def get_slots():
    """Get weekly slot data for the calendar."""
    date_str = request.args.get('date', date.today().isoformat())
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'ok': False, 'error': 'Ungültiges Datum.'}), 400

    data = get_weekly_slots(target_date, current_user)
    return jsonify(data)


@api_bp.route('/booking', methods=['POST'])
@login_required
def create_booking():
    """Create a new booking."""
    data = request.get_json()
    if not data:
        return jsonify({'ok': False, 'error': 'Keine Daten gesendet.'}), 400

    court_id = data.get('court_id')
    date_str = data.get('date')
    start_time = data.get('start_time')
    guest_name = data.get('guest_name', '').strip()

    if not all([court_id, date_str, start_time]):
        return jsonify({'ok': False, 'error': 'Platz, Datum und Uhrzeit sind erforderlich.'}), 400

    # Validate
    valid, error = validate_booking(current_user, court_id, date_str, start_time)
    if not valid:
        return jsonify({'ok': False, 'error': error}), 400

    # Calculate price
    court = Court.query.get(court_id)
    booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    price = calculate_price(court, current_user, booking_date, start_time)

    # Calculate end time
    hour = int(start_time.split(':')[0])
    end_time = f'{hour + 1:02d}:00'

    # Create booking
    booking = Booking(
        user_id=current_user.id,
        court_id=court_id,
        date=booking_date,
        start_time=start_time,
        end_time=end_time,
        price_cents=price,
        guest_name=guest_name or None,
        is_guest_booking=bool(guest_name),
        status='confirmed',
    )
    db.session.add(booking)
    db.session.commit()

    price_display = f'{price / 100:.2f}'.replace('.', ',') + ' \u20ac'
    if price == 0:
        price_display = 'Kostenlos'

    return jsonify({
        'ok': True,
        'booking_id': booking.id,
        'price_display': price_display,
        'message': 'Buchung erfolgreich!'
    })


@api_bp.route('/booking/<int:booking_id>', methods=['DELETE'])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking."""
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'ok': False, 'error': 'Buchung nicht gefunden.'}), 404

    # Only owner or admin can cancel
    if booking.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'ok': False, 'error': 'Keine Berechtigung.'}), 403

    can_cancel, is_free, message = can_cancel_booking(booking)
    if not can_cancel:
        return jsonify({'ok': False, 'error': message}), 400

    booking.status = 'cancelled'
    booking.cancelled_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'ok': True,
        'message': 'Buchung storniert.',
        'was_free': is_free
    })


@api_bp.route('/courts')
@login_required
def get_courts():
    """Get active courts."""
    courts = Court.query.filter_by(is_active=True).order_by(Court.sort_order).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'type': c.court_type,
        'surface': c.surface,
    } for c in courts])


@api_bp.route('/booking/<int:booking_id>/info')
@login_required
def booking_info(booking_id):
    """Get cancel info for a booking."""
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'ok': False, 'error': 'Nicht gefunden.'}), 404

    if booking.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'ok': False, 'error': 'Keine Berechtigung.'}), 403

    can_cancel, is_free, message = can_cancel_booking(booking)

    return jsonify({
        'ok': True,
        'court': booking.court.name,
        'date': format_date_long_de(booking.date),
        'time': f'{booking.start_time} – {booking.end_time} Uhr',
        'can_cancel': can_cancel,
        'is_free': is_free,
        'message': message,
        'booking_id': booking.id
    })
