# ── CELL 1 ────────────────────────────────────────────────────────────────────
import pyspark.sql.functions as F
from pyspark.sql.types import *

spark.sql("USE CATALOG workspace")
spark.sql("USE default")

# ── BRONZE ────────────────────────────────────────────────────────────────────
df_bronze_raw = spark.table("workspace.default.updated_data")

print("Kaggle columns:", df_bronze_raw.columns)
print(f"Raw scheme count: {df_bronze_raw.count()}")

(df_bronze_raw.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.default.aa_schemes_bronze"))

print("✅ aa_schemes_bronze written")
# ── CELL 2 ────────────────────────────────────────────────────────────────────
# Eligibility mapping (rule engine v1)

eligibility_map = {
    "housing":      "housing_status IN ('kutcha', 'semi_pucca') AND has_bpl_card = true",
    "agriculture":  "land_acres > 0 AND income_bracket IN ('EWS', 'LIG', 'MIG')",
    "women":        "has_girl_child = true",
    "tribal":       "is_tribal = true",
    "employment":   "employment_days < 100",
    "nutrition":    "has_girl_child = true",
    "sc":           "caste_category = 'SC'",
    "st":           "caste_category = 'ST'",
    "solar":        "has_electricity = false",
    "health":       "has_bpl_card = true",
    "education":    "has_girl_child = true",
}

default_sql = "income_bracket IN ('EWS', 'LIG')"

def map_eligibility(text):
    if not text:
        return default_sql
    text = str(text).lower()
    for key, sql in eligibility_map.items():
        if key in text:
            return sql
    return default_sql

map_elig_udf = F.udf(map_eligibility, StringType())
# ── CELL 3 ──────────────────────────────────────────────────────────────────
from pyspark.sql.functions import sha2, concat_ws

df_bronze = spark.table("workspace.default.aa_schemes_bronze")

# FIX 1: Replace Python UDF with native SQL CASE WHEN (no Python UDF overhead)
eligibility_expr = F.when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("housing"),
    F.lit("housing_status IN ('kutcha', 'semi_pucca') AND has_bpl_card = true")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("agri"),
    F.lit("land_acres > 0 AND income_bracket IN ('EWS', 'LIG', 'MIG')")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("women"),
    F.lit("has_girl_child = true")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("tribal"),
    F.lit("is_tribal = true")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("employment"),
    F.lit("employment_days < 100")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("solar"),
    F.lit("has_electricity = false")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains("health"),
    F.lit("has_bpl_card = true")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains(" sc"),
    F.lit("caste_category = 'SC'")
).when(
    F.lower(F.concat_ws(" ", F.col("schemeCategory"), F.col("tags"), F.col("details"), F.col("eligibility"))).contains(" st"),
    F.lit("caste_category = 'ST'")
).otherwise(
    F.lit("income_bracket IN ('EWS', 'LIG')")
)

df_silver = (
    df_bronze

    # FIX 2: Use sha2 hash for scheme_id — deterministic, no shuffle, no cast
    .withColumn("scheme_id",
        F.concat(F.lit("SCH"), F.substring(F.sha2(F.col("scheme_name"), 256), 1, 6))
    )

    .withColumn("scheme_name",    F.col("scheme_name"))
    .withColumn("benefit_type",   F.col("schemeCategory"))
    .withColumn("benefit_amount", F.col("benefits"))
    .withColumn("required_docs",  F.col("documents"))

    .withColumn("short_code",
        F.regexp_replace(
            F.upper(F.substring(F.col("scheme_name"), 1, 15)),
            " ", "-"
        )
    )

    # FIX 1: Native expression instead of Python UDF
    .withColumn("eligibility_sql", eligibility_expr)

    .withColumn("is_active",   F.lit(True))
    .withColumn("created_at",  F.current_timestamp())

    .select(
        "scheme_id", "scheme_name", "short_code",
        "benefit_type", "benefit_amount",
        "eligibility_sql", "required_docs",
        "is_active", "created_at"
    )

    .dropDuplicates(["scheme_name"])
    .filter(F.col("scheme_name").isNotNull())
)

# FIX 3: Write FIRST, then count from the saved table — avoids double evaluation
(df_silver.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.default.aa_schemes"))

print("✅ aa_schemes written")
# ── CELL 4 ── (verification only, reads from saved table — fast)
spark.sql("""
    SELECT benefit_type, COUNT(*) as scheme_count
    FROM workspace.default.aa_schemes
    GROUP BY benefit_type
    ORDER BY scheme_count DESC
""").show(20, truncate=False)

spark.sql("""
    SELECT scheme_id, scheme_name, eligibility_sql
    FROM workspace.default.aa_schemes
    LIMIT 10
""").show(truncate=False)

print(f"\n✅ Total schemes: {spark.table('workspace.default.aa_schemes').count()}")
# ── CELL 5 ────────────────────────────────────────────────────────────────────
spark.sql("""
    SELECT benefit_type, COUNT(*) as scheme_count
    FROM workspace.default.aa_schemes
    GROUP BY benefit_type
    ORDER BY scheme_count DESC
""").show(20, truncate=False)

spark.sql("""
    SELECT scheme_id, scheme_name, eligibility_sql
    FROM workspace.default.aa_schemes
    LIMIT 10
""").show(truncate=False)

print(f"\n✅ Total schemes: {spark.table('workspace.default.aa_schemes').count()}")
