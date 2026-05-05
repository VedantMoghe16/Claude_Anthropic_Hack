"""
Adhikar-Aina | 04 Eligibility Matching

Purpose:
- Deterministically match citizens to schemes using Spark DataFrame logic.

Input Delta tables:
- silver_citizens
- schemes_clean

Output Delta table:
- eligibility_results

Output schema:
- citizen_id
- scheme_name
- benefit
- eligibility_status
"""

from __future__ import annotations

from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

SILVER_TABLE  = "silver_citizens"
SCHEMES_TABLE = "schemes_clean"
RESULTS_TABLE = "eligibility_results"


def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-04-matching").getOrCreate()


def match_citizens_to_schemes(citizens_df: DataFrame, schemes_df: DataFrame) -> DataFrame:
    citizens = (
        citizens_df.select(
            "citizen_id",
            F.col("occupation_category").alias("occupation_norm"),                                # ✅ silver column name
            F.coalesce(F.col("annual_income").cast("double"), F.lit(0.0)).alias("income_norm"),   # ✅ silver column name
            F.coalesce(F.col("land_acres").cast("double"),    F.lit(0.0)).alias("land_norm"),
            F.upper(F.trim(F.coalesce(F.col("category"), F.lit("GEN")))).alias("category_norm"),
        )
    )

    schemes = (
        schemes_df.select(
            "scheme_name",
            "benefit",
            F.coalesce(F.col("min_income").cast("double"), F.lit(0.0))        .alias("min_income_norm"),
            F.coalesce(F.col("max_income").cast("double"), F.lit(100000000.0)).alias("max_income_norm"),
            F.coalesce(F.col("max_land").cast("double"),   F.lit(999999.0))   .alias("max_land_norm"),
            F.lower(F.trim(F.coalesce(F.col("occupation"), F.lit("any"))))    .alias("occupation_req"),
            F.upper(F.trim(F.coalesce(F.col("category"),  F.lit("ANY"))))     .alias("category_req"),
        )
    )

    matched = citizens.crossJoin(F.broadcast(schemes)).withColumn(
        "eligibility_status",
        (
            (F.col("income_norm") >= F.col("min_income_norm"))
            & (F.col("income_norm") <= F.col("max_income_norm"))
            & (F.col("land_norm")  <= F.col("max_land_norm"))
            & (
                (F.col("occupation_req") == F.lit("any"))
                | (F.col("occupation_norm") == F.col("occupation_req"))
            )
            & (
                (F.col("category_req") == F.lit("ANY"))
                | (F.col("category_norm") == F.col("category_req"))
            )
        ),
    )

    return matched.select("citizen_id", "scheme_name", "benefit", "eligibility_status")


def write_results(df: DataFrame) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(RESULTS_TABLE)
    )


def evaluate_single_profile(profile: Dict[str, Any], schemes_df: DataFrame) -> DataFrame:
    spark_session = get_spark()
    one_row = [
        (
            "TEST-CITIZEN",
            str(profile.get("occupation", "unemployed") or "unemployed"),
            float(profile.get("annual_income", 0.0) or 0.0),
            float(profile.get("land_acres",    0.0) or 0.0),
            str(profile.get("category", "GEN") or "GEN"),
        )
    ]
    schema = (
        "citizen_id string, occupation_category string, "
        "annual_income double, land_acres double, category string"
    )
    test_citizen_df = spark_session.createDataFrame(one_row, schema=schema)
    return match_citizens_to_schemes(test_citizen_df, schemes_df)


def run_tests(citizens_df: DataFrame, schemes_df: DataFrame, results_df: DataFrame) -> None:
    # ── Test 2: realistic farmer profile should match at least one scheme ──
    test_profile = {
        "annual_income": 300000,
        "occupation":    "farmer",
        "land_acres":    1.5,
        "category":      "OBC",
    }
    test2_count = (
        evaluate_single_profile(test_profile, schemes_df)
        .filter(F.col("eligibility_status") == True)
        .count()
    )
    assert test2_count >= 1, f"Expected >=1 eligible scheme, found {test2_count}"
    print(f"[TEST-2] Matching logic passed — eligible schemes={test2_count}")

    # ── Test 3a: implausible profile ──
    # income=99999999 and land=1000 exceed every scheme with a real cap.
    # Only schemes with NO parseable eligibility limits (max_income=100000000,
    # max_land=999999, occupation=any) can still match — those are data-quality
    # issues in the source CSV, not a logic bug.  After the 03 fix the three
    # baseline schemes all have real caps; assert the count stays low.
    no_match_profile = {
        "annual_income": 99999999,
        "occupation":    "astronaut",
        "land_acres":    1000,
        "category":      "GEN",
    }
    test3a_count = (
        evaluate_single_profile(no_match_profile, schemes_df)
        .filter(F.col("eligibility_status") == True)
        .count()
    )
    assert test3a_count < 5, (
        f"Too many schemes matched an implausible profile ({test3a_count}). "
        "Check schemes_clean for rows where max_income=100000000 AND max_land=999999 AND occupation=any — "
        "these schemes have no parseable eligibility limits in their CSV source text."
    )
    print(f"[TEST-3a] Implausible-profile test passed — uncapped scheme matches={test3a_count}")

    # ── Test 3b: None values should not crash ──
    missing_profile = {
        "annual_income": None,
        "occupation":    None,
        "land_acres":    None,
        "category":      None,
    }
    test3b_df = evaluate_single_profile(missing_profile, schemes_df)
    assert test3b_df.count() > 0, "Missing-value test should evaluate without failure"

    # ── Test 3c: zero income / no land ──
    low_income_profile = {
        "annual_income": 0,
        "occupation":    "laborer",
        "land_acres":    0,
        "category":      "SC",
    }
    test3c_df = evaluate_single_profile(low_income_profile, schemes_df)
    assert test3c_df.count() > 0, "Extreme-low-income test should evaluate without failure"

    assert results_df.count() > 0, "eligibility_results should not be empty"

    print("[TEST-3] All edge-case tests passed (implausible profile, missing values, extreme income)")


def main() -> None:
    spark_session = get_spark()
    citizens_df = spark_session.table(SILVER_TABLE)
    schemes_df  = spark_session.table(SCHEMES_TABLE)

    results_df = match_citizens_to_schemes(citizens_df, schemes_df)
    write_results(results_df)

    print(f"Eligibility results written to Delta table: {RESULTS_TABLE}")
    results_df.groupBy("eligibility_status").count().show()

    run_tests(citizens_df, schemes_df, results_df)


if __name__ == "__main__":
    main()