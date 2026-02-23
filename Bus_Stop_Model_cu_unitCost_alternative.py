from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum, Sense, Alias
from gamspy.math import Round
from gamspy import ModelStatus
import sys

# 1. LOAD DATA
m = Container(load_from="aachen_data_clean_withNames2.gdx")
i = m["i"]          
j = Alias(m, name="j", alias_with=i)
d = m["d"]          
c = m["c"]          
lat = m["lat"]      
lon = m["lon"]      

# 2. INPUT PARAMETERS
r = Parameter(m, name="r", records=400, description="Service Radius (m)", is_miro_input=True)
p = Parameter(m, name="p", records=40, description="Max Stops to Open", is_miro_input=True)
min_coverage_pct = Parameter(m, name="min_coverage_pct", records=10, description="Minimum Coverage Percentage", is_miro_input=True)
alpha = Parameter(m, name="alpha", records=0.5, description="Weight (0=Budget Focus, 1=Society Focus)", is_miro_input=True)
cost_per_stop = Parameter(m, name="cost_per_stop", records=60000, description="Cost for one Bus Stop", is_miro_input=True)


# Cost of walking 1 meter (e.g., 0.005 Euros per meter per person)
c_walk = Parameter(m, name="c_walk", records=0.005, description="Cost of walking per meter per person")

# Penalty cost if a person is NOT served (e.g., 5.00 Euros -> Cost of alternative transport)
c_miss = Parameter(m, name="c_miss", records=5.00, description="Penalty cost per unserved person")

# Shadow parameter and constants
p_calc = Parameter(m, name="p_calc", records=40, description="Internal Solver Limit")
total_pop = Parameter(m, name="total_pop_const")
total_pop[...] = Sum(i, c[i])
max_walk_per_person = 1000 # Python helper variable

# Total potential penalty
total_penalty_const = Parameter(m, name="total_penalty_const", records=0)
total_penalty_const[...] = Sum(i, c[i] * c_miss)


# Coverage Matrix
a = Parameter(m, name="a", domain=[i, j])
a[i, j].where[d[i, j] <= r] = 1

# 4. VARIABLES
X = Variable(m, name="X", domain=j, type="Binary")
Y = Variable(m, name="Y", domain=[i, j], type="Binary")
ObjVal = Variable(m, name="ObjVal", type="free")

# 5. EQUATIONS
objective = Equation(m, name="objective")
assign_limit = Equation(m, name="assign_limit", domain=i)
open_cond = Equation(m, name="open_cond", domain=[i, j])
range_cond = Equation(m, name="range_cond", domain=[i, j])
num_stops = Equation(m, name="num_stops")
min_cov_eq = Equation(m, name="min_cov_eq", description="Enforce Min Coverage %")

# Constraint Definitions
assign_limit[i] = Sum(j, Y[i, j]) <= 1
open_cond[i, j] = Y[i, j] <= X[j]
range_cond[i, j] = Y[i, j] <= a[i, j]
num_stops[...]  = Sum(j, X[j]) <= p_calc
min_cov_eq[...] = Sum([i, j], c[i] * Y[i, j]) >= total_pop * (min_coverage_pct / 100)

objective[...] = ObjVal == (
    # INFRASTRUCTURE COST
    (1 - alpha) * Sum(j, cost_per_stop * X[j])
    
    + 
    
    # SOCIETAL COST
    alpha * (
        # 1. Cost of Walking for served people
        Sum([i, j], c[i] * Y[i, j] * d[i, j] * c_walk)
        +
        # 2. Cost of NOT being served (Total Potential Penalty - Penalty Saved by serving)
        (total_penalty_const - Sum([i, j], c[i] * Y[i, j] * c_miss))
    )
)

# 6. DEFINE MODEL
MCLP = Model(m, name="MCLP", 
             equations=[objective, assign_limit, open_cond, range_cond, num_stops, min_cov_eq], 
             problem="MIP", sense=Sense.MIN, objective=ObjVal)


# 7. SOLVE
p_calc.setRecords(p.toValue()) # Set the user limit

print(f"\n--- SOLVING LINEAR MODEL (p={p.toValue()}) ---")
MCLP.solve(output=sys.stdout)

# Check status
if MCLP.status == ModelStatus.InfeasibleGlobal:
    print("CRITICAL: Model is Infeasible. Check 'Min Coverage' or 'Max Stops'.")
else:
    print("############ Objective Value (Total System Cost in Euros) ############")
    print(f"{ObjVal.toValue():.2f} €")


# 8. DECLARE MIRO OUTPUT & KPIs

# KPIs
total_demand = Parameter(m, name="total_demand", is_miro_output=True)
served_demand = Parameter(m, name="served_demand", is_miro_output=True)
unserved_demand = Parameter(m, name="unserved_demand", is_miro_output=True)
coverage_pct = Parameter(m, name="coverage_pct", is_miro_output=True)
num_built_stops = Parameter(m, name="num_built_stops", description="Number of Stops Built", is_miro_output=True)
avg_walking_dist = Parameter(m, name="avg_walking_dist", description="Avg Walking Dist (m)", is_miro_output=True)
total_cost_Bus_stops_used = Parameter(m, name="total_cost_Bus_stops_used", description="Total costs for Bus Stops used", is_miro_output=True)
cost_per_stop_value = Parameter(m, name="cost_per_stop_value", description="Cost per Bus Stop", is_miro_output=True)   

# Calculate KPIs
num_built_stops[...] = Sum(j, X.l[j])
total_demand[...] = Sum(i, c[i])
served_demand[...] = Sum([i, j], c[i] * Y.l[i, j])
unserved_demand[...] = total_demand - served_demand
coverage_pct[...] = (served_demand / total_demand) * 100
total_walk_dist = Sum([i, j], d[i, j] * Y.l[i, j] * c[i])
cost_per_stop_value[...] = cost_per_stop.toValue()
total_cost_Bus_stops_used[...] = num_built_stops * cost_per_stop.toValue() * 2 # Keeping your original *2 factor

served_val = served_demand.toValue()
dist_val = total_walk_dist.toValue()

# avoid division by zero
if served_val > 0:
    avg_walking_dist[...] = dist_val / served_val
else:
    avg_walking_dist[...] = 0

print(f"Built Stops: {num_built_stops.toValue()}")
print(f"Avg Walking Distance: {avg_walking_dist.toValue():.2f} m")
print(f"Abdeckung: {coverage_pct.toValue():.2f}%")


# 9. PREPARE MAP DATA
stop_coverage = Parameter(m, name="stop_coverage", domain=j)
stop_coverage[j] = Sum(i, c[i] * Y.l[i, j])

map_headers = Set(m, name="map_headers", records=["lat", "lon", "status", "served"])
sol_headers = m["sol_headers"]
lat = m["lat"]
lon = m["lon"]
is_built = (X[j].l > 0.5)

# map_data: ALL Candidates 
map_data = Parameter(m, 
                     name="map_data", 
                     domain=[j, sol_headers], 
                     is_miro_output=True, 
                     is_miro_table=True,
                     description="All Candidates & Results")

map_data[j, "lat"] = lat[j]
map_data[j, "lon"] = lon[j]
map_data[j, "status"] = X[j].l 

# map_data_filtered: Built Stops ONLY 
map_data_filtered = Parameter(m, 
                              name="map_data_filtered", 
                              domain=[j, map_headers], 
                              is_miro_output=True, 
                              is_miro_table=True,
                              description="Built Stops Only")

map_data_filtered[j, "lat"].where[is_built] = lat[j]
map_data_filtered[j, "lon"].where[is_built] = lon[j]
map_data_filtered[j, "status"].where[is_built] = 1
map_data_filtered[j, "served"].where[is_built] = Round(stop_coverage[j], 1)