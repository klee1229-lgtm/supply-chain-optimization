
set W;
set S;

param cap{W} >= 0;
param wh_rent{W} >= 0;
param demand{S} >= 0;
param store_profit{S};
param feasible{W,S} binary;

var x{S} binary;
var y{W} binary;
var z{W,S} binary;

s.t. assign_one{i in S}:
    sum{w in W} z[w,i] = x[i];

s.t. require_wh_open{w in W, i in S}:
    z[w,i] <= y[w];

s.t. time_feasible_assign{w in W, i in S}:
    z[w,i] <= feasible[w,i];

s.t. warehouse_capacity{w in W}:
    sum{i in S} demand[i] * z[w,i] <= cap[w];

maximize Profit:
    sum{i in S} store_profit[i] * x[i]
  - sum{w in W} wh_rent[w] * y[w];
