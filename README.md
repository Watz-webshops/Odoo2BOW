# Odoo2BOW

Middleware voor het genereren van Belcotax-on-web **fiche 281.86** XML-bestanden op basis van inschrijvings- en betalingsdata uit Odoo Online (sport- en vakantiekampen).

## Architectuur

```
frontend (Next.js)  →  backend (FastAPI)  →  PostgreSQL
                              ↓
                       BOW 281.86 XML
```

- **Backend**: Python + FastAPI, async SQLAlchemy, Alembic migraties
- **Frontend**: Next.js 15 (App Router), TanStack Query, Tailwind CSS
- **Database**: PostgreSQL 16

---

## Snel starten (development)

```bash
# 1. Maak .env aan
cp .env.example .env
# Pas POSTGRES_PASSWORD, SECRET_KEY en ADMIN_JWT_SECRET aan

# 2. Start de stack
docker compose up -d

# 3. Voer migraties uit
docker compose exec backend alembic upgrade head

# 4. Maak eerste admin user aan
docker compose exec backend python scripts/create_admin.py admin@voorbeeld.be wachtwoord

# 5. Open de UI
open http://localhost:3000
```

---

## API gebruiken

### Authenticatie
Alle API-calls vereisen een Bearer token (organisatie-gebonden, via de UI aan te maken):

```
Authorization: Bearer sk_live_xxxxxxxxx
```

### Export aanmaken

```bash
curl -X POST http://localhost:8000/api/v1/exports/belcotax \
  -H "Authorization: Bearer sk_live_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "income_year": 2025,
    "organization": {
      "kbo": "0886886638",
      "name": "Sportkamp Leuven VZW",
      "address": { "street": "Kampstraat 12", "zip": "3000", "city": "Leuven", "country_code": 150 },
      "language_code": 1,
      "contact": { "name": "Administratie", "email": "admin@sportkamp.be", "phone": "+32 16 12 34 56" }
    },
    "participations": [
      {
        "event_id": "event_1001",
        "event_name": "Paaskamp 2025",
        "start_date": "2025-04-07",
        "end_date": "2025-04-11",
        "days": 5,
        "amount_paid": 150.00,
        "status": "confirmed",
        "parent": {
          "rrn": "85010112345",
          "first_name": "Jan",
          "last_name": "Peeters",
          "address": { "street": "Ouderlaan 5", "zip": "3000", "city": "Leuven", "country_code": 150 }
        },
        "child": { "rrn": "15012154321", "first_name": "Emma", "last_name": "Peeters" }
      }
    ]
  }'
# → 202 { "export_id": "exp_...", "status": "processing" }
```

### Status opvragen

```bash
curl http://localhost:8000/api/v1/exports/belcotax/exp_xxx \
  -H "Authorization: Bearer sk_live_xxx"
```

### XML downloaden

```bash
curl http://localhost:8000/api/v1/exports/belcotax/exp_xxx/xml \
  -H "Authorization: Bearer sk_live_xxx" \
  -o belcotax_2025.xml
```

---

## Tests uitvoeren

```bash
docker compose exec backend pytest -v
```

---

## Migraties

```bash
# Nieuwe migratie genereren
docker compose exec backend alembic revision --autogenerate -m "beschrijving"

# Uitvoeren
docker compose exec backend alembic upgrade head

# Terugdraaien
docker compose exec backend alembic downgrade -1
```

---

## Omgevingsvariabelen

| Variabele | Beschrijving |
|-----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL wachtwoord |
| `SECRET_KEY` | Algemene geheime sleutel (min. 32 tekens) |
| `ADMIN_JWT_SECRET` | JWT-sleutel voor admin sessies |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT geldigheid (standaard: 15) |
| `NEXT_PUBLIC_API_URL` | Backend URL voor de frontend |

---

## XML structuur

De gegenereerde XML volgt de BOW 281.86 specificatie:

- Bedragen in **centen** (integer)
- Datums in **DD-MM-YYYY** formaat
- Automatische aggregatie: meerdere deelnames van hetzelfde kind/ouder/jaar worden samengevoegd tot één fiche
- RRN-validatie inclusief controlecijfer en geboortedatumafleding
