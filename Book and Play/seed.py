"""
Seed-Script für grundlinie.com — Book and Play
Befüllt die Datenbank mit Plätzen, Preisregeln und Test-Usern.

Ausführen: python3 seed.py
"""
from app import create_app
from app.extensions import db
from app.models import User, Court, PriceRule

app = create_app()

with app.app_context():
    # Tabellen neu erstellen
    db.drop_all()
    db.create_all()
    print('Tabellen erstellt.')

    # === PLÄTZE ===

    # 6 Außenplätze (Sand, Mai-Oktober)
    for i in range(1, 7):
        court = Court(
            name=f'Platz {i}',
            court_type='outdoor',
            surface='Sand (Asche)',
            has_lighting=i <= 4,  # Platz 1-4 mit Flutlicht
            season_start='05-01',
            season_end='10-31',
            open_time='08:00',
            close_time='21:00',
            sort_order=i,
        )
        db.session.add(court)

    # 2 Hallenplätze (Teppich, November-April)
    for i in range(1, 3):
        court = Court(
            name=f'Halle {i}',
            court_type='indoor',
            surface='Teppich/Granulat',
            has_lighting=True,
            season_start='11-01',
            season_end='04-30',
            open_time='08:00',
            close_time='22:00',
            sort_order=10 + i,
        )
        db.session.add(court)

    print('8 Plätze angelegt (6 Außen + 2 Halle).')

    # === PREISREGELN ===

    price_rules = [
        # Außenplätze — Mitglieder kostenlos
        ('outdoor', 'mitglied', 'weekday_offpeak', 0, 'Freiplatz Mitglied (Mo-Fr bis 16h)'),
        ('outdoor', 'mitglied', 'weekday_peak', 0, 'Freiplatz Mitglied (Mo-Fr ab 16h)'),
        ('outdoor', 'mitglied', 'weekend', 0, 'Freiplatz Mitglied (Wochenende)'),
        # Außenplätze — Gäste
        ('outdoor', 'gast', 'weekday_offpeak', 500, 'Freiplatz Gast (Mo-Fr bis 16h)'),
        ('outdoor', 'gast', 'weekday_peak', 500, 'Freiplatz Gast (Mo-Fr ab 16h)'),
        ('outdoor', 'gast', 'weekend', 500, 'Freiplatz Gast (Wochenende)'),
        # Außenplätze — Externe
        ('outdoor', 'extern', 'weekday_offpeak', 1000, 'Freiplatz Extern (Mo-Fr bis 16h)'),
        ('outdoor', 'extern', 'weekday_peak', 1000, 'Freiplatz Extern (Mo-Fr ab 16h)'),
        ('outdoor', 'extern', 'weekend', 1000, 'Freiplatz Extern (Wochenende)'),
        # Hallenplätze — Mitglieder
        ('indoor', 'mitglied', 'weekday_offpeak', 1200, 'Halle Mitglied Off-Peak (Mo-Fr bis 16h)'),
        ('indoor', 'mitglied', 'weekday_peak', 1800, 'Halle Mitglied Prime-Time (Mo-Fr ab 16h)'),
        ('indoor', 'mitglied', 'weekend', 1800, 'Halle Mitglied Wochenende'),
        # Hallenplätze — Gäste
        ('indoor', 'gast', 'weekday_offpeak', 1800, 'Halle Gast Off-Peak (Mo-Fr bis 16h)'),
        ('indoor', 'gast', 'weekday_peak', 2400, 'Halle Gast Prime-Time (Mo-Fr ab 16h)'),
        ('indoor', 'gast', 'weekend', 2400, 'Halle Gast Wochenende'),
    ]

    for court_type, user_type, day_type, price, label in price_rules:
        rule = PriceRule(
            court_type=court_type,
            user_type=user_type,
            day_type=day_type,
            price_cents=price,
            label=label,
        )
        db.session.add(rule)

    print(f'{len(price_rules)} Preisregeln angelegt.')

    # === TEST-USER ===

    users_data = [
        ('admin@tc-losheim.de', 'admin123', 'Moritz', 'Serwe', 'admin', 'M-001'),
        ('sportwart@tc-losheim.de', 'sport123', 'Sascha', 'Kuhn', 'sportwart', 'M-002'),
        ('trainer@tc-losheim.de', 'trainer123', 'Constantin', 'Wieber', 'trainer', 'M-003'),
        ('max.mueller@example.de', 'test123', 'Max', 'Müller', 'mitglied', 'M-010'),
        ('anna.schmidt@example.de', 'test123', 'Anna', 'Schmidt', 'mitglied', 'M-011'),
        ('peter.weber@example.de', 'test123', 'Peter', 'Weber', 'mitglied', 'M-012'),
    ]

    for email, pw, first, last, role, mnr in users_data:
        user = User(
            email=email,
            first_name=first,
            last_name=last,
            role=role,
            member_number=mnr,
        )
        user.set_password(pw)
        db.session.add(user)

    print(f'{len(users_data)} Benutzer angelegt.')

    db.session.commit()
    print('\nDatenbank erfolgreich befüllt!')
    print('Login: admin@tc-losheim.de / admin123')
