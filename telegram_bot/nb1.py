# ── CELL 1 ────────────────────────────────────────────────────────────────────
spark.sql("USE CATALOG workspace")
spark.sql("USE default")

print("Catalog:", spark.sql("SELECT current_catalog()").collect()[0][0])
print("Schema: ", spark.sql("SELECT current_database()").collect()[0][0])
print("✅ Ready")

# ── CELL 2 ────────────────────────────────────────────────────────────────────
from pyspark.sql.types import *
import pyspark.sql.functions as F

import uuid, hashlib, random
from datetime import datetime, date, timedelta

print("✅ Imports done")

# ── CELL 3 ────────────────────────────────────────────────────────────────────
# UPDATED SCHEMA: Added full_name for personalized bot interaction
citizen_schema = StructType([
    StructField("citizen_id",        StringType(),  False),
    StructField("full_name",         StringType(),  True),   # ✅ NEW FIELD
    StructField("aadhaar_hash",      StringType(),  False),
    StructField("district",          StringType(),  True),
    StructField("taluka",            StringType(),  True),
    StructField("village",           StringType(),  True),
    StructField("ward_no",           IntegerType(), True),
    StructField("survey_no",         StringType(),  True),
    StructField("land_acres",        DoubleType(),  True),
    StructField("annual_income",     DoubleType(),  True),
    StructField("caste_category",    StringType(),  True),
    StructField("is_tribal",         BooleanType(), True),
    StructField("has_girl_child",    BooleanType(), True),
    StructField("girl_child_dob",    DateType(),    True),
    StructField("has_bpl_card",      BooleanType(), True),
    StructField("housing_status",    StringType(),  True),
    StructField("has_electricity",   BooleanType(), True),
    StructField("has_water_source",  BooleanType(), True),
    StructField("employment_days",   IntegerType(), True),
    StructField("created_at",        TimestampType(), True),
    StructField("updated_at",        TimestampType(), True),
    StructField("data_source",       StringType(),  True),
])

print("✅ Schema defined with full_name")

# ── CELL 4 ────────────────────────────────────────────────────────────────────
random.seed(42)

# Lists for random name generation
FIRST_NAMES = ["Rajesh", "Sunita", "Amit", "Priya", "Sanjay", "Anjali", "Vijay", "Meena", "Rahul", "Kavita"]
LAST_NAMES  = ["Patil", "Deshmukh", "Pawar", "Kulkarni", "Jadhav", "More", "Gaekwad", "Shinde"]

DISTRICTS = ["Satara", "Kolhapur", "Sangli"]
TALUKAS   = ["Koregaon", "Patan", "Karad", "Wai"]
VILLAGES  = ["Koregaon Panchayat", "Masur", "Umbraj", "Khatav", "Shirval"]
CASTES    = ["SC", "ST", "OBC", "GEN"]
HOUSING   = ["kutcha", "semi_pucca", "pucca"]
SOURCES   = ["civil_registry", "agriculture_dept", "health_dept"]

def make_citizen(i):
    caste    = random.choice(CASTES)
    is_trib  = (caste == "ST") and (random.random() < 0.7)
    has_girl = random.random() < 0.35
    
    # Generate random full name
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

    girl_dob = (
        date.today() - timedelta(days=random.randint(1, 365*5))
        if has_girl else None
    )

    income = round(random.uniform(30000, 250000), 2)
    land   = round(random.uniform(0.5, 8.0), 2)

    created = datetime.now() - timedelta(days=random.randint(0, 730))
    raw_id  = f"CITIZEN_{i:06d}_{random.randint(1000,9999)}"

    return {
        "citizen_id":       str(uuid.uuid4()),
        "full_name":        name,                            # ✅ ADDED TO RECORD
        "aadhaar_hash":     hashlib.sha256(raw_id.encode()).hexdigest(),
        "district":         random.choice(DISTRICTS),
        "taluka":           random.choice(TALUKAS),
        "village":          random.choice(VILLAGES),
        "ward_no":          random.randint(1, 4),
        "survey_no":        f"{random.randint(100,250)}/{random.randint(1,10)}",
        "land_acres":       float(land),
        "annual_income":    float(income),
        "caste_category":   caste,
        "is_tribal":        is_trib,
        "has_girl_child":   has_girl,
        "girl_child_dob":   girl_dob,
        "has_bpl_card":     (income < 80000) and (random.random() < 0.75),
        "housing_status":   random.choice(HOUSING) if income < 150000 else "pucca",
        "has_electricity":  (income > 60000) or (random.random() < 0.6),
        "has_water_source": random.random() < 0.65,
        "employment_days":  random.randint(0, 100),
        "created_at":       created,
        "updated_at":       datetime.now(),
        "data_source":      random.choice(SOURCES),
    }

records = [make_citizen(i) for i in range(1000)]
df = spark.createDataFrame(records, schema=citizen_schema)

print(f"✅ Generated {df.count()} citizen records with unique names")

# ── CELL 5 ────────────────────────────────────────────────────────────────────
(df.write
   .format("delta")
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .partitionBy("district")
   .saveAsTable("workspace.default.aa_citizens_bronze"))

print("✅ Table written: workspace.default.aa_citizens_bronze")