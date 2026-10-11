
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus

password = quote_plus(input("Enter your MySQL password: "))

engine = create_engine(
    f"mysql+mysqlconnector://root:{password}@localhost/apparel_production"
)

query = """
SELECT
    option_name,
    additional_workers,
    daily_wage,
    working_days,
    estimated_cost
FROM improvement_options
"""

df = pd.read_sql(query, engine)

df["recalculated_cost"] = (
    df["additional_workers"]
    * df["daily_wage"]
    * df["working_days"]
)

print("\nWORKFORCE COST ESTIMATE")
print(df.to_string(index=False))

print(
    "\nEstimated total hiring cost: ₹"
    + f"{df['recalculated_cost'].sum():,.2f}"
)

engine.dispose()
