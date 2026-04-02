/**
 * grundlinie.com — Kalender-Widget
 * Wochenansicht (Desktop) + Tagesansicht (Mobile)
 */

(function () {
    'use strict';

    const DAYS_DE = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
    const DAYS_LONG = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];

    let currentMonday = null;
    let currentDayIndex = 0; // for mobile
    let weekData = null;
    let isMobile = window.innerWidth < 768;

    // --- Init ---
    document.addEventListener('DOMContentLoaded', () => {
        const today = new Date();
        currentMonday = getMonday(today);
        currentDayIndex = today.getDay() === 0 ? 6 : today.getDay() - 1; // 0=Mo

        document.getElementById('btn-prev').addEventListener('click', () => navigateWeek(-1));
        document.getElementById('btn-next').addEventListener('click', () => navigateWeek(1));
        document.getElementById('btn-today').addEventListener('click', goToday);

        const btnDayPrev = document.getElementById('btn-day-prev');
        const btnDayNext = document.getElementById('btn-day-next');
        if (btnDayPrev) btnDayPrev.addEventListener('click', () => navigateDay(-1));
        if (btnDayNext) btnDayNext.addEventListener('click', () => navigateDay(1));

        window.addEventListener('resize', () => {
            const wasMobile = isMobile;
            isMobile = window.innerWidth < 768;
            if (wasMobile !== isMobile && weekData) render();
        });

        fetchAndRender();
    });

    // --- Date Helpers ---
    function getMonday(d) {
        const date = new Date(d);
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(date.setDate(diff));
    }

    function formatDateISO(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function addDays(d, n) {
        const result = new Date(d);
        result.setDate(result.getDate() + n);
        return result;
    }

    function getWeekNumber(d) {
        const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
        date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
        const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
        return Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
    }

    function formatDateShort(d) {
        return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.`;
    }

    function formatPrice(cents) {
        if (cents === 0) return 'Kostenlos';
        return (cents / 100).toFixed(2).replace('.', ',') + ' \u20ac';
    }

    // --- Navigation ---
    function navigateWeek(dir) {
        currentMonday = addDays(currentMonday, dir * 7);
        fetchAndRender();
    }

    function navigateDay(dir) {
        currentDayIndex += dir;
        if (currentDayIndex < 0) {
            currentMonday = addDays(currentMonday, -7);
            currentDayIndex = 6;
            fetchAndRender();
            return;
        }
        if (currentDayIndex > 6) {
            currentMonday = addDays(currentMonday, 7);
            currentDayIndex = 0;
            fetchAndRender();
            return;
        }
        render();
    }

    function goToday() {
        const today = new Date();
        currentMonday = getMonday(today);
        currentDayIndex = today.getDay() === 0 ? 6 : today.getDay() - 1;
        fetchAndRender();
    }

    // --- Fetch ---
    function fetchAndRender() {
        const dateStr = formatDateISO(currentMonday);
        const title = document.getElementById('calendar-title');
        title.textContent = 'Wird geladen...';

        fetch(`/api/slots?date=${dateStr}`)
            .then(r => r.json())
            .then(data => {
                weekData = data;
                render();
            })
            .catch(() => {
                title.textContent = 'Fehler beim Laden.';
            });
    }

    // --- Render ---
    function render() {
        if (!weekData) return;

        // Update title
        const sunday = addDays(currentMonday, 6);
        const kw = getWeekNumber(currentMonday);
        document.getElementById('calendar-title').textContent =
            `KW ${kw}  |  ${formatDateShort(currentMonday)} – ${formatDateShort(sunday)}${sunday.getFullYear()}`;

        if (isMobile) {
            renderDayView();
        } else {
            renderWeekGrid();
        }
    }

    // --- Desktop: Week Grid ---
    function renderWeekGrid() {
        const courts = weekData.courts;
        const days = weekData.days;
        const dates = Object.keys(days).sort();

        if (courts.length === 0) {
            document.getElementById('calendar-thead').innerHTML = '';
            document.getElementById('calendar-tbody').innerHTML =
                '<tr><td colspan="100" style="padding:40px; text-align:center; color:#999;">Keine Plätze in dieser Woche verfügbar (außerhalb der Saison).</td></tr>';
            return;
        }

        // Collect all time slots across all courts
        const allTimes = new Set();
        for (const dateStr of dates) {
            for (const court of courts) {
                const courtSlots = days[dateStr].slots[court.id];
                if (courtSlots) {
                    Object.keys(courtSlots).forEach(t => allTimes.add(t));
                }
            }
        }
        const times = Array.from(allTimes).sort();

        if (times.length === 0) {
            document.getElementById('calendar-thead').innerHTML = '';
            document.getElementById('calendar-tbody').innerHTML =
                '<tr><td colspan="100" style="padding:40px; text-align:center; color:#999;">Keine Zeitslots verfügbar.</td></tr>';
            return;
        }

        // Build header: Time | Court1-Mo | Court1-Di | ...
        // Actually: Time | Mo-Court1 | Mo-Court2 | ... | Di-Court1 | ...
        // Better UX: columns = days, sub-columns = courts per day
        // Simplest: one column per (day, court) combo

        let thead = '<tr><th class="time-col">Zeit</th>';
        for (const dateStr of dates) {
            const dayLabel = days[dateStr].label;
            for (const court of courts) {
                // Only show court if it has slots for this day
                if (days[dateStr].slots[court.id] && Object.keys(days[dateStr].slots[court.id]).length > 0) {
                    thead += `<th><div style="line-height:1.2;">${dayLabel}<br><span style="font-weight:400; font-size:11px;">${court.name}</span></div></th>`;
                }
            }
        }
        thead += '</tr>';
        document.getElementById('calendar-thead').innerHTML = thead;

        // Build body
        let tbody = '';
        for (const time of times) {
            tbody += `<tr><td class="time-cell">${time}</td>`;
            for (const dateStr of dates) {
                for (const court of courts) {
                    const courtSlots = days[dateStr].slots[court.id];
                    if (!courtSlots || Object.keys(courtSlots).length === 0) continue;

                    const slot = courtSlots[time];
                    if (!slot) {
                        tbody += '<td></td>';
                        continue;
                    }

                    const hour = parseInt(time.split(':')[0]);
                    const endTime = `${String(hour + 1).padStart(2, '0')}:00`;

                    switch (slot.s) {
                        case 'a': // available
                            tbody += `<td><div class="slot slot-available"
                                data-court-id="${court.id}" data-court-name="${court.name}"
                                data-date="${dateStr}" data-date-label="${days[dateStr].label}"
                                data-time="${time}" data-end-time="${endTime}"
                                data-price="${slot.p}"
                                onclick="window.BookingFlow.openBookingModal(this)">
                                Frei</div></td>`;
                            break;
                        case 'b': // booked by someone
                            tbody += `<td><div class="slot slot-booked">${slot.u || 'Belegt'}</div></td>`;
                            break;
                        case 'o': // own booking
                            tbody += `<td><div class="slot slot-own"
                                data-booking-id="${slot.bid}"
                                onclick="window.BookingFlow.openCancelModal(${slot.bid})">
                                Deine</div></td>`;
                            break;
                        case 'x': // blocked
                            const reasons = { training: 'Training', mannschaft: 'Spiel', turnier: 'Turnier', wartung: 'Wartung' };
                            tbody += `<td><div class="slot slot-blocked">${reasons[slot.r] || 'Gesperrt'}</div></td>`;
                            break;
                        case 'p': // past
                            tbody += `<td><div class="slot slot-past">–</div></td>`;
                            break;
                        default:
                            tbody += '<td></td>';
                    }
                }
            }
            tbody += '</tr>';
        }
        document.getElementById('calendar-tbody').innerHTML = tbody;
    }

    // --- Mobile: Day View ---
    function renderDayView() {
        const days = weekData.days;
        const dates = Object.keys(days).sort();
        const courts = weekData.courts;

        if (currentDayIndex >= dates.length) currentDayIndex = 0;
        const dateStr = dates[currentDayIndex];
        if (!dateStr) return;

        const dayData = days[dateStr];

        // Update day title
        const d = new Date(dateStr + 'T00:00:00');
        document.getElementById('day-title').textContent =
            `${DAYS_LONG[currentDayIndex]}, ${formatDateShort(d)}`;

        const container = document.getElementById('day-courts');
        let html = '';

        for (const court of courts) {
            const courtSlots = dayData.slots[court.id];
            if (!courtSlots || Object.keys(courtSlots).length === 0) continue;

            const times = Object.keys(courtSlots).sort();
            html += `<div class="day-court-card">
                <div class="day-court-header">${court.name}</div>
                <div class="day-slots">`;

            for (const time of times) {
                const slot = courtSlots[time];
                const hour = parseInt(time.split(':')[0]);
                const endTime = `${String(hour + 1).padStart(2, '0')}:00`;

                switch (slot.s) {
                    case 'a':
                        html += `<div class="day-slot slot-available"
                            data-court-id="${court.id}" data-court-name="${court.name}"
                            data-date="${dateStr}" data-date-label="${dayData.label}"
                            data-time="${time}" data-end-time="${endTime}"
                            data-price="${slot.p}"
                            onclick="window.BookingFlow.openBookingModal(this)">
                            ${time}</div>`;
                        break;
                    case 'b':
                        html += `<div class="day-slot slot-booked">${time}</div>`;
                        break;
                    case 'o':
                        html += `<div class="day-slot slot-own"
                            data-booking-id="${slot.bid}"
                            onclick="window.BookingFlow.openCancelModal(${slot.bid})">
                            ${time}</div>`;
                        break;
                    case 'x':
                        html += `<div class="day-slot slot-blocked">${time}</div>`;
                        break;
                    case 'p':
                        html += `<div class="day-slot slot-past">${time}</div>`;
                        break;
                }
            }

            html += '</div></div>';
        }

        if (!html) {
            html = '<p style="text-align:center; padding:40px; color:#999;">Keine Plätze verfügbar an diesem Tag.</p>';
        }

        container.innerHTML = html;
    }

    // Expose refresh function for booking.js
    window.CalendarRefresh = fetchAndRender;

})();
