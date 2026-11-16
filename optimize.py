# Retail network optimization
#   1. Fix price at $38 and compute each store's demand and profit
#   2. MILP (AMPL + Gurobi): which warehouses to open, which stores to serve, assignments
#   3. Greedy vehicle routing under capacity and time limits
#   4. Daily profit after routing costs; writes outputs/warehouses.txt, stores.txt, routes.txt
#
# Needs an AMPL license with Gurobi. Set AMPL_LICENSE_UUID or run inside the Colab notebook.

import pandas as pd
from amplpy import AMPL

PRICE = 38
UNIT_COST = 10
MARGIN = PRICE - UNIT_COST       # 28
VEH_CAP = 500
ROUTE_LIMIT = 480                # minutes (8 hours)
SERVICE_TIME = 30                # per store
VEHICLE_COST = 200               # per vehicle
TIME_COST = 0.1                  # $ per minute

# ------------------------------------------------------------
# Compute single-store route feasibility
# ------------------------------------------------------------
def single_route_time(w, i, whtt):
    t = float(whtt.loc[f"wh{w}", f"store{i}"])
    return 2 * t + SERVICE_TIME

# ------------------------------------------------------------
# Compute time of route (wh -> s1 -> ... -> sn -> wh)
# ------------------------------------------------------------
def route_time(wh, stores, whtt, storett):
    if not stores:
        return 0

    time = float(whtt.loc[f"wh{wh}", f"store{stores[0]}"])
    time += SERVICE_TIME

    for a, b in zip(stores, stores[1:]):
        time += float(storett.loc[f"store{a}", f"store{b}"])
        time += SERVICE_TIME

    time += float(whtt.loc[f"wh{wh}", f"store{stores[-1]}"])
    return time

# ------------------------------------------------------------
# Greedy VRP Algo
# ------------------------------------------------------------
def build_routes(open_whs, wh_assign, demand, whtt, storett):
    routes = []
    for w in open_whs:
        remaining = set(wh_assign[w])

        while remaining:
            load = 0
            route = []

            # pick first store = nearest to warehouse
            candidates = list(remaining)
            candidates.sort(key=lambda s: float(whtt.loc[f"wh{w}", f"store{s}"]))

            for s in candidates:
                d = demand[s]
                if d <= VEH_CAP:
                    if single_route_time(w, s, whtt) <= ROUTE_LIMIT:
                        route.append(s)
                        load += d
                        remaining.remove(s)
                    break

            # greedily add more stores
            improved = True
            while improved and remaining:
                improved = False
                best = None
                best_dist = None

                for s in remaining:
                    if load + demand[s] > VEH_CAP:
                        continue
                    t = route_time(w, route + [s], whtt, storett)
                    if t <= ROUTE_LIMIT:
                        dist = float(storett.loc[f"store{route[-1]}", f"store{s}"])
                        if best is None or dist < best_dist:
                            best = s
                            best_dist = dist

                if best is not None:
                    route.append(best)
                    load += demand[best]
                    remaining.remove(best)
                    improved = True

            routes.append((w, [(s, demand[s]) for s in route]))

    return routes

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    whdata = pd.read_csv("data/whdata.csv")
    storedata = pd.read_csv("data/storedata.csv")
    whtt = pd.read_csv("data/whtt.csv", index_col=0)
    storett = pd.read_csv("data/storett.csv", index_col=0)

    demand = {}
    store_profit = {}

    # ---------------------------------------------------------
    # Compute demand & store profit at price 38
    # ---------------------------------------------------------
    for _, row in storedata.iterrows():
        i = int(row["store"])
        a = float(row["inter"])
        b = float(row["slope"])
        rent = float(row["rent"])

        d = a + b * PRICE
        if d < 0:
            d = 0

        demand[i] = d
        store_profit[i] = MARGIN * d - rent

    # ---------------------------------------------------------
    # Feasibility matrix for AMPL (single-store route check)
    # ---------------------------------------------------------
    feasible = {}
    W = sorted(whdata["wh"].unique())
    S = sorted(storedata["store"].unique())

    for w in W:
        for i in S:
            t = single_route_time(w, i, whtt)
            feasible[(w, i)] = 1 if t <= ROUTE_LIMIT else 0

    # ---------------------------------------------------------
    # Run AMPL
    # ---------------------------------------------------------
    ampl = AMPL()
    ampl.read("model/part2.mod")
    ampl.setOption("solver", "gurobi")

    ampl.getSet("W").setValues(W)
    ampl.getSet("S").setValues(S)

    ampl.getParameter("cap").setValues({int(r.wh): float(r.cap) for _, r in whdata.iterrows()})
    ampl.getParameter("wh_rent").setValues({int(r.wh): float(r.rent) for _, r in whdata.iterrows()})
    ampl.getParameter("demand").setValues(demand)
    ampl.getParameter("store_profit").setValues(store_profit)
    ampl.getParameter("feasible").setValues(feasible)

    ampl.solve()

    base_profit = ampl.getObjective("Profit").value()
    print(f"\nMILP profit (without routing costs): {base_profit:.2f}\n")

    x_vals = ampl.getVariable("x").getValues().toDict()
    y_vals = ampl.getVariable("y").getValues().toDict()
    z_vals = ampl.getVariable("z").getValues().toDict()

    open_stores = [i for i, v in x_vals.items() if v > 0.5]
    open_whs = [w for w, v in y_vals.items() if v > 0.5]

    wh_assign = {w: [] for w in open_whs}
    for (w, i), v in z_vals.items():
        if v > 0.5 and w in open_whs and i in open_stores:
            wh_assign[w].append(i)

    # ---------------------------------------------------------
    # Build Routes
    # ---------------------------------------------------------
    routes = build_routes(open_whs, wh_assign, demand, whtt, storett)

    # ---------------------------------------------------------
    # Compute routing costs
    # ---------------------------------------------------------
    total_route_cost = 0

    for w, stops in routes:
        stores = [s for s, _ in stops]
        t = route_time(w, stores, whtt, storett)
        cost = VEHICLE_COST + TIME_COST * t
        total_route_cost += cost

    final_profit = base_profit - total_route_cost

    print(f"Routing cost: {total_route_cost:.2f}")
    print(f"\n===== FINAL DAILY PROFIT INCLUDING ROUTING =====")
    print(f"FINAL PROFIT = {final_profit:.2f}\n")

    # ---------------------------------------------------------
    # Write warehouses.txt
    # ---------------------------------------------------------
    with open("outputs/warehouses.txt", "w") as f:
        for w in open_whs:
            stock = sum(demand[i] for i in wh_assign[w])
            f.write(f"{w},{stock:.4f}\n")

    # ---------------------------------------------------------
    # Write stores.txt
    # ---------------------------------------------------------
    with open("outputs/stores.txt", "w") as f:
        for i in open_stores:
            f.write(f"{i},{PRICE:.2f}\n")

    # ---------------------------------------------------------
    # Write routes.txt
    # ---------------------------------------------------------
    with open("outputs/routes.txt", "w") as f:
        for w, stops in routes:
            parts = [str(w)]
            for i, q in stops:
                parts.append(f"{i}:{q:.4f}")
            f.write(",".join(parts) + "\n")

    print("Generated files: warehouses.txt, stores.txt, routes.txt")


if __name__ == "__main__":
    main()
