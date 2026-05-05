"""
Adhikar-Aina | 02 Silver Citizens

Reads bronze_citizens, performs feature engineering + tagging,
and writes Delta table:
- silver_citizens
"""

from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BRONZE_TABLE = "bronze_citizens"
SILVER_TABLE = "silver_citizens"


def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-02-silver").getOrCreate()


def build_silver_dataframe(bronze_df):
    base = (
        bronze_df
        .withColumn("district",      F.initcap(F.trim(F.coalesce(F.col("district"),        F.lit("Pune")))))
        .withColumn("occupation",    F.lower(F.trim(F.coalesce(F.col("occupation"),         F.lit("unemployed")))))
        .withColumn("annual_income", F.coalesce(F.col("annual_income").cast("double"),      F.lit(0.0)))   # ✅ correct bronze column name
        .withColumn("land_acres",    F.coalesce(F.col("land_acres").cast("double"),         F.lit(0.0)))
        .withColumn("category",      F.upper(F.trim(F.coalesce(F.col("caste_category"),     F.lit("GEN")))))  # ✅ correct bronze column name
        .withColumn("has_daughter",  F.coalesce(F.col("has_girl_child").cast("boolean"),    F.lit(False)))    # ✅ correct bronze column name
    )

    engineered = (
        base
        .withColumn(
            "income_bracket",
            F.when(F.col("annual_income") < 100000,  F.lit("EWS"))
            .when(F.col("annual_income") < 300000,   F.lit("LIG"))
            .when(F.col("annual_income") < 1000000,  F.lit("MIG"))
            .otherwise(F.lit("HIG")),
        )
        .withColumn(
            "land_category",
            F.when(F.col("land_acres") < 1, F.lit("marginal"))
            .when(F.col("land_acres") < 2, F.lit("small"))
            .when(F.col("land_acres") < 5, F.lit("medium"))
            .otherwise(F.lit("large")),
        )
        .withColumn(
            "occupation_category",
            F.when(F.col("occupation") == "farmer",      F.lit("farmer"))
            .when(F.col("occupation") == "student",      F.lit("student"))
            .when(F.col("occupation") == "worker",       F.lit("worker"))
            .when(F.col("occupation") == "entrepreneur", F.lit("entrepreneur"))
            .otherwise(F.lit("unemployed")),
        )
    )

    tags_array = F.array(
        F.col("occupation_category"),
        F.when(F.col("annual_income") < 300000,               F.lit("low_income"))  .otherwise(F.lit("")),
        F.when(F.col("occupation_category") == "farmer",      F.lit("agriculture")) .otherwise(F.lit("")),
        F.when(F.col("occupation_category") == "student",     F.lit("education"))   .otherwise(F.lit("")),
        F.when(F.col("occupation_category") == "unemployed",  F.lit("welfare"))     .otherwise(F.lit("")),
        F.when(F.col("has_daughter"),                          F.lit("girl_child"))  .otherwise(F.lit("")),
    )

    tagged = (
        engineered
        .withColumn("tags_array",   tags_array)
        .withColumn("clean_tags",   F.expr("filter(tags_array, x -> x != '')"))
        .withColumn("citizen_tags", F.concat_ws(",", F.col("clean_tags")))
        .drop("tags_array", "clean_tags")
        .select(
            "citizen_id",
            "district",
            "annual_income",        # ✅ kept numeric for downstream range matching
            "income_bracket",
            "occupation_category",
            "land_acres",           # ✅ kept numeric for downstream range matching
            "land_category",
            "category",
            "has_daughter",
            "citizen_tags",
        )
    )
    return tagged


def main() -> None:
    spark_session = get_spark()
    bronze_df = spark_session.table(BRONZE_TABLE)
    silver_df = build_silver_dataframe(bronze_df)

    (
        silver_df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(SILVER_TABLE)
    )

    print("silver_citizens table written")
    spark_session.sql("SELECT * FROM silver_citizens LIMIT 5").show()


if __name__ == "__main__":
    main()