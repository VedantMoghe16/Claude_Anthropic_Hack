# Databricks notebook source
exec(open("nb6.py").read())

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM workspace.default.aa_citizens_silver 
# MAGIC WHERE full_name = 'Rahul Kulkarni'

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Find if one Telegram user is linked to multiple Rahuls
# MAGIC SELECT chat_id, COUNT(DISTINCT citizen_id) as identity_count
# MAGIC FROM workspace.default.aa_user_registry
# MAGIC GROUP BY chat_id
# MAGIC HAVING COUNT(DISTINCT citizen_id) > 1;
# MAGIC
# MAGIC -- To fix: Delete the duplicates and keep only the latest registration
# MAGIC -- (Or just wipe it and re-register once in the bot)
# MAGIC TRUNCATE TABLE workspace.default.aa_user_registry;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 1. Insert the Dynamic Ujjwala Scheme
# MAGIC INSERT INTO workspace.default.aa_schemes (
# MAGIC     scheme_id, 
# MAGIC     scheme_name, 
# MAGIC     short_code, 
# MAGIC     benefit_type, 
# MAGIC     benefit_amount, 
# MAGIC     eligibility_sql, 
# MAGIC     is_active, 
# MAGIC     created_at
# MAGIC ) VALUES (
# MAGIC     'SCH-UJJWALA-2026', 
# MAGIC     'Pradhan Mantri Ujjwala 2.0 (LPG Subsidy)', 
# MAGIC     'PM-UJJWALA', 
# MAGIC     'Housing', -- Matches 'kutcha' or 'semi_pucca' citizens
# MAGIC     'Free LPG Connection + Rs. 1,600 Cash Grant', 
# MAGIC     'housing_status IN (kutcha, semi_pucca) AND income_bracket IN (EWS, LIG)', 
# MAGIC     true, 
# MAGIC     current_timestamp()
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC     
# MAGIC -- 2. Find the Rahul Kulkarni who qualifies for 'Housing' benefits
# MAGIC SELECT 
# MAGIC     llm.citizen_id, 
# MAGIC     silver.full_name, 
# MAGIC     llm.district, 
# MAGIC     llm.village, 
# MAGIC     llm.housing_status, 
# MAGIC     llm.income_bracket
# MAGIC FROM workspace.default.aa_citizens_for_llm llm
# MAGIC JOIN workspace.default.aa_citizens_silver silver ON llm.citizen_id = silver.citizen_id
# MAGIC WHERE silver.full_name = 'Rahul Kulkarni' 
# MAGIC   AND llm.housing_status IN ('kutcha', 'semi_pucca')
# MAGIC LIMIT 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC DELETE FROM workspace.default.aa_eligibility_results WHERE citizen_id = '22576de2-f458-4350-9400-1622c78ad22b';

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT scheme_name, count(*) as duplicate_check
# MAGIC FROM workspace.default.aa_eligibility_results
# MAGIC WHERE citizen_id = '22576de2-f458-4350-9400-1622c78ad22b'
# MAGIC GROUP BY scheme_name
# MAGIC HAVING count(*) > 1;

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT INTO workspace.default.aa_schemes (
# MAGIC     scheme_id, 
# MAGIC     scheme_name, 
# MAGIC     short_code, 
# MAGIC     benefit_type, 
# MAGIC     benefit_amount, 
# MAGIC     eligibility_sql, 
# MAGIC     is_active, 
# MAGIC     created_at
# MAGIC ) VALUES (
# MAGIC     'SCH-LEK-LADKI-2026', 
# MAGIC     'Lek Ladki Yojana (Girl Child Empowerment)', 
# MAGIC     'LEK-LADKI', 
# MAGIC     'Women & Child', -- This matches the 'has_girl_child' tag in your code
# MAGIC     'Total ₹1,01,000 (₹5,000 at birth, ₹6,000 in Class 1, ₹75,000 at age 18)', 
# MAGIC     'has_girl_child = true AND income_bracket IN (EWS, LIG)', 
# MAGIC     true, 
# MAGIC     current_timestamp()
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT full_name, has_girl_child, income_bracket 
# MAGIC FROM workspace.default.aa_citizens_for_llm 
# MAGIC WHERE citizen_id = '22576de2-f458-4350-9400-1622c78ad22b';