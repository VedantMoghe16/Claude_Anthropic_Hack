"""
Adhikar-Aina | 03 Schemes Engine

Purpose:
- Load raw schemes CSV.
- Convert unstructured scheme text into deterministic, structured eligibility fields.
- Produce a clean scheme table for matching.

Input file:
- data/updated_data.csv

Output Delta table:
- schemes_clean
"""

from __future__ import annotations

import re
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
)

SCHEMES_CLEAN_TABLE = "schemes_clean"


def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-03-schemes").getOrCreate()


def read_schemes_csv(spark_session: SparkSession) -> DataFrame:
    path = "/Workspace/Users/anant.asati.moodi@gmail.com/bharatbricks_hackathon/data/updated_data.csv"
    return (
        spark_session.read.option("header", True)
        .option("inferSchema", True)
        .csv(path)
    )


def find_column(df: DataFrame, candidates: list[str]) -> Optional[str]:
    lookup = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def parse_income_min(text: str) -> Optional[float]:
    if not text:
        return None
    text_lower = text.lower()
    if "above" in text_lower or "more than" in text_lower:
        value = parse_first_lakh_value(text_lower)
        if value is not None:
            return value
    return None


def parse_income_max(text: str) -> Optional[float]:
    if not text:
        return None
    text_lower = text.lower()

    lakh_value = parse_first_lakh_value(text_lower)
    if lakh_value is not None:
        return lakh_value

    number_match = re.search(r"(\d{5,7})", text_lower)
    if number_match:
        return float(number_match.group(1))

    return None


def parse_first_lakh_value(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*lakh", text)
    if match:
        return float(match.group(1)) * 100000.0

    match_short = re.search(r"(\d+(?:\.\d+)?)\s*l\b", text)
    if match_short:
        return float(match_short.group(1)) * 100000.0

    return None


def parse_max_land(text: str) -> Optional[float]:
    if not text:
        return None
    text_lower = text.lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(acre|acres)", text_lower)
    if match:
        return float(match.group(1))
    return None


def parse_occupation(text: str) -> str:
    if not text:
        return "any"
    text_lower = text.lower()
    if any(token in text_lower for token in ["farmer", "agri", "kisan", "cultivator"]):
        return "farmer"
    if any(token in text_lower for token in ["student", "scholar"]):
        return "student"
    if any(token in text_lower for token in ["artisan", "craft", "vishwakarma"]):
        return "artisan"
    if any(token in text_lower for token in ["unemployed", "jobless", "employment guarantee"]):
        return "unemployed"
    if any(token in text_lower for token in ["labor", "labour", "worker"]):
        return "laborer"
    return "any"


def parse_category(text: str) -> str:
    if not text:
        return "ANY"
    text_lower = text.lower()
    if "sc" in text_lower:
        return "SC"
    if "st" in text_lower or "tribal" in text_lower:
        return "ST"
    if "obc" in text_lower:
        return "OBC"
    if "general" in text_lower or "gen" in text_lower:
        return "GEN"
    return "ANY"


def extraction_schema() -> StructType:
    return StructType(
        [
            StructField("min_income", DoubleType(), True),
            StructField("max_income", DoubleType(), True),
            StructField("occupation", StringType(), True),
            StructField("max_land",   DoubleType(), True),
            StructField("category",   StringType(), True),
        ]
    )


def extract_rule_fields(
    text: Optional[str],
) -> tuple[Optional[float], Optional[float], str, Optional[float], str]:
    combined = (text or "").strip()
    return (
        parse_income_min(combined),
        parse_income_max(combined),
        parse_occupation(combined),
        parse_max_land(combined),
        parse_category(combined),
    )


def build_structured_schemes(raw_df: DataFrame) -> DataFrame:
    scheme_name_col = find_column(raw_df, ["scheme_name", "scheme", "name", "title"]) or raw_df.columns[0]
    benefit_col     = find_column(raw_df, ["benefits", "benefit", "amount", "support", "assistance"]) or scheme_name_col

    text_columns = [
        col_name
        for col_name in [
            find_column(raw_df, ["eligibility"]),
            find_column(raw_df, ["details", "description"]),
            find_column(raw_df, ["tags", "keywords"]),
            find_column(raw_df, ["schemecategory", "category"]),
        ]
        if col_name is not None
    ]

    if not text_columns:
        text_columns = [scheme_name_col]

    combined_text = F.concat_ws(
        " ",
        *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in text_columns],
    )

    rule_udf = F.udf(extract_rule_fields, extraction_schema())

    base_df = (
        raw_df
        .withColumn("scheme_name",   F.trim(F.col(scheme_name_col).cast("string")))
        .withColumn("benefit",       F.trim(F.col(benefit_col).cast("string")))
        .withColumn("combined_text", combined_text)
        .withColumn("parsed",        rule_udf(F.col("combined_text")))
        .withColumn("min_income",    F.col("parsed.min_income"))
        .withColumn("max_income",    F.col("parsed.max_income"))
        .withColumn("occupation",    F.col("parsed.occupation"))
        .withColumn("max_land",      F.col("parsed.max_land"))
        .withColumn("category",      F.col("parsed.category"))
        .drop("parsed")
    )

    normalized_df = (
        base_df
        .withColumn("min_income", F.coalesce(F.col("min_income"), F.lit(0.0)))
        .withColumn("max_income", F.coalesce(F.col("max_income"), F.lit(100000000.0)))
        .withColumn("occupation", F.coalesce(F.col("occupation"), F.lit("any")))
        .withColumn("max_land",   F.coalesce(F.col("max_land"),   F.lit(999999.0)))
        .withColumn("category",   F.coalesce(F.col("category"),   F.lit("ANY")))
        .withColumn("benefit",    F.coalesce(F.col("benefit"),    F.lit("Benefit details not provided")))
        .withColumn("scheme_id",  F.concat(F.lit("SCH-"), F.upper(F.substring(F.sha2(F.col("scheme_name"), 256), 1, 10))))
        .select(
            "scheme_id",
            "scheme_name",
            F.col("min_income").cast("double"),
            F.col("max_income").cast("double"),
            F.lower(F.col("occupation")).alias("occupation"),
            F.col("max_land").cast("double"),
            F.upper(F.col("category")).alias("category"),
            "benefit",
        )
        .filter(F.col("scheme_name").isNotNull() & (F.col("scheme_name") != ""))
        .dropDuplicates(["scheme_name"])
    )

    # ✅ Baseline rows: capped income + specific occupation so they don't match
    #    implausible profiles (income=99999999, land=1000).
    #    SCH-BASE-003 now has a realistic income cap instead of 100000000.
    baseline_rows = [
        ("SCH-BASE-001", "Small Farmer Income Support",      0.0,    500000.0,  "farmer", 2.0,    "ANY", "Direct assistance up to Rs 6,000/year"),
        ("SCH-BASE-002", "OBC Agri Equipment Subsidy",       0.0,    400000.0,  "farmer", 3.0,    "OBC", "Subsidy for farm equipment purchase"),
        ("SCH-BASE-003", "Universal Rural Livelihood Grant", 0.0,    350000.0,  "any",    5.0,    "ANY", "Livelihood support for rural households"),  # ✅ max_income 350k, max_land 5 acres
    ]
    baseline_schema = (
        "scheme_id string, scheme_name string, min_income double, max_income double, "
        "occupation string, max_land double, category string, benefit string"
    )
    baseline_df = get_spark().createDataFrame(baseline_rows, schema=baseline_schema)

    return normalized_df.unionByName(baseline_df).dropDuplicates(["scheme_name"])


def write_schemes(df: DataFrame) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(SCHEMES_CLEAN_TABLE)
    )


def main() -> None:
    spark_session = get_spark()
    raw_df          = read_schemes_csv(spark_session)
    schemes_clean_df = build_structured_schemes(raw_df)
    write_schemes(schemes_clean_df)

    print(f"Schemes cleaned and written to Delta table: {SCHEMES_CLEAN_TABLE}")
    schemes_clean_df.select(
        "scheme_id", "scheme_name", "min_income", "max_income", "occupation", "max_land", "category"
    ).show(15, truncate=False)


if __name__ == "__main__":
    main()