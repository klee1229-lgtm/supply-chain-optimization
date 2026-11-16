<img src="assets/header.svg" width="100%" alt="Retail Network Optimization"/>

A retailer can open up to 10 warehouses and 40 stores. Demand at each store drops as price goes up, neighboring stores cannot differ in price by more than $5, every open warehouse pays rent, trucks carry 500 units, and drivers work 8-hour shifts. Which warehouses do you open, which stores do you serve, what do you charge, and how do the trucks run?

**Result: $55,210.64 a day.** 4 warehouses open, all 40 stores served, 22 routes.

| Benchmark | Daily profit | This solution vs. it |
|---|---|---|
| Part 1 target set by the course | $10,000 | 5.5x |
| Our Part 1 solution, built by hand without optimization (16 stores, 3 warehouses, 6 routes) | $15,176 | 3.6x |
| Retailer's baseline stated in the Part 2 brief | $48,000 | +15% (target was +10%) |

**Course:** BUDT 732 Decision Analytics, University of Maryland Smith School, Fall 2025. Team of 4. Solved with AMPL and Gurobi.

---

## Approach

One model that decides prices, locations, and routes at the same time is too big to solve at this size, so we split it into three steps, each feeding the next.

**1. Price.** Setting a different price at each store runs into the $5 neighbor rule and makes the problem nonlinear. One price for every store satisfies the rule on its own. $38 was the best single price on the demand curves from Part 1. With price fixed, each store's demand and daily profit become plain numbers.

**2. Which warehouses and stores (MILP).** Yes/no variables for each store, each warehouse, and each store-to-warehouse pairing. Rules: every open store gets exactly one warehouse, only open warehouses can serve, warehouses cannot ship more than their capacity, and a pairing is off the table if a round trip plus unloading takes more than 8 hours. Goal: store profit minus warehouse rent. Gurobi solves it in 137 branch-and-bound nodes.

```
maximize  sum(store_profit[i] * x[i]) - sum(wh_rent[w] * y[w])
s.t.      sum_w z[w,i] = x[i]            each open store gets one warehouse
          z[w,i] <= y[w]                 only from open warehouses
          z[w,i] <= feasible[w,i]        round trip fits in a shift
          sum_i demand[i] * z[w,i] <= cap[w]
```

**3. Routes (greedy).** For each warehouse, start a route at the nearest unserved store, then keep adding the nearest store that still fits in the truck and keeps the route under 480 minutes, counting 30 minutes of unloading per stop. Each route costs $200 plus $0.10 a minute. Because step 2 only paired stores that fit in a single round trip, routing never gets stuck.

| Stage | Value |
|---|---|
| MILP profit (store margin minus rent) | $60,498.04 |
| Routing cost (22 routes) | $5,287.40 |
| **Daily profit** | **$55,210.64** |

## Solution

| Warehouse | Stores | Routes | Daily volume |
|---|---|---|---|
| 3 | 9 | 4 | 1,159 units |
| 4 | 11 | 5 | 1,298 |
| 6 | 10 | 6 | 1,214 |
| 7 | 10 | 7 | 1,329 |

Full assignments are in `outputs/routes.txt`, one line per route: warehouse, then `store:quantity` for each stop.

## My role

I built several of the models we tried on the way here, including a per-store pricing model and an early warehouse-assignment model in AMPL. The final version uses the integer-programming formulation from class for the warehouse and store decisions and a greedy heuristic for routing.

## Repository

```
optimize.py                 the full pipeline: demand, MILP, routing, outputs
model/part2.mod             AMPL model
data/                       store demand curves and rent, warehouse rent and capacity, travel-time matrices
outputs/                    warehouses.txt, stores.txt, routes.txt (the submitted solution)
notebooks/part2_colab.ipynb the same pipeline as it ran in Colab
docs/report.docx            report with the full algebraic formulation
```

**Run it:** `pip install amplpy pandas`, activate an AMPL license with Gurobi (`AMPL_LICENSE_UUID`), then `python optimize.py` from the repo root.

**Tools:** AMPL, Gurobi, Python (pandas, amplpy)
