# Apparel Production Planning & Optimization System

A data-driven production planning system designed to improve manufacturing capacity utilization, workforce allocation, and material procurement for an apparel manufacturing unit.

## Project Overview

This project integrates SQL, Python, mathematical optimization, and Power BI to support production planning and operational decision-making.

The system analyzes production orders, bills of materials (BOM), inventory levels, and process capacities to identify production bottlenecks and recommend workforce allocation.

## Tech Stack

- **SQL / MySQL:** Production data storage and querying
- **Python:** Data processing, capacity calculations, and automation
- **PuLP:** Workforce optimization using linear/integer programming
- **Power BI:** Operational dashboards and KPI visualization
- **Excel / CSV:** Data exchange and reporting

## Key Features

- Production order and delivery planning
- Daily production target calculations
- Process-wise capacity and bottleneck analysis
- Workforce allocation optimization
- Material requirement and procurement gap analysis
- Wastage-adjusted material planning
- Production KPI reporting through Power BI

## Production Workflow

1. Retrieve production data from MySQL.
2. Calculate production targets and process capacities.
3. Estimate material requirements, including wastage.
4. Use optimization to evaluate workforce allocation.
5. Export planning data for Power BI dashboards.
6. Monitor production KPIs and capacity constraints.

## Repository Structure

```text
apparel-production-planning/
├── python/
│   ├── main.py
│   ├── calculate_capacity.py
│   ├── export_dashboard_data.py
│   ├── optimize_from_database.py
│   └── optimize_workforce.py
├── dashboard_data/
├── .gitignore
└── README.md
```

## Important Note

Some production parameters, including process times, efficiency, and material wastage, are assumptions that require validation against actual manufacturing data. Optimization recommendations depend on the accuracy of these inputs.

## Future Improvements

- Integrate validated factory production data
- Add automated production-plan updates
- Incorporate machine availability and shift constraints
- Improve dashboard monitoring and scenario analysis