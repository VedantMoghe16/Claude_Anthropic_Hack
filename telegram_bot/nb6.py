import asyncio
import json
import subprocess
import sys
import nest_asyncio
from datetime import datetime

# ── 1. SETUP LIBRARIES ──────────────────────────────────────────────────────────
try:
    import telegram
    from dotenv import load_dotenv
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot", "python-dotenv"])
    from dotenv import load_dotenv

from telegram import Bot
import pyspark.sql.functions as F
from pyspark.sql.types import *
from pyspark.sql import Row, SparkSession

# Initialize Spark Session for production .py execution
spark = SparkSession.builder.getOrCreate()
spark.sql("USE CATALOG workspace")
spark.sql("USE default")

# ── 2. CONFIGURATION ────────────────────────────────────────────────────────────
import os
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
bot = Bot(token=TELEGRAM_TOKEN)

# ── 3. DYNAMIC ELIGIBILITY LOGIC ─────────────────────────────────────────────
def run_eligibility_pulse():
    print("="*60)
    print("🚀 SOVEREIGN PULSE: Processing All Active Schemes")
    print("="*60)
    
    # ── SERVERLESS SAFE REFRESH ──
    try:
        spark.catalog.refreshTable("workspace.default.aa_eligibility_results")
        spark.catalog.refreshTable("workspace.default.aa_schemes")
    except Exception as e:
        if "NOT_SUPPORTED_WITH_SERVERLESS" in str(e):
            print("ℹ️ Serverless detected: Using automatic metadata refresh.")
        else:
            print(f"⚠️ Metadata refresh warning: {e}")

    # 1. ENRICH CITIZENS (Normalized tags for bulletproof matching)
    df_citizens = spark.table("workspace.default.aa_citizens_for_llm")
    df_citizens_enriched = df_citizens.withColumn("citizen_tags", F.lower(F.concat_ws(",", 
        F.when(F.col("employment_days") < 100, F.lit("skills & employment")),
        F.when(F.col("housing_status").isin("kutcha", "semi_pucca"), F.lit("housing")),
        F.when(F.col("has_girl_child") == True, F.lit("women & child")),
        F.when(F.col("income_bracket").isin("EWS", "LIG"), F.lit("financial aid")),
        F.when(F.col("has_bpl_card") == True, F.lit("healthcare"))
    )))

    # 2. FETCH SCHEMES (Nothing hardcoded - matching on cleaned tags)
    df_active_schemes = spark.table("workspace.default.aa_schemes") \
                         .filter(F.col("short_code") == "PM-UJJWALA") \
                             .withColumn("scheme_tag", F.lower(F.trim(F.col("benefit_type"))))

    # 3. DYNAMIC MATCHING JOIN
    df_new_matches = (
        df_citizens_enriched.alias("c")
        .join(df_active_schemes.alias("s"), 
            F.col("c.citizen_tags").contains(F.col("s.scheme_tag")), 
            "inner"
        )
        .select(
            F.col("c.citizen_id"), F.col("c.district"), F.col("c.village"), F.col("c.taluka"),
            F.col("c.income_bracket"), F.col("c.caste_category"), F.col("c.is_tribal"),
            F.col("s.scheme_id"), F.col("s.short_code"), F.col("s.scheme_name"), 
            F.col("s.benefit_amount").alias("benefit"), F.col("s.required_docs"),
            F.lit(False).alias("is_notified"), 
            F.current_timestamp().alias("matched_at")
        )
        .dropDuplicates(["citizen_id", "scheme_id"])
    )

    # 4. DATA SYNC
    match_count = df_new_matches.count()
    print(f"🎯 ANALYSIS: Found {match_count} qualifying matches in the registry.")

    df_new_matches.createOrReplaceTempView("_dynamic_staging")
    spark.sql("""
        MERGE INTO workspace.default.aa_eligibility_results AS target
        USING _dynamic_staging AS source
        ON target.citizen_id = source.citizen_id AND target.scheme_id = source.scheme_id
        WHEN NOT MATCHED THEN INSERT *
    """)
    print(f"✅ Eligibility pulse complete. Data synchronized.")

# ── 4. BULK NOTIFICATION DISPATCHER ──────────────────────────────────────────
async def push_alerts():
    print("\n" + "📡" + "─"*58)
    print("  SOVEREIGN DISPATCHER: Scanning for notifications...")
    
    try:
        # 1. Deduplicate Registry (Anti-Spam Shield)
        df_registry = spark.table("workspace.default.aa_user_registry") \
                           .dropDuplicates(["citizen_id", "chat_id"])
        
        df_results  = spark.table("workspace.default.aa_eligibility_results")
        df_silver   = spark.table("workspace.default.aa_citizens_silver")

        # 2. Process first 50 alerts to ensure stability
        queue_df = (df_results.filter(F.col("is_notified") == False)
                 .join(df_registry, "citizen_id")
                 .join(df_silver.select("citizen_id", "full_name"), "citizen_id")) \
                 .limit(50)
        
        queue = queue_df.collect()
        if not queue:
            print("  📭 Queue Empty: No new alerts to push.")
            return

        print(f"  📣 Processing {len(queue)} pending notifications...")
        successfully_sent = [] 

        for row in queue:
            # ✅ Markdown Safety: Escape characters that break Telegram parsing
            clean_name = str(row['full_name']).replace("_", "\\_").replace("*", "\\*")
            clean_scheme = str(row['scheme_name']).replace("_", "\\_").replace("*", "\\*")

            msg = (f"🔔 *NEW RIGHT DETECTED*\n\n"
                   f"Namaste {clean_name},\n"
                   f"You qualify for: *{clean_scheme}*.\n"
                   f"Benefit: {row['benefit']}\n\n"
                   f"Tap 'Generate Certificate' in the bot to claim.")
            
            try:
                await bot.send_message(chat_id=row['chat_id'], text=msg, parse_mode='Markdown')
                successfully_sent.append((row['citizen_id'], row['scheme_id']))
                print(f"  ✅ Pushed: {row['full_name']}")
            except Exception as bot_err:
                # If Markdown fails, retry with plain text
                try:
                    await bot.send_message(chat_id=row['chat_id'], text=msg, parse_mode=None)
                    successfully_sent.append((row['citizen_id'], row['scheme_id']))
                except:
                    print(f"  ⚠️ Failed for {row['citizen_id']}: {bot_err}")

        # 3. Bulk Sync notified status
        if successfully_sent:
            sent_df = spark.createDataFrame(successfully_sent, ["citizen_id", "scheme_id"])
            sent_df.createOrReplaceTempView("_bulk_updates")
            spark.sql("""
                MERGE INTO workspace.default.aa_eligibility_results AS target
                USING _bulk_updates AS source
                ON target.citizen_id = source.citizen_id AND target.scheme_id = source.scheme_id
                WHEN MATCHED THEN UPDATE SET target.is_notified = True
            """)
            print(f"  💾 Database synchronized: {len(successfully_sent)} records updated.")

    except Exception as e:
        print(f"  ❌ Dispatcher Error: {e}")

# ── 5. ENTRY POINT ────────────────────────────────────────────────────────────
async def main():
    run_eligibility_pulse()
    await push_alerts()
    print("\n" + "="*60 + "\n✅ ADHIKAR-AINA AUTOMATION CYCLE COMPLETE\n" + "="*60)

if __name__ == "__main__":
    print("🚀 SOVEREIGN ENGINE: Initializing Pulse...")
    try:
        asyncio.run(main())
    except RuntimeError:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except Exception as e:
        print(f"❌ Entry point error: {e}")