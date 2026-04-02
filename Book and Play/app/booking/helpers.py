"""
Kern-Buchungslogik für grundlinie.com
Slot-Generierung, Validierung, Preisberechnung.
"""
from datetime import date, datetime, timedelta
from ..models import Court, Booking, PriceRule, CourtBlock


DAYS_DE = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
DAYS_LONG_DE = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']

MAX_ACTIVE_BOOKINGS = 2
MAX_ADVANCE_DAYS = 14
MIN_HOURS_BEFORE = 1
FREE_CANCEL_HOURS = 6


def get_monday(d):
    """Get Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def format_date_de(d):
    """Format date as 'Mo 05.05.' """
    return f'{DAYS_DE[d.weekday()]} {d.strftime("%d.%m.")}'


def format_date_long_de(d):
    """Format date as 'Montag, 05.05.2026' """
    return f'{DAYS_LONG_DE[d.weekday()]}, {d.strftime("%d.%m.%Y")}'


def get_weekly_slots(target_date, current_user):
    """
    Generate slot data for 7 days starting from Monday of target_date's week.
    Returns dict suitable for JSON serialization.
    """
    monday = get_monday(target_date)
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    now = datetime.now()

    # Get all active courts
    courts = Court.query.filter_by(is_active=True).order_by(Court.sort_order).all()

    # Determine which courts are in-season for each day
    # Build court list (only courts that are in-season for at least one day)
    courts_in_season = []
    court_season_map = {}  # court_id -> set of day indices where in season
    for court in courts:
        day_indices = set()
        for i, d in enumerate(week_dates):
            if court.is_in_season(d):
                day_indices.add(i)
        if day_indices:
            courts_in_season.append(court)
            court_season_map[court.id] = day_indices

    # Batch query: all confirmed bookings this week
    bookings = Booking.query.filter(
        Booking.date.between(week_dates[0], week_dates[6]),
        Booking.status == 'confirmed'
    ).all()

    # Index bookings by (court_id, date_str, start_time)
    booking_map = {}
    for b in bookings:
        key = (b.court_id, b.date.isoformat(), b.start_time)
        booking_map[key] = b

    # Batch query: all blocks this week
    blocks = CourtBlock.query.filter(
        CourtBlock.date.between(week_dates[0], week_dates[6])
    ).all()

    # Index blocks: for each (court_id, date_str), list of (start, end, reason)
    block_map = {}
    for bl in blocks:
        key = (bl.court_id, bl.date.isoformat())
        if key not in block_map:
            block_map[key] = []
        block_map[key].append((bl.start_time, bl.end_time, bl.reason))

    # Build response
    courts_data = [
        {'id': c.id, 'name': c.name, 'type': c.court_type}
        for c in courts_in_season
    ]

    days_data = {}
    for i, d in enumerate(week_dates):
        date_str = d.isoformat()
        day_label = format_date_de(d)

        slots = {}
        for court in courts_in_season:
            if i not in court_season_map.get(court.id, set()):
                continue

            court_slots = {}
            open_h = int(court.open_time.split(':')[0])
            close_h = int(court.close_time.split(':')[0])

            for hour in range(open_h, close_h):
                time_str = f'{hour:02d}:00'
                end_time_str = f'{hour + 1:02d}:00'

                # Check if slot is in the past
                slot_dt = datetime.combine(d, datetime.strptime(time_str, '%H:%M').time())
                if slot_dt < now - timedelta(minutes=30):
                    court_slots[time_str] = {'s': 'p'}  # past
                    continue

                # Check blocks
                block_key = (court.id, date_str)
                is_blocked = False
                block_reason = ''
                for bl_start, bl_end, bl_reason in block_map.get(block_key, []):
                    if bl_start <= time_str < bl_end:
                        is_blocked = True
                        block_reason = bl_reason
                        break

                if is_blocked:
                    court_slots[time_str] = {'s': 'x', 'r': block_reason}
                    continue

                # Check bookings
                booking_key = (court.id, date_str, time_str)
                booking = booking_map.get(booking_key)

                if booking:
                    if booking.user_id == current_user.id:
                        court_slots[time_str] = {
                            's': 'o',
                            'bid': booking.id,
                            'p': booking.price_cents,
                            'g': booking.guest_name or ''
                        }
                    else:
                        court_slots[time_str] = {
                            's': 'b',
                            'u': booking.user.initials
                        }
                else:
                    # Available — calculate price
                    price = calculate_price(court, current_user, d, time_str)
                    court_slots[time_str] = {
                        's': 'a',
                        'p': price
                    }

            slots[str(court.id)] = court_slots

        days_data[date_str] = {
            'label': day_label,
            'slots': slots
        }

    return {
        'week_start': week_dates[0].isoformat(),
        'week_end': week_dates[6].isoformat(),
        'courts': courts_data,
        'days': days_data
    }


def validate_booking(user, court_id, date_str, start_time_str):
    """
    Validate a booking request.
    Returns (True, None) or (False, error_message).
    """
    # Parse date
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return False, 'Ungültiges Datumsformat.'

    # Parse time
    try:
        booking_time = datetime.strptime(start_time_str, '%H:%M').time()
    except ValueError:
        return False, 'Ungültiges Zeitformat.'

    # Court exists and is active
    court = Court.query.get(court_id)
    if not court or not court.is_active:
        return False, 'Platz nicht verfügbar.'

    # In season
    if not court.is_in_season(booking_date):
        return False, f'{court.name} ist in diesem Zeitraum nicht bespielbar.'

    # Within operating hours
    open_h = int(court.open_time.split(':')[0])
    close_h = int(court.close_time.split(':')[0])
    hour = int(start_time_str.split(':')[0])
    if hour < open_h or hour >= close_h:
        return False, f'{court.name} ist zu dieser Uhrzeit geschlossen.'

    # Not in the past
    now = datetime.now()
    slot_dt = datetime.combine(booking_date, booking_time)
    if slot_dt < now:
        return False, 'Dieser Zeitslot liegt in der Vergangenheit.'

    # Minimum hours before
    if (slot_dt - now).total_seconds() < MIN_HOURS_BEFORE * 3600:
        return False, f'Buchung muss mindestens {MIN_HOURS_BEFORE} Stunde(n) im Voraus erfolgen.'

    # Max advance days
    if (booking_date - date.today()).days > MAX_ADVANCE_DAYS:
        return False, f'Buchung maximal {MAX_ADVANCE_DAYS} Tage im Voraus möglich.'

    # User not blocked
    if user.is_blocked():
        return False, 'Dein Konto ist vorübergehend für Buchungen gesperrt.'

    # Max active bookings
    active_count = Booking.query.filter(
        Booking.user_id == user.id,
        Booking.status == 'confirmed',
        Booking.date >= date.today()
    ).count()
    if active_count >= MAX_ACTIVE_BOOKINGS:
        return False, f'Du hast bereits {MAX_ACTIVE_BOOKINGS} aktive Buchungen. Storniere eine, um neu zu buchen.'

    # Slot not already booked
    existing = Booking.query.filter_by(
        court_id=court_id,
        date=booking_date,
        start_time=start_time_str,
        status='confirmed'
    ).first()
    if existing:
        return False, 'Dieser Slot ist bereits belegt.'

    # Slot not blocked
    blocks = CourtBlock.query.filter_by(
        court_id=court_id,
        date=booking_date
    ).all()
    for block in blocks:
        if block.start_time <= start_time_str < block.end_time:
            return False, 'Dieser Slot ist gesperrt.'

    return True, None


def calculate_price(court, user, booking_date, start_time_str):
    """Calculate price in cents for a booking."""
    # Outdoor + member = free
    if court.court_type == 'outdoor' and user.role in ('mitglied', 'trainer', 'sportwart', 'admin'):
        return 0

    # Determine user_type for price lookup
    if user.role in ('mitglied', 'trainer', 'sportwart', 'admin'):
        user_type = 'mitglied'
    elif user.role == 'gast':
        user_type = 'gast'
    else:
        user_type = 'extern'

    # Determine day_type
    hour = int(start_time_str.split(':')[0])
    weekday = booking_date.weekday()

    if weekday >= 5:  # Saturday or Sunday
        day_type = 'weekend'
    elif hour < 16:
        day_type = 'weekday_offpeak'
    else:
        day_type = 'weekday_peak'

    # Lookup price rule
    rule = PriceRule.query.filter_by(
        court_type=court.court_type,
        user_type=user_type,
        day_type=day_type,
        is_active=True
    ).first()

    return rule.price_cents if rule else 0


def can_cancel_booking(booking):
    """
    Check if a booking can be cancelled.
    Returns (can_cancel, is_free, message).
    """
    now = datetime.now()
    slot_dt = datetime.combine(
        booking.date,
        datetime.strptime(booking.start_time, '%H:%M').time()
    )

    if slot_dt < now:
        return False, False, 'Vergangene Buchungen können nicht storniert werden.'

    hours_until = (slot_dt - now).total_seconds() / 3600

    if hours_until >= FREE_CANCEL_HOURS:
        return True, True, 'Kostenlose Stornierung möglich.'

    # Indoor court with late cancel
    if booking.court.court_type == 'indoor' and booking.price_cents > 0:
        price_display = f'{booking.price_cents / 100:.2f}'.replace('.', ',')
        return True, False, f'Späte Stornierung — Kosten: {price_display} EUR.'

    return True, True, 'Kostenlose Stornierung möglich.'
