"""
Adhikar-Aina | 05 Adhikar Certificates

Purpose:
- Generate structured certificate objects for eligible citizen-scheme matches.

Input Delta tables:
- eligibility_results
- silver_citizens

Output Delta table:
- adhikar_certificates
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

RESULTS_TABLE = "eligibility_results"
SILVER_TABLE = "silver_citizens"
CERT_TABLE = "adhikar_certificates"


def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-05-certificate").getOrCreate()


def build_certificates(results_df: DataFrame, citizens_df: DataFrame) -> DataFrame:
    def col_or_default(df: DataFrame, col_name: str, default=None):
        if col_name in df.columns:
            return F.col(col_name)
        return F.lit(default)

    eligible = results_df.filter(F.col("eligibility_status") == F.lit(True))

    eligible_norm = eligible.select(
        col_or_default(eligible, "citizen_id").alias("citizen_id"),
        F.coalesce(col_or_default(eligible, "scheme_name"), F.lit("Unknown Scheme")).alias("scheme_name"),
        col_or_default(eligible, "benefit", "").alias("benefit"),
        col_or_default(eligible, "required_docs", "").alias("required_docs"),
        col_or_default(eligible, "short_code", "").alias("short_code"),
        col_or_default(eligible, "matched_at").alias("matched_at"),
    )

    citizens_norm = citizens_df.select(
        col_or_default(citizens_df, "citizen_id").alias("citizen_id"),
        F.coalesce(col_or_default(citizens_df, "name"), F.lit("Unknown Citizen")).alias("citizen_name"),
        F.coalesce(col_or_default(citizens_df, "district"), F.lit("Unknown District")).alias("district"),
        F.coalesce(col_or_default(citizens_df, "taluka"), F.lit("Unknown Taluka")).alias("taluka"),
        F.coalesce(col_or_default(citizens_df, "village"), F.lit("Unknown Village")).alias("village"),
        F.coalesce(col_or_default(citizens_df, "income_bracket"), F.lit("Unknown")).alias("income_bracket"),
        F.coalesce(col_or_default(citizens_df, "caste_category"), F.lit("Unknown")).alias("caste_category"),
        F.coalesce(col_or_default(citizens_df, "is_tribal"), F.lit(False)).alias("is_tribal"),
    )

    base = (
        eligible_norm.join(citizens_norm, on="citizen_id", how="left")
        .withColumn("timestamp", F.coalesce(F.col("matched_at"), F.current_timestamp()))
        .withColumn("status", F.lit("Eligible"))
    )

    top_candidates = base.withColumn(
        "scheme_row_number",
        F.row_number().over(Window.partitionBy("citizen_id").orderBy(F.col("scheme_name").asc())),
    )

    top_schemes = (
        top_candidates.filter(F.col("scheme_row_number") <= 5)
        .groupBy("citizen_id")
        .agg(
            F.collect_list(
                F.struct(
                    F.col("short_code").alias("scheme_code"),
                    F.col("scheme_name").alias("scheme_name"),
                    F.col("benefit").alias("benefit"),
                    F.lit("As per applicable government scheme guidelines.").alias("legal_basis"),
                    F.lit("Visit nearest facilitation center with required documents.").alias("action_required"),
                )
            ).alias("top_schemes")
        )
    )

    totals = base.groupBy("citizen_id").agg(F.countDistinct("scheme_name").alias("total_schemes_eligible"))

    enriched = base.join(top_schemes, on="citizen_id", how="left").join(totals, on="citizen_id", how="left")

    certificates = (
        enriched.withColumn(
            "certificate_json",
            F.to_json(
                F.struct(
                    F.concat(
                        F.lit("AC-"),
                        F.upper(F.substring(F.col("district"), 1, 3)),
                        F.lit("-"),
                        F.upper(F.substring(F.col("citizen_id"), 1, 4)),
                    ).alias("certificate_id"),
                    F.col("citizen_id").alias("citizen_id"),
                    F.lit("Adhikar-Aina Sovereign AI System").alias("issued_by"),
                    F.date_format(F.col("timestamp"), "yyyy-MM-dd").alias("issued_date"),
                    F.lit(
                        "Generated under Right to Information Act 2005 and relevant scheme guidelines."
                    ).alias("legal_validity"),
                    F.concat_ws(
                        " ",
                        F.lit("Citizen from"),
                        F.col("district"),
                        F.lit("/"),
                        F.col("taluka"),
                        F.lit("/"),
                        F.col("village"),
                        F.lit("with income bracket"),
                        F.col("income_bracket"),
                        F.lit("and caste category"),
                        F.col("caste_category"),
                        F.lit("is eligible for multiple welfare schemes."),
                    ).alias("citizen_summary"),
                    F.coalesce(F.col("top_schemes"), F.array()).alias("top_schemes"),
                    F.lit("तुमच्या हक्काच्या योजनांसाठी नजीकच्या सुविधा केंद्राशी संपर्क करा.").alias("marathi_message"),
                    F.lit("अपने अधिकार वाली योजनाओं के लिए नजदीकी सुविधा केंद्र से संपर्क करें।").alias("hindi_message"),
                    F.col("total_schemes_eligible").alias("total_schemes_eligible"),
                    F.lit(
                        "AI-generated based on available data. Subject to verification by issuing authority."
                    ).alias("disclaimer"),
                )
            ),
        )
        .select(
            "citizen_id",
            "citizen_name",
            "scheme_name",
            "benefit",
            "status",
            "timestamp",
            "certificate_json",
        )
    )

    return certificates


def write_certificates(df: DataFrame) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(CERT_TABLE)
    )


def main() -> None:
    spark_session = get_spark()
    results_df = spark_session.table(RESULTS_TABLE)
    citizens_df = spark_session.table(SILVER_TABLE)

    certificates_df = build_certificates(results_df, citizens_df)
    write_certificates(certificates_df)

    print(f"Certificates written to Delta table: {CERT_TABLE}")
    certificates_df.select("citizen_name", "scheme_name", "status", "timestamp").show(10, truncate=False)


if __name__ == "__main__":
    main()
