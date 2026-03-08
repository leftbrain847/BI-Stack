"""
Synthetic healthcare data generator for BI-Stack POC.

Generates five interrelated CSVs with deliberate edge cases:
  - patients.csv
  - providers.csv
  - encounters.csv
  - diagnoses.csv
  - billing.csv

Run: python scripts/generate_data.py
Output: data/raw/*.csv
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

OUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Susan", "Richard", "Jessica",
    "Joseph", "Sarah", "Thomas", "Karen", "Charles", "Lisa", "Christopher",
    "Nancy", "Daniel", "Betty", "Matthew", "Margaret", "Anthony", "Sandra",
    "Mark", "Ashley", "Donald", "Dorothy", "Steven", "Kimberly", "Paul",
    "Emily", "Andrew", "Donna", "Kenneth", "Michelle", "Joshua", "Carol",
    "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah", "Timothy",
    "Stephanie", "Ronald", "Rebecca", "Edward", "Sharon", "Jason", "Laura",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

SPECIALTIES = [
    "Internal Medicine", "Family Medicine", "Cardiology", "Endocrinology",
    "Orthopedics", "Neurology", "Gastroenterology", "Pulmonology",
    "Nephrology", "Oncology", "Psychiatry", "Dermatology", "Urology",
    "Rheumatology", "Infectious Disease",
]

STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

INSURANCES = ["Medicare", "Medicaid", "BCBS Commercial", "Aetna", "UnitedHealth",
              "Cigna", "Humana", "Self-Pay", "Tricare", "None"]

RACE_ETHNICITIES = [
    "White Non-Hispanic", "Black or African American", "Hispanic or Latino",
    "Asian", "American Indian or Alaska Native", "Two or More Races",
    "Unknown", "Declined to Specify",
]

CHIEF_COMPLAINTS = [
    "Chest pain", "Shortness of breath", "Abdominal pain", "Headache",
    "Back pain", "Fatigue", "Dizziness", "Nausea and vomiting",
    "Cough", "Fever", "Joint pain", "Diabetes management follow-up",
    "Hypertension management", "Annual wellness visit", "Depression screening",
    "Medication refill", "Post-surgical follow-up", "Palpitations",
    "Urinary symptoms", "Skin rash",
]

# ICD-10 codes — (code_with_dot, description)
ICD10_CODES = [
    ("E11.9",  "Type 2 diabetes mellitus without complications"),
    ("I10",    "Essential (primary) hypertension"),
    ("J18.9",  "Pneumonia, unspecified organism"),
    ("M54.5",  "Low back pain"),
    ("F32.9",  "Major depressive disorder, single episode, unspecified"),
    ("E78.5",  "Hyperlipidemia, unspecified"),
    ("J44.1",  "Chronic obstructive pulmonary disease with acute exacerbation"),
    ("N18.3",  "Chronic kidney disease, stage 3"),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina"),
    ("Z00.00", "Encounter for general adult medical examination without abnormal findings"),
    ("K21.0",  "Gastro-esophageal reflux disease with esophagitis"),
    ("F41.1",  "Generalized anxiety disorder"),
    ("M17.11", "Primary osteoarthritis, right knee"),
    ("I50.9",  "Heart failure, unspecified"),
    ("E11.65", "Type 2 diabetes mellitus with hyperglycemia"),
    ("G43.909","Migraine, unspecified, not intractable, without status migrainosus"),
    ("J06.9",  "Acute upper respiratory infection, unspecified"),
    ("R05.9",  "Cough, unspecified"),
    ("Z12.11", "Encounter for screening for malignant neoplasm of colon"),
    ("B96.81", "Helicobacter pylori as the cause of diseases classified elsewhere"),
]

DENIAL_REASONS = [
    "Not medically necessary",
    "Prior authorization required",
    "Duplicate claim",
    "Member not eligible on date of service",
    "Provider not in network",
    "Claim filed after timely filing limit",
    "Missing or invalid diagnosis code",
]


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def fmt_date(d: date, fmt: str = "iso") -> str:
    if fmt == "iso":
        return d.isoformat()
    if fmt == "us":
        return d.strftime("%m/%d/%Y")
    return d.isoformat()


# ── patients ───────────────────────────────────────────────────────────────

def generate_patients(n: int = 200) -> list[dict]:
    rows = []
    for i in range(n):
        pid = 1001 + i
        dob = rand_date(date(1940, 1, 1), date(2005, 12, 31))

        # Edge case 1: ~5% DOB in US format instead of ISO
        dob_str = fmt_date(dob, "us" if random.random() < 0.05 else "iso")

        # Edge case 2: gender — inconsistent casing / coding
        gender_pool = ["Male", "Female", "M", "F", "male", "female",
                       "MALE", "FEMALE", "Other", "Unknown", ""]
        gender_weights = [20, 20, 5, 5, 5, 5, 3, 3, 2, 2, 1]
        gender = random.choices(gender_pool, weights=gender_weights)[0]

        # Edge case 3: zip — ~10% nine-digit
        base_zip = f"{random.randint(10000, 99999):05d}"
        if random.random() < 0.10:
            zip_code = f"{base_zip}-{random.randint(1000, 9999)}"
        else:
            zip_code = base_zip

        # Edge case 4: is_active — mixed bool encoding
        active_pool = ["True", "False", "1", "0", "true", "false"]
        active_weights = [60, 8, 15, 5, 8, 4]
        is_active = random.choices(active_pool, weights=active_weights)[0]

        rows.append({
            "patient_id":        pid,
            "first_name":        random.choice(FIRST_NAMES),
            "last_name":         random.choice(LAST_NAMES),
            "date_of_birth":     dob_str,
            "gender":            gender,
            "race_ethnicity":    random.choice(RACE_ETHNICITIES),
            "zip_code":          zip_code,
            "primary_insurance": random.choice(INSURANCES),
            "created_date":      rand_date(date(2018, 1, 1), date(2022, 12, 31)).isoformat(),
            "is_active":         is_active,
        })
    return rows


# ── providers ──────────────────────────────────────────────────────────────

def generate_providers(n: int = 50) -> list[dict]:
    rows = []
    for i in range(n):
        pvid = 2001 + i

        # Edge case 5: NPI — ~5% start with 0 (lost if stored as int)
        if random.random() < 0.05:
            npi = f"0{random.randint(100000000, 999999999)}"  # 10 chars, starts with 0
        else:
            npi = f"{random.randint(1000000000, 9999999999)}"

        rows.append({
            "provider_id":   pvid,
            "npi":           npi,
            "first_name":    random.choice(FIRST_NAMES),
            "last_name":     random.choice(LAST_NAMES),
            "specialty":     random.choice(SPECIALTIES),
            "facility_id":   random.randint(3001, 3010),  # Edge case 6: FK to non-existent table
            "license_state": random.choice(STATES),
            "is_active":     random.choice(["True", "False", "True", "True", "True"]),
        })
    return rows


# ── encounters ─────────────────────────────────────────────────────────────

def generate_encounters(n: int = 500, patient_ids: list[int] = None,
                        provider_ids: list[int] = None) -> list[dict]:
    rows = []
    for i in range(n):
        eid = 3001 + i
        enc_date = rand_date(date(2022, 1, 1), date(2024, 6, 30))
        enc_type = random.choices(
            ["Outpatient", "Inpatient", "Telehealth", "Emergency"],
            weights=[55, 15, 20, 10],
        )[0]

        # Edge case 7: ~3% encounters with orphaned patient_id (not in patients table)
        if random.random() < 0.03:
            pid = random.randint(1201, 1215)
        else:
            pid = random.choice(patient_ids)

        discharge_date = None
        los_days = None
        if enc_type == "Inpatient":
            los = random.randint(1, 14)
            los_days = round(los + random.random(), 1)
            discharge_date = (enc_date + timedelta(days=los)).isoformat()

        rows.append({
            "encounter_id":   eid,
            "patient_id":     pid,
            "provider_id":    random.choice(provider_ids),
            "encounter_date": enc_date.isoformat(),
            "encounter_type": enc_type,
            "discharge_date": discharge_date or "",
            "chief_complaint": random.choice(CHIEF_COMPLAINTS),
            "admit_status":   "Admitted" if enc_type == "Inpatient" else "Not Admitted",
            "los_days":       los_days if los_days is not None else "",
            "total_charge":   round(random.uniform(75, 45000), 2),
        })
    return rows


# ── diagnoses ──────────────────────────────────────────────────────────────

def generate_diagnoses(encounter_ids: list[int]) -> list[dict]:
    rows = []
    diag_id = 4001
    for eid in encounter_ids:
        n_diags = random.choices([1, 2, 3, 4, 5, 6], weights=[30, 25, 20, 12, 8, 5])[0]
        chosen = random.sample(ICD10_CODES, min(n_diags, len(ICD10_CODES)))
        enc_date = rand_date(date(2022, 1, 1), date(2024, 6, 30))
        for seq, (code, desc) in enumerate(chosen, start=1):
            # Edge case 8: ~40% ICD codes stored without dot
            if random.random() < 0.40:
                code = code.replace(".", "")

            rows.append({
                "diagnosis_id":          diag_id,
                "encounter_id":          eid,
                "icd10_code":            code,
                "diagnosis_description": desc,
                "is_primary":            "True" if seq == 1 else "False",
                "diagnosis_date":        enc_date.isoformat(),
                "sequence_number":       seq,
            })
            diag_id += 1
    return rows


# ── billing ────────────────────────────────────────────────────────────────

def generate_billing(encounters: list[dict]) -> list[dict]:
    rows = []
    claim_id = 5001

    # Edge case 9: ~10% of encounters get a second claim (duplicate encounter_id in billing)
    double_claim_eids = set(
        random.sample([e["encounter_id"] for e in encounters],
                      k=int(len(encounters) * 0.10))
    )

    status_pool   = ["PAID", "Paid", "paid", "DENIED", "Denied", "denied",
                     "PENDING", "Pending", "pending", "VOID"]
    status_weights = [20, 15, 10, 10, 8, 5, 10, 8, 5, 9]

    for enc in encounters:
        for pass_num in range(1 + (1 if enc["encounter_id"] in double_claim_eids else 0)):
            billed = round(float(enc["total_charge"]) * random.uniform(0.9, 1.1), 2)

            # Edge case 10: ~5% allowed > billed
            if random.random() < 0.05:
                allowed = round(billed * random.uniform(1.01, 1.20), 2)
            else:
                allowed = round(billed * random.uniform(0.50, 0.95), 2)

            paid_pct = random.uniform(0.80, 1.0)
            status = random.choices(status_pool, weights=status_weights)[0]

            # Edge case 11: adjustment_amount is negative
            adjustment = round(allowed - billed, 2)

            claim_date = date.fromisoformat(enc["encounter_date"])
            paid_date = ""
            denial_reason = ""

            status_norm = status.lower()
            if status_norm == "paid":
                paid_amount = round(allowed * paid_pct, 2)
                paid_date = (claim_date + timedelta(days=random.randint(14, 60))).isoformat()
            elif status_norm == "denied":
                paid_amount = 0.0
                denial_reason = random.choice(DENIAL_REASONS)
            elif status_norm == "void":
                paid_amount = 0.0
            else:  # pending
                paid_amount = 0.0

            rows.append({
                "claim_id":        claim_id,
                "encounter_id":    enc["encounter_id"],
                "patient_id":      enc["patient_id"],
                "payer_id":        random.randint(6001, 6020),
                "billed_amount":   billed,
                "allowed_amount":  allowed,
                "paid_amount":     paid_amount,
                "adjustment_amount": adjustment,
                "claim_status":    status,
                "claim_date":      claim_date.isoformat(),
                "paid_date":       paid_date,
                "denial_reason":   denial_reason,
            })
            claim_id += 1

    return rows


# ── write CSV ──────────────────────────────────────────────────────────────

def write_csv(filename: str, rows: list[dict]) -> None:
    path = OUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name:25s} {len(rows):>5,} rows")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generating synthetic healthcare CSVs...")

    patients  = generate_patients(200)
    providers = generate_providers(50)

    patient_ids  = [p["patient_id"]  for p in patients]
    provider_ids = [p["provider_id"] for p in providers]

    encounters = generate_encounters(500, patient_ids, provider_ids)
    enc_ids    = [e["encounter_id"] for e in encounters]

    diagnoses = generate_diagnoses(enc_ids)
    billing   = generate_billing(encounters)

    write_csv("patients.csv",   patients)
    write_csv("providers.csv",  providers)
    write_csv("encounters.csv", encounters)
    write_csv("diagnoses.csv",  diagnoses)
    write_csv("billing.csv",    billing)

    print(f"\nDone. Files written to {OUT_DIR}")
    print("\nEdge cases baked in:")
    print("  1. ~5%  patients have DOB in MM/DD/YYYY (rest ISO)")
    print("  2. ~10% patients have 9-digit zip codes")
    print("  3. gender values are inconsistently cased/coded")
    print("  4. is_active uses mixed boolean encoding (True/1/true/False/0/false)")
    print("  5. ~5%  provider NPIs start with 0 (lost if cast to INT)")
    print("  6. provider.facility_id references a table not in this dataset")
    print("  7. ~3%  encounters have orphaned patient_id")
    print("  8. ~40% ICD-10 codes have dots stripped (E119 vs E11.9)")
    print("  9. ~10% encounters appear twice in billing (duplicate FK)")
    print(" 10. ~5%  billing rows have allowed_amount > billed_amount")
    print(" 11. adjustment_amount contains negative values")
    print(" 12. claim_status has inconsistent casing (PAID/Paid/paid)")


if __name__ == "__main__":
    main()
