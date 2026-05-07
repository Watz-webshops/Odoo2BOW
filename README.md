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
- **Database**: PostgreSQL via [Neon Console](https://console.neon.tech) (serverless)

---

## Snel starten met Neon (aanbevolen)

1. Ga naar https://console.neon.tech en maak een project aan (bv. `odoo2bow`).
2. Klik op **Connect** → kies **Pooled connection** → copy de connection string.
3. Maak `.env` aan en plak de string als `DATABASE_URL` (let op: `postgresql+asyncpg://` ipv `postgresql://`):
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx-pooler.region.aws.neon.tech/odoo2bow?ssl=require
   SECRET_KEY=...minimum-32-tekens...
   ADMIN_JWT_SECRET=...minimum-32-tekens...
   ```
4. Start de stack:
   ```powershell
   docker compose up -d --build
   ```
5. Voer migraties uit (tegen Neon):
   ```powershell
   docker compose exec backend alembic upgrade head
   ```
6. Maak de eerste admin aan via Neon Console SQL editor — zie [Eerste admin aanmaken](#eerste-admin-aanmaken) hieronder.
7. Open http://localhost:3000

### Lokale Postgres (offline / optioneel)

```powershell
docker compose --profile local-db up -d
# DATABASE_URL=postgresql+asyncpg://odoo2bow:changeme@db:5432/odoo2bow
```

---

## Eerste admin aanmaken

**Optie A — via Neon Console (aanbevolen):**

```powershell
# Genereer bcrypt hash van je wachtwoord
docker compose run --rm backend python -c "from passlib.hash import bcrypt; print(bcrypt.hash('jouw-wachtwoord'))"
# → kopieer de output ($2b$12$...)
```

In Neon Console → **SQL Editor**:
```sql
INSERT INTO admin_users (email, password_hash)
VALUES ('admin@jouw-domein.be', '$2b$12$...PLAK_HASH_HIER...');
```

**Optie B — via CLI:**
```powershell
docker compose exec backend python scripts/create_admin.py admin@voorbeeld.be wachtwoord
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

De gegenereerde XML volgt de officiële BOW 281.86 specificatie (`Belcotax-2025.xsd`):

- Bedragen in **centen** (integer)
- Datums in **DD-MM-YYYY** formaat
- Automatische aggregatie: meerdere deelnames van hetzelfde kind/ouder/jaar worden samengevoegd tot één fiche
- RRN-validatie inclusief controlecijfer en geboortedatumafleiding
- `v0010_bestandtype` = `BELCOTAX` (productie) of `BCTEST` (test)
- Volledige trailer-records: `r8010..r8013` per Aangifte en `r9010..r9014` per Verzending

### XSD-validatie

De middleware valideert elke gegenereerde XML automatisch tegen de officiële `Belcotax-2025.xsd` (in `backend/app/schemas/` of `backend/app/services/schemas/`). Validatiefouten verschijnen als waarschuwingen in de export-summary.

## Toekomst: automatische indiening

De FOD Financiën werkt aan een **bulks API** voor automatische indiening:
`https://server.minfin.be/external/api/bulks/v1` (nog niet publiek toegankelijk).

Een placeholder staat klaar in [backend/app/services/bulk_submission.py](backend/app/services/bulk_submission.py). Tot de API publiek is, blijft manuele upload in Belcotax-on-web de werkwijze.
