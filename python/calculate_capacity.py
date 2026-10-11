
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Connect to MySQL
password = quote_plus(input("Enter your MySQL password: "))

engine = create_engine(
    f"mysql+mysqlconnector://root:{password}@localhost/apparel_production"
)

query = """
SELECT
    pc.process_name,
    pc.capacity_per_day AS recorded_capacity,
    pc.capacity_basis,
    m.workers_count,
    m.hours_per_worker_per_day,
    pp.minutes_per_unit,
    pp.efficiency_pct
FROM process_capacity pc
JOIN manpower m
    ON pc.process_name = m.process_name
LEFT JOIN process_parameters pp
    ON pc.process_name = pp.process_name
ORDER BY pc.process_id
"""

df = pd.read_sql(query, engine)
engine.dispose()

# Calculate capacity only when all required parameters exist
df["calculated_capacity"] = pd.NA

valid = (
    df["minutes_per_unit"].notna()
    & df["efficiency_pct"].notna()
    & (df["minutes_per_unit"] > 0)
    & (df["workers_count"] > 0)
)

df.loc[valid, "calculated_capacity"] = (
    df.loc[valid, "workers_count"]
    * df.loc[valid, "hours_per_worker_per_day"]
    * 60
    * df.loc[valid, "efficiency_pct"] / 100
    / df.loc[valid, "minutes_per_unit"]
)

df["capacity_status"] = valid.map({
    True: "Calculated from parameters",
    False: "Assumption - needs validation"
})

print("\nPROCESS CAPACITY VALIDATION")
print(
    df[[
        "process_name",
        "workers_count",
        "recorded_capacity",
        "calculated_capacity",
        "capacity_status"
    ]].to_string(index=False)
)

print("\nSUMMARY")
print(f"Processes with calculated capacity: {valid.sum()}")
print(f"Processes needing validation: {(~valid).sum()}")
