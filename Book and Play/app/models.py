from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='mitglied')
    member_number = db.Column(db.String(20), unique=True, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    no_show_count = db.Column(db.Integer, default=0)
    blocked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = db.relationship('Booking', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def initials(self):
        return f'{self.first_name[0]}.{self.last_name[0]}.'

    def is_admin(self):
        return self.role == 'admin'

    def is_sportwart(self):
        return self.role in ('admin', 'sportwart')

    def is_trainer(self):
        return self.role in ('admin', 'sportwart', 'trainer')

    def is_blocked(self):
        if self.blocked_until is None:
            return False
        return datetime.utcnow() < self.blocked_until

    def __repr__(self):
        return f'<User {self.email}>'


class Court(db.Model):
    __tablename__ = 'courts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    court_type = db.Column(db.String(10), nullable=False)  # 'outdoor' or 'indoor'
    surface = db.Column(db.String(30))
    has_lighting = db.Column(db.Boolean, default=False)
    season_start = db.Column(db.String(5))  # 'MM-DD'
    season_end = db.Column(db.String(5))    # 'MM-DD'
    open_time = db.Column(db.String(5), default='08:00')
    close_time = db.Column(db.String(5), default='22:00')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='court', lazy='dynamic')
    blocks = db.relationship('CourtBlock', backref='court', lazy='dynamic')

    def is_in_season(self, check_date):
        """Check if court is available on a given date."""
        if not self.season_start or not self.season_end:
            return True

        month_day = check_date.strftime('%m-%d')
        start = self.season_start
        end = self.season_end

        # Handle season that wraps around year boundary (e.g., Nov-Apr)
        if start <= end:
            return start <= month_day <= end
        else:
            return month_day >= start or month_day <= end

    def __repr__(self):
        return f'<Court {self.name}>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('courts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    end_time = db.Column(db.String(5), nullable=False)     # 'HH:MM'
    duration_min = db.Column(db.Integer, default=60)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled, no_show
    guest_name = db.Column(db.String(100), nullable=True)
    is_guest_booking = db.Column(db.Boolean, default=False)
    price_cents = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(255), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_booking_court_date_time', 'court_id', 'date', 'start_time'),
        db.Index('ix_booking_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f'<Booking {self.court_id} {self.date} {self.start_time}>'


class PriceRule(db.Model):
    __tablename__ = 'price_rules'

    id = db.Column(db.Integer, primary_key=True)
    court_type = db.Column(db.String(10), nullable=False)   # 'indoor' or 'outdoor'
    user_type = db.Column(db.String(20), nullable=False)     # 'mitglied', 'gast', 'extern'
    day_type = db.Column(db.String(20), nullable=False)      # 'weekday_offpeak', 'weekday_peak', 'weekend'
    price_cents = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PriceRule {self.court_type}/{self.user_type}/{self.day_type}: {self.price_cents}ct>'


class CourtBlock(db.Model):
    __tablename__ = 'court_blocks'

    id = db.Column(db.Integer, primary_key=True)
    court_id = db.Column(db.Integer, db.ForeignKey('courts.id'), nullable=False)
    blocked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    reason = db.Column(db.String(20), nullable=False)  # training, mannschaft, turnier, wartung
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    blocked_by = db.relationship('User', backref='blocks_created')

    def __repr__(self):
        return f'<CourtBlock {self.court_id} {self.date} {self.reason}>'
