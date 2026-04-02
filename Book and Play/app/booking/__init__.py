from flask import Blueprint

booking_bp = Blueprint('booking', __name__)

from . import routes  # noqa: E402, F401
