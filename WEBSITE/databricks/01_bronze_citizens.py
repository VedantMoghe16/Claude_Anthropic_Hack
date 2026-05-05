"""
Adhikar-Aina | 01 Bronze Citizens

Creates synthetic citizen records and writes Delta table:
- bronze_citizens
"""

from __future__ import annotations

import random
from datetime import datetime

from pyspark.sql import SparkSession

BRONZE_TABLE = "bronze_citizens"
ROW_COUNT = 1000


FIRST_NAMES = [
    "Aarav",
    "Vihaan",
    "Reyansh",
    "Ishaan",
    "Aanya",
    "Saanvi",
    "Diya",
    "Anaya",
    "Rohan",
    "Meera",
    "Nikhil",
    "Pooja",
    "Kavya",
    "Rahul",
    "Sneha",
    "Arjun",
    "Priya",
    "Kiran",
    "Sunita",
    "Mahesh",
]
LAST_NAMES = [
    "Patil",
    "Shinde",
    "Jadhav",
    "Pawar",
    "Kulkarni",
    "Deshmukh",
    "More",
    "Chavan",
    "Kale",
    "Joshi",
]
DISTRICTS = ["Pune", "Satara", "Nashik", "Kolhapur", "Nagpur", "Solapur", "Ahmednagar"]
CASTE_CATEGORIES = ["SC", "ST", "OBC", "GEN"]
GENDERS = ["Male", "Female"]
OCCUPATIONS = ["farmer", "student", "worker", "entrepreneur", "unemployed"]
EMPLOYMENT_TYPES = ["daily_wage", "salaried", "self_employed"]
HOUSING = ["kutcha", "semi_pucca", "pucca"]
LANGUAGES = ["hi", "mr", "en"]



def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-01-bronze").getOrCreate()



def _safe_choice(weighted_pairs: list[tuple[str, float]]) -> str:
    values = [v for v, _ in weighted_pairs]
    weights = [w for _, w in weighted_pairs]
    return random.choices(values, weights=weights, k=1)[0]



def _generate_record(index: int) -> dict:
    occupation = _safe_choice(
        [
            ("farmer", 0.32),
            ("worker", 0.24),
            ("entrepreneur", 0.12),
            ("student", 0.16),
            ("unemployed", 0.16),
        ]
    )

    if occupation == "farmer":
        annual_income = round(random.uniform(40000, 850000), 2)
        land_acres = round(random.uniform(0.1, 10.0), 2)
        employment_type = _safe_choice([("self_employed", 0.7), ("daily_wage", 0.2), ("salaried", 0.1)])
    elif occupation == "worker":
        annual_income = round(random.uniform(30000, 600000), 2)
        land_acres = round(random.uniform(0.0, 1.2), 2)
        employment_type = _safe_choice([("daily_wage", 0.5), ("salaried", 0.35), ("self_employed", 0.15)])
    elif occupation == "entrepreneur":
        annual_income = round(random.uniform(150000, 2000000), 2)
        land_acres = round(random.uniform(0.0, 3.0), 2)
        employment_type = _safe_choice([("self_employed", 0.8), ("salaried", 0.1), ("daily_wage", 0.1)])
    elif occupation == "student":
        annual_income = round(random.uniform(0, 250000), 2)
        land_acres = round(random.uniform(0.0, 0.8), 2)
        employment_type = _safe_choice([("salaried", 0.05), ("self_employed", 0.1), ("daily_wage", 0.85)])
    else:
        annual_income = round(random.uniform(0, 200000), 2)
        land_acres = round(random.uniform(0.0, 0.5), 2)
        employment_type = _safe_choice([("daily_wage", 0.55), ("self_employed", 0.25), ("salaried", 0.20)])

    caste_category = _safe_choice([("OBC", 0.42), ("GEN", 0.32), ("SC", 0.18), ("ST", 0.08)])
    is_tribal = caste_category == "ST" and random.random() < 0.85

    age = random.randint(0, 80)
    gender = _safe_choice([("Male", 0.52), ("Female", 0.48)])

    has_children = age >= 21 and random.random() < 0.58
    has_girl_child = has_children and random.random() < 0.47

    household_size = random.randint(1, 8)

    has_bpl_card = (annual_income < 120000 and household_size >= 4) or (annual_income < 80000)
    has_bpl_card = bool(has_bpl_card or (annual_income < 250000 and random.random() < 0.08))

    if has_bpl_card:
        housing_status = _safe_choice([("kutcha", 0.5), ("semi_pucca", 0.35), ("pucca", 0.15)])
    else:
        housing_status = _safe_choice([("kutcha", 0.12), ("semi_pucca", 0.36), ("pucca", 0.52)])

    employment_days = random.randint(0, 365)

    primary_language = _safe_choice([("mr", 0.64), ("hi", 0.25), ("en", 0.11)])

    return {
        "citizen_id": f"CIT-{index:04d}",
        "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "district": random.choice(DISTRICTS),
        "state": "Maharashtra",
        "age": age,
        "gender": gender,
        "caste_category": caste_category,
        "is_tribal": bool(is_tribal),
        "annual_income": float(annual_income),
        "occupation": occupation,
        "employment_type": employment_type,
        "land_acres": float(land_acres),
        "has_children": bool(has_children),
        "has_girl_child": bool(has_girl_child),
        "household_size": household_size,
        "has_bpl_card": bool(has_bpl_card),
        "housing_status": housing_status,
        "employment_days": employment_days,
        "primary_language": primary_language,
        "created_at": datetime.utcnow(),
    }



def build_bronze_dataframe(spark_session: SparkSession):
    random.seed(42)
    rows = [_generate_record(i) for i in range(1, ROW_COUNT + 1)]
    return spark_session.createDataFrame(rows)



def main() -> None:
    spark_session = get_spark()
    bronze_df = build_bronze_dataframe(spark_session)

    (
        bronze_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(BRONZE_TABLE)
    )

    print("bronze_citizens table written")
    spark_session.sql("SELECT COUNT(*) FROM bronze_citizens").show()


if __name__ == "__main__":
    main()
