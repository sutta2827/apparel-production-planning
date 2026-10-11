
from pathlib import Path
from urllib.parse import quote_plus
from math import ceil

import pandas as pd
from sqlalchemy import create_engine

# Connect to MySQL without hardcoding the password
password = quote_plus(input("Enter your MySQL password: "))

engine = create_engine(
    f"mysql+mysqlconnector://root:{password}@localhost/apparel_production"
)

output_dir = Path(__file__).resolve().parent.parent / "dashboard_data"
output_dir.mkdir(exist_ok=True)

try:
    # 1. ORDER OVERVIEW
    orders = pd.read_sql("""
        SELECT
            o.order_id,
            o.sku,
            o.buyer,
            o.order_quantity,
            o.order_date,
            o.delivery_date,
            o.status,
            op.available_working_days,
            op.required_daily_output
        FROM orders o
        LEFT JOIN order_planning op
            ON o.order_id = op.order_id
    """, engine)

    orders.to_csv(
        output_dir / "order_overview.csv",
        index=False
    )

    # 2. MATERIAL REQUIREMENTS AND INVENTORY SHORTAGES
    materials = pd.read_sql("""
        SELECT
            o.order_id,
            o.order_quantity,
            m.material_id,
            m.material_name,
            b.qty_per_unit,
            b.unit,
            COALESCE(i.stock_qty, 0) AS stock_qty
        FROM orders o
        JOIN bom b ON o.sku = b.sku
        JOIN materials m ON b.material_id = m.material_id
        LEFT JOIN inventory i ON m.material_id = i.material_id
    """, engine)

    # Provisional wastage assumptions.
    # Validate these rates with actual factory data before operational use.
    wastage_rates = {
        "Fleece / Polycotton": 0.08,
        "PU / Faux Leather": 0.07,
        "Elasticized Ribbing": 0.06,
        "Polyester Satin": 0.08,
        "Snap Button": 0.02,
        "Heavy-duty Polyester Thread": 0.05,
        "Chenille / Felt Patch": 0.03,
        "Fusible Interfacing": 0.05,
        "Shoulder Pad": 0.02,
    }

    materials["wastage_pct"] = (
        materials["material_name"]
        .map(wastage_rates)
    )

    # Warn if any database material name is missing from the dictionary
    unmatched_materials = materials.loc[
        materials["wastage_pct"].isna(),
        "material_name"
    ].drop_duplicates().tolist()

    if unmatched_materials:
        print(
            "\nWARNING: No specific wastage rate found for:",
            unmatched_materials
        )
        print("Using the provisional default rate of 5% for these materials.")
        materials["wastage_pct"] = (
            materials["wastage_pct"].fillna(0.05)
        )

    # Base consumption before wastage
    materials["base_required_qty"] = (
        materials["order_quantity"]
        * materials["qty_per_unit"]
    )

    # Total material requirement including wastage
    materials["required_qty"] = (
        materials["base_required_qty"]
        * (1 + materials["wastage_pct"])
    )

    # Additional quantity that must be procured
    materials["procurement_gap"] = (
        materials["required_qty"] - materials["stock_qty"]
    ).clip(lower=0)

    # Stock remaining after planned production
    materials["surplus_stock"] = (
        materials["stock_qty"] - materials["required_qty"]
    ).clip(lower=0)

    materials.to_csv(
        output_dir / "material_planning.csv",
        index=False
    )

    # 3. PRODUCTION KPIs
    production = pd.read_sql("""
        SELECT
            SUM(planned_qty) AS planned_qty,
            SUM(good_qty) AS good_qty,
            SUM(rejected_qty) AS rejected_qty,
            SUM(rework_qty) AS rework_qty,
            SUM(downtime_hours) AS downtime_hours,
            SUM(production_hours) AS production_hours
        FROM production_history
    """, engine)

    kpi = production.iloc[0]

    total_inspected = (
        (kpi["good_qty"] or 0)
        + (kpi["rejected_qty"] or 0)
    )

    production["plan_attainment_pct"] = (
        kpi["good_qty"] / kpi["planned_qty"] * 100
        if pd.notna(kpi["planned_qty"]) and kpi["planned_qty"] else 0
    )

    production["rejection_rate_pct"] = (
        kpi["rejected_qty"] / total_inspected * 100
        if total_inspected else 0
    )

    production["rework_rate_pct"] = (
        kpi["rework_qty"] / kpi["good_qty"] * 100
        if pd.notna(kpi["good_qty"]) and kpi["good_qty"] else 0
    )

    production.to_csv(
        output_dir / "production_kpis.csv",
        index=False
    )

    # 4. PROCESS CAPACITY AND WORKFORCE PLANNING
    capacity = pd.read_sql("""
        SELECT
            pc.process_name,
            pc.capacity_per_day AS recorded_capacity,
            pc.capacity_basis,
            m.workers_count,
            m.hours_per_worker_per_day,
            pp.minutes_per_unit,
            pp.efficiency_pct,
            op.required_daily_output
        FROM process_capacity pc
        JOIN manpower m
            ON pc.process_name = m.process_name
        LEFT JOIN process_parameters pp
            ON pc.process_name = pp.process_name
        CROSS JOIN (
            SELECT MAX(required_daily_output) AS required_daily_output
            FROM order_planning
        ) op
        ORDER BY pc.process_id
    """, engine)

    # Check for missing or invalid inputs before calculating capacity
    required_parameters = [
        "hours_per_worker_per_day",
        "minutes_per_unit",
        "efficiency_pct",
        "workers_count",
        "required_daily_output",
    ]

    if capacity[required_parameters].isna().any().any():
        missing = capacity.loc[
            capacity[required_parameters].isna().any(axis=1),
            ["process_name"] + required_parameters
        ]
        raise ValueError(
            "Missing workforce or capacity parameters:\n"
            f"{missing.to_string(index=False)}"
        )

    if (capacity["minutes_per_unit"] <= 0).any():
        raise ValueError("minutes_per_unit must be greater than zero.")

    # Estimated output per worker per day
    capacity["capacity_per_worker"] = (
        capacity["hours_per_worker_per_day"]
        * 60
        * capacity["efficiency_pct"] / 100
        / capacity["minutes_per_unit"]
    )

    # Current estimated capacity
    capacity["calculated_capacity"] = (
        capacity["workers_count"]
        * capacity["capacity_per_worker"]
    )

    # Minimum workforce required to meet the target in each process
    capacity["recommended_workers"] = capacity.apply(
        lambda row: ceil(
            row["required_daily_output"]
            / row["capacity_per_worker"]
        ),
        axis=1
    )

    # Never recommend fewer workers than currently employed
    capacity["recommended_workers"] = capacity.apply(
        lambda row: max(
            int(row["workers_count"]),
            int(row["recommended_workers"])
        ),
        axis=1
    )

    # Additional workers needed
    capacity["additional_workers"] = (
        capacity["recommended_workers"]
        - capacity["workers_count"]
    )

    # Projected daily capacity after staffing changes
    capacity["projected_capacity"] = (
        capacity["recommended_workers"]
        * capacity["capacity_per_worker"]
    )

    # Provisional wage assumption: ₹800 per additional worker per day
    daily_wage = 800

    capacity["estimated_daily_hiring_cost"] = (
        capacity["additional_workers"] * daily_wage
    )

    # Flag provisional versus supplied parameters
    capacity["data_quality"] = capacity["process_name"].map({
        "Sewing": "Supplied parameters; verify against factory data",
        "Cutting": "Provisional estimates",
        "Embroidery": "Provisional estimates",
        "Finishing": "Provisional estimates",
        "Packing": "Provisional estimates",
    }).fillna("Verify process parameters")

    capacity.to_csv(
        output_dir / "capacity_workforce.csv",
        index=False
    )

    # 5. EXPORT SUMMARY
    print("\nDASHBOARD DATA EXPORTED SUCCESSFULLY")
    print(f"Folder: {output_dir}")

    print("\nFiles created:")
    for file in sorted(output_dir.glob("*.csv")):
        print(f"- {file.name}")

    print("\nMaterial wastage assumptions:")
    print(
        materials[["material_name", "wastage_pct"]]
        .drop_duplicates()
        .to_string(index=False)
    )

    print("\nWorkforce recommendations:")
    print(
        capacity[
            [
                "process_name",
                "workers_count",
                "additional_workers",
                "recommended_workers",
                "projected_capacity",
            ]
        ].to_string(index=False)
    )

finally:
    engine.dispose()
