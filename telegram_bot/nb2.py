# Adhikar-Aina | Notebook 02 — Silver Layer + PII Masking
# Catalog: workspace.default

# ── CELL 1 ────────────────────────────────────────────────────────────────────
spark.sql("USE CATALOG workspace")
spark.sql("USE default")
print("✅ Ready")

# ── CELL 2 ────────────────────────────────────────────────────────────────────
from pyspark.sql.functions import *
from pyspark.sql.types import IntegerType

df_bronze = spark.table("workspace.default.aa_citizens_bronze")

# The Silver Layer now preserves 'full_name' for the bot's greeting logic
# while continuing to mask sensitive raw data like Aadhaar and Income.
df_silver = (
    df_bronze
    .drop("aadhaar_hash")  # Masked: Never passes to LLM or Bot
    .withColumn("income_bracket",
        when(col("annual_income") < 50000,  lit("EWS"))
       .when(col("annual_income") < 100000, lit("LIG"))
       .when(col("annual_income") < 200000, lit("MIG"))
       .otherwise(lit("HIG"))
    )
    .withColumn("land_category",
        when(col("land_acres") < 1.0, lit("marginal"))
       .when(col("land_acres") < 2.5, lit("small"))
       .when(col("land_acres") < 5.0, lit("medium"))
       .otherwise(lit("large"))
    )
    .withColumn("girl_child_age_years",
        when(
            col("has_girl_child") & col("girl_child_dob").isNotNull(),
            floor(datediff(current_date(), col("girl_child_dob")) / 365)
        ).otherwise(lit(None).cast(IntegerType()))
    )
    # Removing raw PII while keeping 'full_name' in the Silver table
    .drop("annual_income", "land_acres", "girl_child_dob")
    .withColumn("silver_processed_at", current_timestamp())
)

print(f"✅ Silver transform done (Names preserved). Rows: {df_silver.count()}")

# ── CELL 3 ────────────────────────────────────────────────────────────────────
(df_silver.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .partitionBy("district")
    .saveAsTable("workspace.default.aa_citizens_silver"))

print("✅ Table written: workspace.default.aa_citizens_silver")

# ── CELL 4 ────────────────────────────────────────────────────────────────────
# Enable Change Data Feed — allows the notification engine to trigger 
# proactively when life events are registered.
spark.sql("""
    ALTER TABLE workspace.default.aa_citizens_silver
    SET TBLPROPERTIES (
        'delta.enableChangeDataFeed' = 'true',
        'delta.autoOptimize.optimizeWrite' = 'true',
        'delta.autoOptimize.autoCompact' = 'true'
    )
""")
print("✅ Change Data Feed enabled")

# ── CELL 5 ────────────────────────────────────────────────────────────────────
# SOVEREIGN FIREWALL: This view is PII-FREE. 
# It includes attributes for AI matching but EXCLUDES 'full_name'.
spark.sql("""
    CREATE OR REPLACE VIEW workspace.default.aa_citizens_for_llm AS
    SELECT
        citizen_id,
        district,
        taluka,
        village,
        ward_no,
        caste_category,
        is_tribal,
        has_girl_child,
        girl_child_age_years,
        has_bpl_card,
        housing_status,
        has_electricity,
        has_water_source,
        employment_days,
        income_bracket,
        land_category,
        data_source,
        updated_at
    FROM workspace.default.aa_citizens_silver
""")
print("✅ LLM-Safe View created (PII Firewalled)")

# ── CELL 6 ────────────────────────────────────────────────────────────────────
print("\n── Silver distribution ──")
spark.sql("""
    SELECT income_bracket, COUNT(*) as citizens,
           SUM(CAST(is_tribal AS INT)) as tribal,
           SUM(CAST(has_bpl_card AS INT)) as bpl
    FROM workspace.default.aa_citizens_silver
    GROUP BY income_bracket ORDER BY income_bracket
""").show()

print("\n── Verification: full_name exists in Silver but NOT in LLM view ──")
print("Silver Table Columns:", spark.table("workspace.default.aa_citizens_silver").columns)
print("LLM View Columns:   ", spark.table("workspace.default.aa_citizens_for_llm").columns)

print("\n✅ Notebook 02 complete — Names are ready for the Bot login flow.")