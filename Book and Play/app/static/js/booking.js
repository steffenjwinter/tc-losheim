/**
 * grundlinie.com — Buchungs- und Storno-Flow
 * Modals + Toast-Notifications + API-Calls
 */

(function () {
    'use strict';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    // --- Toast ---
    function showToast(message, type) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type || 'info'}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            toast.style.transition = '0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // --- Booking Modal ---
    function openBookingModal(el) {
        const modal = document.getElementById('booking-modal');
        const courtName = el.dataset.courtName;
        const dateLabel = el.dataset.dateLabel;
        const date = el.dataset.date;
        const time = el.dataset.time;
        const endTime = el.dataset.endTime;
        const price = parseInt(el.dataset.price) || 0;
        const courtId = el.dataset.courtId;

        // Parse date for nice display
        const d = new Date(date + 'T00:00:00');
        const days = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
        const dateDisplay = `${days[d.getDay()]}, ${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;

        document.getElementById('bm-court').textContent = courtName;
        document.getElementById('bm-date').textContent = dateDisplay;
        document.getElementById('bm-time').textContent = `${time} – ${endTime} Uhr`;

        const priceEl = document.getElementById('bm-price');
        if (price === 0) {
            priceEl.textContent = 'Kostenlos';
            priceEl.classList.add('price-free');
        } else {
            priceEl.textContent = (price / 100).toFixed(2).replace('.', ',') + ' \u20ac';
            priceEl.classList.remove('price-free');
        }

        document.getElementById('bm-guest').value = '';

        // Store data for confirm
        modal.dataset.courtId = courtId;
        modal.dataset.date = date;
        modal.dataset.time = time;

        modal.classList.add('open');
    }

    function closeBookingModal() {
        document.getElementById('booking-modal').classList.remove('open');
    }

    function confirmBooking() {
        const modal = document.getElementById('booking-modal');
        const courtId = modal.dataset.courtId;
        const date = modal.dataset.date;
        const time = modal.dataset.time;
        const guestName = document.getElementById('bm-guest').value.trim();

        const btn = document.getElementById('bm-confirm');
        btn.disabled = true;
        btn.textContent = 'Wird gebucht...';

        fetch('/api/booking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                court_id: parseInt(courtId),
                date: date,
                start_time: time,
                guest_name: guestName
            })
        })
            .then(r => r.json())
            .then(data => {
                closeBookingModal();
                if (data.ok) {
                    showToast(data.message, 'success');
                    if (window.CalendarRefresh) window.CalendarRefresh();
                } else {
                    showToast(data.error, 'error');
                }
            })
            .catch(() => {
                closeBookingModal();
                showToast('Verbindungsfehler. Bitte versuche es erneut.', 'error');
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = 'Jetzt buchen';
            });
    }

    // --- Cancel Modal ---
    function openCancelModal(bookingId) {
        const modal = document.getElementById('cancel-modal');

        // Fetch booking info
        fetch(`/api/booking/${bookingId}/info`)
            .then(r => r.json())
            .then(data => {
                if (!data.ok) {
                    showToast(data.error, 'error');
                    return;
                }

                document.getElementById('cm-court').textContent = data.court;
                document.getElementById('cm-date').textContent = data.date;
                document.getElementById('cm-time').textContent = data.time;
                document.getElementById('cm-message').textContent = data.message;

                const confirmBtn = document.getElementById('cm-confirm');
                if (!data.can_cancel) {
                    confirmBtn.disabled = true;
                    confirmBtn.textContent = 'Nicht möglich';
                } else {
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = 'Stornieren';
                }

                modal.dataset.bookingId = bookingId;
                modal.classList.add('open');
            })
            .catch(() => {
                showToast('Fehler beim Laden der Buchungsinfo.', 'error');
            });
    }

    function closeCancelModal() {
        document.getElementById('cancel-modal').classList.remove('open');
    }

    function confirmCancel() {
        const modal = document.getElementById('cancel-modal');
        const bookingId = modal.dataset.bookingId;

        const btn = document.getElementById('cm-confirm');
        btn.disabled = true;
        btn.textContent = 'Wird storniert...';

        fetch(`/api/booking/${bookingId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
            .then(r => r.json())
            .then(data => {
                closeCancelModal();
                if (data.ok) {
                    showToast(data.message, 'success');
                    if (window.CalendarRefresh) window.CalendarRefresh();
                } else {
                    showToast(data.error, 'error');
                }
            })
            .catch(() => {
                closeCancelModal();
                showToast('Verbindungsfehler. Bitte versuche es erneut.', 'error');
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = 'Stornieren';
            });
    }

    // --- Event Listeners ---
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('bm-cancel').addEventListener('click', closeBookingModal);
        document.getElementById('bm-confirm').addEventListener('click', confirmBooking);
        document.getElementById('cm-cancel').addEventListener('click', closeCancelModal);
        document.getElementById('cm-confirm').addEventListener('click', confirmCancel);

        // Close modals on overlay click
        document.getElementById('booking-modal').addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) closeBookingModal();
        });
        document.getElementById('cancel-modal').addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) closeCancelModal();
        });

        // Close modals on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeBookingModal();
                closeCancelModal();
            }
        });
    });

    // Expose for calendar.js onclick handlers
    window.BookingFlow = {
        openBookingModal,
        openCancelModal
    };

})();
