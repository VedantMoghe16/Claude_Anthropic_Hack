import pyspark.sql.functions as F
from pyspark.sql.types import *

spark.sql("USE CATALOG workspace")
spark.sql("USE default")

spark.conf.set("spark.sql.shuffle.partitions", "8")

df_citizens = spark.table("workspace.default.aa_citizens_for_llm")
df_schemes  = spark.table("workspace.default.aa_schemes")

print(f"Citizens : {df_citizens.count()}")
print(f"Schemes  : {df_schemes.count()}")

df_citizens_enriched = df_citizens.withColumn(
    "citizen_tags",
    F.concat_ws(",",
        F.when(F.col("housing_status").isin("kutcha","semi_pucca"), F.lit("housing")),
        F.when(F.col("has_bpl_card") == True, F.lit("health")),
        F.when(F.col("has_girl_child") == True, F.lit("women,nutrition,education")),
        F.when(F.col("is_tribal") == True, F.lit("tribal")),
        F.when(F.col("caste_category") == "SC", F.lit("sc")),
        F.when(F.col("caste_category") == "ST", F.lit("st")),
        F.when(F.col("employment_days") < 100, F.lit("employment")),
        F.when(F.col("has_electricity") == False, F.lit("solar")),
        F.when(F.col("land_category").isin("marginal","small","medium"), F.lit("agriculture")),
        F.when(F.col("income_bracket").isin("EWS","LIG"), F.lit("ews_lig")),
        F.when(F.col("income_bracket").isin("EWS","LIG","MIG"), F.lit("ews_lig_mig")),
    )
)

df_schemes_enriched = df_schemes.withColumn(
    "scheme_tag",
    F.when(F.col("eligibility_sql").contains("housing_status"), F.lit("housing"))
     .when(F.col("eligibility_sql").contains("is_tribal"), F.lit("tribal"))
     .when(F.col("eligibility_sql").contains("has_girl_child"), F.lit("women"))
     .when(F.col("eligibility_sql").contains("caste_category = 'SC'"), F.lit("sc"))
     .when(F.col("eligibility_sql").contains("caste_category = 'ST'"), F.lit("st"))
     .when(F.col("eligibility_sql").contains("employment_days"), F.lit("employment"))
     .when(F.col("eligibility_sql").contains("has_electricity"), F.lit("solar"))
     .when(F.col("eligibility_sql").contains("land_acres"), F.lit("agriculture"))
     .otherwise(F.lit("ews_lig"))
)

df_results = (
    df_citizens_enriched.alias("c")
    .join(df_schemes_enriched.alias("s"),
        F.col("c.citizen_tags").contains(F.col("s.scheme_tag")),
        "inner"
    )
    .select(
        F.col("c.citizen_id"),
        F.col("c.district"),
        F.col("c.taluka"),
        F.col("c.village"),
        F.col("c.income_bracket"),
        F.col("c.caste_category"),
        F.col("c.is_tribal"),
        F.col("s.scheme_id"),
        F.col("s.short_code"),
        F.col("s.scheme_name"),
        F.col("s.benefit_amount").alias("benefit"),
        F.col("s.required_docs"),
        F.lit(False).alias("is_notified"),
        F.current_timestamp().alias("matched_at"),
    )
)

total = df_results.count()
print(f"✅ Total eligibility matches: {total:,}")

(df_results.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .partitionBy("district")
    .saveAsTable("workspace.default.aa_eligibility_results"))

print("✅ aa_eligibility_results written")

spark.sql("""
    SELECT district, village,
        COUNT(DISTINCT citizen_id) AS eligible_citizens,
        COUNT(DISTINCT scheme_id)  AS schemes_available
    FROM workspace.default.aa_eligibility_results
    GROUP BY district, village
    ORDER BY eligible_citizens DESC
""").show(20, truncate=False)

spark.sql("""
    SELECT scheme_name,
        COUNT(DISTINCT citizen_id) AS citizens_to_notify
    FROM workspace.default.aa_eligibility_results
    WHERE is_notified = false
    GROUP BY scheme_name
    ORDER BY citizens_to_notify DESC
    LIMIT 10
""").show(truncate=False)

total = spark.table("workspace.default.aa_eligibility_results").count()
print(f"\n✅ PULSE COMPLETE — {total:,} eligibility matches across 3,397 schemes and 1,000 citizens")
print("▶ Ready for Notebook 05 — Adhikar Certificate")