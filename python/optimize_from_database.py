
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import pulp

# Connect to MySQL
password = quote_plus(input("Enter your MySQL password: "))

engine = create_engine(
    f"mysql+mysqlconnector://root:{password}@localhost/apparel_production"
)

# Load workforce and process parameters
query = """
SELECT
    m.process_name,
    m.workers_count,
    m.hours_per_worker_per_day,
    pp.minutes_per_unit,
    pp.efficiency_pct
FROM manpower m
JOIN process_parameters pp
    ON m.process_name = pp.process_name
"""

df = pd.read_sql(query, engine)

# Load order target
order_query = """
SELECT required_daily_output
FROM order_planning
LIMIT 1
"""

target = float(
    pd.read_sql(order_query, engine)["required_daily_output"].iloc[0]
)

engine.dispose()

# Calculate capacity per worker per day
df["capacity_per_worker"] = (
    df["hours_per_worker_per_day"]
    * 60
    * df["efficiency_pct"] / 100
    / df["minutes_per_unit"]
)

# Integer decision variables: additional workers
model = pulp.LpProblem(
    "Workforce_Optimization",
    pulp.LpMinimize
)

extra_workers = {
    row.process_name: pulp.LpVariable(
        f"extra_{row.process_name}",
        lowBound=0,
        cat="Integer"
    )
    for row in df.itertuples()
}

# Minimize additional workers
model += pulp.lpSum(extra_workers.values())

# Each process must meet the daily target
for row in df.itertuples():
    model += (
        (row.workers_count + extra_workers[row.process_name])
        * row.capacity_per_worker
        >= target
    )

model.solve(pulp.PULP_CBC_CMD(msg=False))

print("\nWORKFORCE OPTIMIZATION RESULTS")
print(f"Solver status: {pulp.LpStatus[model.status]}")
print(f"Daily production target: {target:.2f} jackets")

total_extra = 0

for row in df.itertuples():
    extra = int(pulp.value(extra_workers[row.process_name]))
    total_extra += extra

    new_workers = row.workers_count + extra
    new_capacity = new_workers * row.capacity_per_worker

    print(f"\nProcess: {row.process_name}")
    print(f"Current workers: {row.workers_count}")
    print(f"Additional workers: {extra}")
    print(f"Recommended workforce: {new_workers}")
    print(f"Estimated capacity/day: {new_capacity:.2f}")

daily_wage = 800
working_days = 52

print("\nCOST SUMMARY")
print(f"Additional workers: {total_extra}")
print(f"Estimated daily cost: ₹{total_extra * daily_wage:,.2f}")
print(
    f"Estimated cost over {working_days} days: "
    f"₹{total_extra * daily_wage * working_days:,.2f}"
)
