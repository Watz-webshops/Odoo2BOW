# BOW 281.86 XML — herkomst van de velden

Overzicht van welke velden in de gegenereerde XML uit welke bron komen.
Referentie-implementatie: [`xml_generator.py`](../backend/app/services/xml_generator.py).
Voorbeeldbestand: [`BOW2022_VoorbeeldXML_f86.xml`](../backend/app/schemas/BOW2022_VoorbeeldXML_f86.xml).

## 1. Verzending-header + Aangifte-header (1× per export)

### Komt uit de organisatie-registratie in de app
Zie [`OrganizationPayload`](../backend/app/schemas/export.py), bewerkt via [`OrgBasicFieldsEditor.tsx`](../frontend/src/components/OrgBasicFieldsEditor.tsx).

| Veld | Inhoud |
|---|---|
| `v0014_naam` / `a1011_naamnl1` | organisatienaam |
| `v0015_adres` / `a1013_adresnl` | straat + nr |
| `v0016_postcode` / `a1014_postcodebelgisch` | postcode |
| `v0017_gemeente` / `a1015_gemeente` | gemeente |
| `v0028_landwoonplaats` / `a1016_landwoonplaats` | landcode (default 150 = BE) |
| `v0018_telefoonnummer` | telefoon contactpersoon |
| `v0021_contactpersoon` | naam contactpersoon |
| `v0023_emailadres` | e-mail |
| `v0024_nationaalnr` / `a1005_registratienummer` | KBO |
| `v0022_taalcode` / `a1020_taalcode` | taalcode (1 = NL) |
| `a1027` / `a1029` / `a1030` / `a1031` | optioneel — FR varianten |
| `a1032` / `a1034` / `a1035` / `a1036` | optioneel — DE varianten |

### Komt uit Odoo
Niets in dit blok rechtstreeks. Bij **Test verbinding** kan de KBO opgehaald worden uit `res.company.vat` (zie [`odoo_mapper.py`](../backend/app/services/odoo_mapper.py) — functie `normalize_kbo`).

### Door de app gegenereerd bij export

| Veld | Inhoud |
|---|---|
| `v0002_inkomstenjaar` / `a1002_inkomstenjaar` | gekozen door gebruiker |
| `v0010_bestandtype` | `BELCOTAX` of `BCTEST` |
| `v0011_aanmaakdatum` | huidige datum |
| `v0025_typeenvoi` | vast `0` |

## 2. Fiche28186 (1× per kind-ouder combinatie)

### Komt uit Odoo
Deelnames + contactgegevens, geaggregeerd in [`aggregation.py`](../backend/app/services/aggregation.py).

| Veld | Inhoud |
|---|---|
| `f2011_nationaalnr` | RRN ouder (uit survey-antwoord) |
| `f2013_naam` / `f2114_voornamen` | naam ouder (uit `res.partner`) |
| `f2015_adres` / `f2016_postcodebelgisch` / `f2017_gemeente` / `f2018_landwoonplaats` | adres ouder |
| `f86_2153_nnchild` | RRN kind (uit survey-antwoord) |
| `f86_2106_childname` / `f86_2107_childfirstname` | naam kind (uit survey) |
| `f86_2102_childaddress` / `f86_2139_childpostnr` / `f86_2140_childmunicipality` / `f86_2101_childcountry` | adres kind (fallback = ouderadres) |
| `f86_2055` / `f86_2056_begindate1/enddate1` + optioneel `f86_2093` / `f86_2144_begindate2/enddate2` | periodes (afgeleid uit `start_date` / `end_date` van event registrations, geclusterd) |
| `f86_2060_amount1` + optioneel `f86_2061_amount2` | betaalde bedragen per periode |

### Door de app gegenereerd / berekend

| Veld | Inhoud |
|---|---|
| `f2002_inkomstenjaar`, `f2005_registratienummer` | herhaald uit header |
| `f2007_division` | altijd leeg |
| `f2008_typefiche` | vast `28186` |
| `f2009_volgnummer`, `f2010_referentie` | volgnummer en export-referentie |
| `f2028_typetraitement` | vast `0` |
| `f2029_enkelopgave325` | vast `0` |
| `f86_2031_certificationautorisation` | vast `1` |
| `f86_2059_totaalcontrole` | som controle per fiche |
| `f86_2064_totalamount` | som amount1 + amount2 |
| `f86_2110` / `f86_2113_numberofday1/2` | afgeleid uit halve dagen via [`day_classifier`](../backend/app/services/day_classifier.py) |
| `f86_2111` / `f86_2115_dailytariff1/2` | bedrag / dagen |
| `f86_2163_childbirthdate` | afgeleid uit RRN kind |
| `f86_2100_certifierpostnr`, `f86_2109_certifiercbenumber`, `f86_2154_certifiermunicipality`, `f86_2155_certifiername`, `f86_2156_certifieradres` | herhaald uit organisatie |
| `f86_2164` / `f86_2171` | optioneel — certificeringsgeldigheid (per organisatie ingesteld) |

## 3. Trailers (r8 / r9)

Volledig door de app berekend:

- `r8010_aantalrecords`
- `r8011_controletotaal` / `r8012_controletotaal`
- `r8013_totaalvoorheffingen`
- `r9010_aantallogbestanden`
- `r9011_totaalaantalrecords`
- `r9012_controletotaal` / `r9013_controletotaal` / `r9014_controletotaal`

## Korte samenvatting

| Bron | Velden |
|---|---|
| **App-registratie (org)** | Naam, adres, KBO, taal, contact, optioneel meertalige varianten + cert.-geldigheid |
| **Odoo** | Ouder (RRN / naam / adres), kind (RRN / naam / adres via survey), periodes, bedragen, halve dagen |
| **Door app berekend** | Inkomstenjaar, volgnummers, controletotalen, dagen / dagtarief, geboortedatum uit RRN, vaste codes (typefiche, taal, landcode) |
