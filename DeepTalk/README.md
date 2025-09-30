# DeepTalk Web MVP

## Setup
1. PostgreSQL starten und DB anlegen, z. B. `deeptalk`.
2. `.env` ausfüllen (`cp .env.example .env`).
3. Schema einspielen: `psql "$DATABASE_URL" -f schema.sql`.
4. Abhängigkeiten: `pip install -r requirements.txt`.
5. Start: `python app.py` (läuft auf http://127.0.0.1:5000)

## Hinweise
- WebRTC funktioniert auf `localhost` ohne HTTPS. Für Produktion: HTTPS + TURN-Server.
- Matching ist extrem simpel (ältester Eintrag).
- Kein Login/Profil im MVP: Gast-User werden automatisch erzeugt.
- Für echte Skalierung: separater Signaling-Server, persistente Sessions, Rate Limiting.
