"""
Adhikar-Aina | 06 Automation Trigger

Purpose:
- Simulate proactive pulse when new schemes are added.
- Re-run matching for newly added schemes and report newly eligible citizens.

Input Delta tables:
- silver_citizens
- schemes_clean
- eligibility_results

Output Delta tables:
- eligibility_results (updated)
- schemes_snapshot (state table for change detection)
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# ✅ __file__ is undefined in Databricks notebooks.
_TELEGRAM_MODULE_SEARCH_PATHS = [
    "/Workspace/Users/anant.asati.moodi@gmail.com/bharatbricks_hackathon",
    "/Workspace/Repos/anant.asati.moodi@gmail.com/bharatbricks_hackathon",
]

def _ensure_telegram_on_path() -> None:
    for path in _TELEGRAM_MODULE_SEARCH_PATHS:
        if os.path.isdir(path) and path not in sys.path:
            sys.path.append(path)

_ensure_telegram_on_path()

try:
    from telegram_integration import format_new_benefit_message, send_telegram_message_sync
    _TELEGRAM_AVAILABLE = True
except ModuleNotFoundError:
    _TELEGRAM_AVAILABLE = False
    print("[06] telegram_integration not found — notification steps will be skipped.")

    def format_new_benefit_message(scheme_name: str, benefit: str, action: str) -> str:  # type: ignore[misc]
        return f"New scheme available: {scheme_name}. Benefit: {benefit}. Action: {action}"

    def send_telegram_message_sync(chat_id: str, text: str) -> None:  # type: ignore[misc]
        raise RuntimeError("telegram_integration not available")


SILVER_TABLE           = "silver_citizens"
SCHEMES_TABLE          = "schemes_clean"
RESULTS_TABLE          = "eligibility_results"
SNAPSHOT_TABLE         = "schemes_snapshot"
TELEGRAM_MAPPING_TABLE = "workspace.default.telegram_user_mapping"


def get_spark() -> SparkSession:
    try:
        return spark  # type: ignore[name-defined]
    except NameError:
        return SparkSession.builder.appName("adhikar-aina-06-trigger").getOrCreate()


def _is_empty(df: DataFrame) -> bool:
    """
    ✅ Replaces df.rdd.isEmpty() which is banned on Databricks Serverless.
    Uses DataFrame.limit(1).count() instead — fully supported.
    """
    return df.limit(1).count() == 0


def _match_with_subset(citizens_df: DataFrame, scheme_subset_df: DataFrame) -> DataFrame:
    citizens = citizens_df.select(
        "citizen_id",
        F.col("occupation_category").alias("occupation_norm"),                               # ✅ silver column name
        F.coalesce(F.col("annual_income").cast("double"), F.lit(0.0)).alias("income_norm"),  # ✅ silver column name
        F.coalesce(F.col("land_acres").cast("double"),    F.lit(0.0)).alias("land_norm"),
        F.upper(F.trim(F.coalesce(F.col("category"), F.lit("GEN")))).alias("category_norm"),
    )

    schemes = scheme_subset_df.select(
        "scheme_name",
        "benefit",
        F.coalesce(F.col("min_income").cast("double"), F.lit(0.0))        .alias("min_income_norm"),
        F.coalesce(F.col("max_income").cast("double"), F.lit(100000000.0)).alias("max_income_norm"),
        F.coalesce(F.col("max_land").cast("double"),   F.lit(999999.0))   .alias("max_land_norm"),
        F.lower(F.trim(F.coalesce(F.col("occupation"), F.lit("any"))))    .alias("occupation_req"),
        F.upper(F.trim(F.coalesce(F.col("category"),  F.lit("ANY"))))     .alias("category_req"),
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


def ensure_snapshot_exists(spark_session: SparkSession) -> None:
    if not spark_session.catalog.tableExists(SNAPSHOT_TABLE):
        (
            spark_session.table(SCHEMES_TABLE)
            .select("scheme_id")
            .dropDuplicates()
            .write.format("delta")
            .mode("overwrite")
            .saveAsTable(SNAPSHOT_TABLE)
        )


def append_new_scheme(spark_session: SparkSession) -> str:
    # ✅ datetime.utcnow() deprecated — use datetime.now(timezone.utc) instead
    new_scheme_id = f"SCH-NEW-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    rows = [
        (
            new_scheme_id,
            "Proactive Rural Farmer Booster",
            0.0,
            380000.0,
            "farmer",
            2.5,
            "OBC",
            "Top-up support for small and marginal farmers",
        )
    ]
    schema = (
        "scheme_id string, scheme_name string, min_income double, max_income double, "
        "occupation string, max_land double, category string, benefit string"
    )
    (
        spark_session.createDataFrame(rows, schema=schema)
        .write.format("delta")
        .mode("append")
        .saveAsTable(SCHEMES_TABLE)
    )
    return new_scheme_id


def detect_new_schemes(spark_session: SparkSession) -> DataFrame:
    current_schemes = spark_session.table(SCHEMES_TABLE).select(
        "scheme_id", "scheme_name", "min_income", "max_income",
        "occupation", "max_land", "category", "benefit",
    )
    snapshot = spark_session.table(SNAPSHOT_TABLE).select("scheme_id").dropDuplicates()
    return current_schemes.join(snapshot, on="scheme_id", how="left_anti")


def update_snapshot(spark_session: SparkSession) -> None:
    (
        spark_session.table(SCHEMES_TABLE)
        .select("scheme_id")
        .dropDuplicates()
        .write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(SNAPSHOT_TABLE)
    )


def _table_has_column(spark_session: SparkSession, table_name: str, column_name: str) -> bool:
    return column_name in spark_session.table(table_name).columns


def notify_newly_eligible(spark_session: SparkSession, newly_eligible_df: DataFrame) -> int:
    # ✅ _is_empty() replaces .rdd.isEmpty() — banned on Serverless
    if _is_empty(newly_eligible_df):
        return 0

    if not _TELEGRAM_AVAILABLE:
        print("[06] Telegram module unavailable — skipping notifications.")
        return 0

    if not spark_session.catalog.tableExists(TELEGRAM_MAPPING_TABLE):
        print("[TEST-4] Telegram mapping table not found. Skipping notifications.")
        return 0

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("[TEST-4] TELEGRAM_BOT_TOKEN missing. Skipping notifications.")
        return 0

    candidates = newly_eligible_df.select("citizen_id", "scheme_name", "benefit").dropDuplicates()

    if _table_has_column(spark_session, RESULTS_TABLE, "is_notified"):
        already_notified = (
            spark_session.table(RESULTS_TABLE)
            .filter(F.col("eligibility_status") == F.lit(True))
            .filter(F.col("is_notified") == F.lit(True))
            .select("citizen_id", "scheme_name")
            .dropDuplicates()
        )
        candidates = candidates.join(already_notified, on=["citizen_id", "scheme_name"], how="left_anti")

    mapped = candidates.join(
        spark_session.table(TELEGRAM_MAPPING_TABLE).select("citizen_id", "telegram_chat_id"),
        on="citizen_id",
        how="inner",
    )

    rows       = mapped.collect()
    sent       = 0
    sent_pairs = []

    for row in rows:
        message = format_new_benefit_message(
            scheme_name=row["scheme_name"],
            benefit=row["benefit"],
            action="Visit nearest facilitation center with required documents.",
        )
        try:
            send_telegram_message_sync(chat_id=row["telegram_chat_id"], text=message)
            sent += 1
            sent_pairs.append((row["citizen_id"], row["scheme_name"]))
        except Exception as exc:
            print(f"[TEST-4] Notification failed for citizen_id={row['citizen_id']}: {exc}")

    if sent_pairs and _table_has_column(spark_session, RESULTS_TABLE, "is_notified"):
        sent_df = spark_session.createDataFrame(sent_pairs, schema="citizen_id string, scheme_name string")
        sent_df.createOrReplaceTempView("_sent_notifications")
        spark_session.sql(
            f"""
            MERGE INTO {RESULTS_TABLE} AS target
            USING _sent_notifications AS source
            ON  target.citizen_id         = source.citizen_id
            AND target.scheme_name        = source.scheme_name
            AND target.eligibility_status = true
            WHEN MATCHED THEN UPDATE SET is_notified = true
            """
        )

    return sent


def run_test_4(spark_session: SparkSession) -> None:
    ensure_snapshot_exists(spark_session)
    inserted_scheme_id = append_new_scheme(spark_session)

    new_schemes_df   = detect_new_schemes(spark_session)
    new_scheme_count = new_schemes_df.count()
    assert new_scheme_count >= 1, "Expected at least one new scheme after append"

    citizens_df    = spark_session.table(SILVER_TABLE)
    new_results_df = _match_with_subset(citizens_df, new_schemes_df)

    if _table_has_column(spark_session, RESULTS_TABLE, "is_notified"):
        new_results_df = new_results_df.withColumn("is_notified", F.lit(False))

    new_results_df.write.format("delta").mode("append").saveAsTable(RESULTS_TABLE)

    newly_eligible_df = new_results_df.filter(F.col("eligibility_status") == F.lit(True))
    newly_eligible    = newly_eligible_df.count()
    assert newly_eligible >= 1, "Expected newly eligible citizens after adding new scheme"

    notifications_sent = notify_newly_eligible(spark_session, newly_eligible_df)
    update_snapshot(spark_session)

    print(f"[TEST-4] New scheme trigger passed. inserted_scheme_id={inserted_scheme_id}")
    print(f"[TEST-4] new_scheme_count={new_scheme_count}, newly_eligible={newly_eligible}")
    print(f"[TEST-4] notifications_sent={notifications_sent}")


def main() -> None:
    spark_session = get_spark()
    run_test_4(spark_session)


if __name__ == "__main__":
    main()