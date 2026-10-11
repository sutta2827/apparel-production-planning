
import pulp

# ==========================================
# 1. PRODUCTION TARGET AND ASSUMPTIONS
# ==========================================

order_quantity = 30000
working_days = 52
required_output = order_quantity / working_days

daily_wage = 800  # Assumed wage per additional worker per day

# Current daily capacity and workforce.
# Capacities for four processes are assumptions.
processes = {
    "Cutting": {"capacity": 500, "workers": 4},
    "Embroidery": {"capacity": 500, "workers": 3},
    "Finishing": {"capacity": 500, "workers": 5},
    "Packing": {"capacity": 500, "workers": 3},
    "Sewing": {"capacity": 630, "workers": 35},
}

# ==========================================
# 2. CREATE OPTIMIZATION MODEL
# ==========================================

model = pulp.LpProblem(
    name="Workforce_Optimization",
    sense=pulp.LpMinimize
)

# Decision variable: additional whole workers per process
extra_workers = {
    process: pulp.LpVariable(
        name=f"extra_workers_{process}",
        lowBound=0,
        cat="Integer"
    )
    for process in processes
}

# ==========================================
# 3. OBJECTIVE: MINIMIZE ADDITIONAL WAGE COST
# ==========================================

model += daily_wage * pulp.lpSum(
    extra_workers[process]
    for process in processes
), "Total_Additional_Daily_Wage_Cost"

# ==========================================
# 4. CAPACITY CONSTRAINTS
# ==========================================

for process, data in processes.items():
    capacity_per_worker = data["capacity"] / data["workers"]

    model += (
        data["capacity"]
        + capacity_per_worker * extra_workers[process]
        >= required_output,
        f"Capacity_Requirement_{process}"
    )

# ==========================================
# 5. SOLVE MODEL
# ==========================================

solver = pulp.PULP_CBC_CMD(msg=False)
model.solve(solver)

status = pulp.LpStatus[model.status]

print("=" * 55)
print("APPAREL PRODUCTION WORKFORCE OPTIMIZATION")
print("=" * 55)

print(f"Solver status: {status}")
print(f"Order quantity: {order_quantity:,} jackets")
print(f"Assumed working days: {working_days}")
print(f"Required daily output: {required_output:.2f} jackets")

# Only read decision-variable values if a solution exists
if status != "Optimal":
    print("\nNo optimal solution was found.")
    print("Check the solver installation and model constraints.")

else:
    total_extra_workers = 0

    print("\nWORKFORCE AND CAPACITY PLAN")
    print("-" * 75)
    print(
        f"{'Process':<15}"
        f"{'Current':>10}"
        f"{'Extra':>10}"
        f"{'Final staff':>13}"
        f"{'Final cap/day':>15}"
    )
    print("-" * 75)

    for process, data in processes.items():
        extra = pulp.value(extra_workers[process])

        # Protect against missing solver values
        if extra is None:
            raise RuntimeError(
                f"No solution value returned for {process}."
            )

        extra = int(round(extra))
        total_extra_workers += extra

        capacity_per_worker = (
            data["capacity"] / data["workers"]
        )

        final_capacity = (
            data["capacity"]
            + capacity_per_worker * extra
        )

        final_staff = data["workers"] + extra

        print(
            f"{process:<15}"
            f"{data['workers']:>10}"
            f"{extra:>10}"
            f"{final_staff:>13}"
            f"{final_capacity:>15.2f}"
        )

        # Verify each capacity constraint
        if final_capacity + 1e-6 < required_output:
            raise RuntimeError(
                f"Capacity constraint failed for {process}."
            )

    total_daily_cost = total_extra_workers * daily_wage
    total_period_cost = total_daily_cost * working_days

    print("-" * 75)
    print(f"Additional workers: {total_extra_workers}")
    print(f"Additional daily wage cost: Rs. {total_daily_cost:,.2f}")
    print(
        f"Additional wage cost for {working_days} days: "
        f"Rs. {total_period_cost:,.2f}"
    )
    print("\nValidation: all modeled process capacities meet the target.")

print("=" * 55)
