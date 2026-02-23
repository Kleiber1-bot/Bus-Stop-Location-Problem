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
alpha = Parameter(m, name="alpha", records=0.5, description="Weight", is_miro_input=True)
cost_per_stop = Parameter(m, name="cost_per_stop", records=60000, description="Cost for one Bus Stop", is_miro_input=True)

# Shadow parameter
p_calc = Parameter(m, name="p_calc", records=40, description="Internal Solver Limit")
total_pop = Parameter(m, name="total_pop_const")
total_pop[...] = Sum(i, c[i])
max_walk_per_person = 1000

# Coverage Matrix
a = Parameter(m, name="a", domain=[i, j])
a[i, j].where[d[i, j] <= r] = 1 # quasi N_i von trad. mclp -> Set of candidate stops in range r

X = Variable(m, name="X", domain=j, type="Binary")
Y = Variable(m, name="Y", domain=[i, j], type="Binary")
ObjVal = Variable(m, name="ObjVal", type="free")

objective = Equation(m, name="objective")
assign_limit = Equation(m, name="assign_limit", domain=i)
open_cond = Equation(m, name="open_cond", domain=[i, j])
range_cond = Equation(m, name="range_cond", domain=[i, j])
num_stops = Equation(m, name="num_stops")


assign_limit[i] = Sum(j, Y[i, j]) <= 1
open_cond[i, j] = Y[i, j] <= X[j]
range_cond[i, j] = Y[i, j] <= a[i, j]
num_stops[...]  = Sum(j, X[j]) <= p_calc

# 1. Parameters for normalization
z_cost_ideal = Parameter(m, name="z_cost_ideal", records=0)
z_cost_nadir = Parameter(m, name="z_cost_nadir", records=0)
z_ben_ideal  = Parameter(m, name="z_ben_ideal", records=0)
z_ben_nadir  = Parameter(m, name="z_ben_nadir", records=0)

#  ranges to 1 to prevent division-by-zero
r_cost = Parameter(m, name="r_cost", records=1)
r_ben  = Parameter(m, name="r_ben", records=1)

#####PRE-SOLVE ######

# 1. DEFINE THE MIN COVERAGE EQUATION
min_cov_eq = Equation(m, name="min_cov_eq", description="Enforce Min Coverage %")
min_cov_eq[...] = Sum([i, j], c[i] * Y[i, j]) >= total_pop * (min_coverage_pct / 100)

#  p_calc for the pre-solve (using user input)
p_calc.setRecords(p.toValue())

# A) SUB-PROBLEM 1: Minimize Cost (number of Stops)
obj_stops = Equation(m, name="obj_stops")
obj_stops[...] = ObjVal == Sum(j, X[j])

Model_Cost = Model(m, name="Model_Cost", 
                   equations=[obj_stops, assign_limit, open_cond, range_cond, min_cov_eq], 
                   sense=Sense.MIN, objective=ObjVal)

print("\n--- PRE-SOLVE: Finding Ideal Cost ---")
Model_Cost.solve()
print("############ Objective Value (Min Stops) ############")
print (ObjVal.toValue())
# Get the minimum stops required to hit the target coverage
required_stops = ObjVal.toValue()
min_stops_needed_msg = Parameter(m, name="min_stops_needed_msg", description="validation_result", is_miro_output=True)

min_stops_needed_msg[...] = required_stops

user_p_val = p.toValue()
# Check for infeasibility
if Model_Cost.status == ModelStatus.InfeasibleGlobal:
    print("CRITICAL: The requested coverage is impossible even with ALL stops.")
    p_calc.setRecords(500) 
else:
    if required_stops > user_p_val:
        print(f"WARNING: User requested {user_p_val} stops, but {required_stops} are needed for coverage.")
        print(f"-> Overwriting Limit: Setting max stops to {required_stops}")
        
        p_calc.setRecords(required_stops)
    else:
        print("Validation OK: User limit is sufficient.")
        p_calc.setRecords(user_p_val)

# Cost = stops

############ This is where the normalization part starts ############
z_cost_ideal[...] = required_stops

# Calculate Nadir Benefit 
# Benefit Formula = (Coverage - Walking distance)
z_ben_nadir[...] = (Sum([i, j], c[i] * Y.l[i, j]) / total_pop) - \
                   (Sum([i, j], d[i, j] * Y.l[i, j] * c[i]) / (total_pop * max_walk_per_person))


# B) SUB-PROBLEM 2: Maximize Benefit (Coverage/Distance)
obj_benefit = Equation(m, name="obj_benefit")
obj_benefit[...] = ObjVal == (Sum([i, j], c[i] * Y[i, j]) / total_pop) - \
                             (Sum([i, j], d[i, j] * Y[i, j] * c[i]) / (total_pop * max_walk_per_person))

Model_Ben = Model(m, name="Model_Ben", 
                  equations=[obj_benefit, assign_limit, open_cond, range_cond, num_stops, min_cov_eq], 
                  sense=Sense.MAX, objective=ObjVal)



print("\n--- PRE-SOLVE: Finding Ideal Benefit ---")
Model_Ben.solve()


print("############ Objective Value (Max Benefit) ############")
print (ObjVal.toValue())
z_ben_ideal[...]  = ObjVal.l
z_cost_nadir[...] = Sum(j, X.l[j])


# C) Compute Ranges - +1e-6 to avoid zero division
r_cost[...] = (z_cost_nadir - z_cost_ideal) + 1e-6
r_ben[...]  = (z_ben_ideal - z_ben_nadir) + 1e-6


##### Objective Function with Normalization #####

objective[...] = ObjVal == (
    # Normalized Benefit: (Actual - Nadir) / Range
    alpha * ( 
        ( (Sum([i, j], c[i] * Y[i, j]) / total_pop) 
          - (Sum([i, j], d[i, j] * Y[i, j] * c[i]) / (total_pop * max_walk_per_person)) 
          - z_ben_nadir 
        ) / r_ben
    )
    - 
    # Normalized Cost: (Actual - Ideal) / Range
    (1 - alpha) * (
        (Sum(j, X[j]) - z_cost_ideal) / r_cost
    )
)

MCLP = Model(m, name="MCLP", equations=[objective, assign_limit, open_cond, range_cond, num_stops, min_cov_eq], 
             problem="MIP", sense=Sense.MAX, objective=ObjVal)


# 6. OPTIMIZATION LOOP (Marginal Gain Calculation)

user_p = p.toValue()


#Step A: Solve for p + 1
#print(f"\n--- CALCULATING MARGINAL BENEFIT (Testing p={int(user_p + 1)}) ---")
#p_calc.setRecords(user_p + 1)
#MCLP.solve(output=sys.stdout)
#served_plus_one = Sum([i, j], c[i] * Y.l[i, j]).toValue()

##### Solving the Model#####
print(f"\n--- CALCULATING FINAL RESULT (Restoring p={int(user_p)}) ---")
p_calc.setRecords(user_p)
MCLP.solve(output=sys.stdout)

print("############ Objective Value MCLP ############")
print (ObjVal.toValue())
##### Declare Miro Output #######

# KPIs
total_demand = Parameter(m, name="total_demand", is_miro_output=True)
served_demand = Parameter(m, name="served_demand", is_miro_output=True)
unserved_demand = Parameter(m, name="unserved_demand", is_miro_output=True)
coverage_pct = Parameter(m, name="coverage_pct", is_miro_output=True)
num_built_stops = Parameter(m, name="num_built_stops", description="Number of Stops Built", is_miro_output=True)
avg_walking_dist = Parameter(m, name="avg_walking_dist", description="Avg Walking Dist (m)", is_miro_output=True)
total_cost_Bus_stops_used = Parameter(m, name="total_cost_Bus_stops_used", description="Total costs for Bus Stops used", is_miro_output=True)
cost_per_stop_value = Parameter(m, name="cost_per_stop_value", description="Cost per Bus Stop", is_miro_output=True)   
#marginal_cost_bus_stops = Parameter(m, name="marginal_cost_bus_stops", description="Marginal Cost per Additional Bus Stop", is_miro_output=True)
#min_stops_needed_msg = Parameter(m, name="min_stops_needed_msg", description="validation_result", is_miro_output=True)

num_built_stops[...] = Sum(j, X.l[j])
total_demand[...] = Sum(i, c[i])
served_demand[...] = Sum([i, j], c[i] * Y.l[i, j])
unserved_demand[...] = total_demand - served_demand
coverage_pct[...] = (served_demand / total_demand) * 100
total_walk_dist = Sum([i, j], d[i, j] * Y.l[i, j] * c[i])
cost_per_stop_value[...] = cost_per_stop.toValue()
total_cost_Bus_stops_used[...] = num_built_stops * cost_per_stop.toValue()*2
#marginal_cost_bus_stops[...] = 120000  # Fixed cost per additional bus stop (2 Busstops have to be built)

served_val = served_demand.toValue()
dist_val = total_walk_dist.toValue()

# avoid division by zero
if served_val > 0:
    avg_walking_dist[...] = dist_val / served_val
else:
    avg_walking_dist[...] = 0


print(f"Built Stops: {num_built_stops.toValue()}")
print(f"Avg Walking Distance: {avg_walking_dist.toValue():.2f} m")


# Tooltip
stop_coverage = Parameter(m, name="stop_coverage", domain=j)
stop_coverage[j] = Sum(i, c[i] * Y.l[i, j])

# 0. Setup references
map_headers = Set(m, name="map_headers", records=["lat", "lon", "status", "served"])
sol_headers = m["sol_headers"]
lat = m["lat"]
lon = m["lon"]
is_built = (X[j].l > 0.5)


# 1. map_data: ALL Candidates 

map_data = Parameter(m, 
                     name="map_data", 
                     domain=[j, sol_headers], 
                     is_miro_output=True, 
                     is_miro_table=True,
                     description="All Candidates & Results")

# Fill data for ALL stops
map_data[j, "lat"] = lat[j]
map_data[j, "lon"] = lon[j]
map_data[j, "status"] = X[j].l  # Contains both 0s and 1s



# 2. map_data_filtered: Built Stops ONLY 

map_data_filtered = Parameter(m, 
                              name="map_data_filtered", 
                              domain=[j, map_headers], 
                              is_miro_output=True, 
                              is_miro_table=True,
                              description="Built Stops Only")

# Fill data ONLY where is_built is True
map_data_filtered[j, "lat"].where[is_built] = lat[j]
map_data_filtered[j, "lon"].where[is_built] = lon[j]
map_data_filtered[j, "status"].where[is_built] = 1
from gamspy.math import Round
map_data_filtered[j, "served"].where[is_built] = Round(stop_coverage[j], 1)

print(f"\nAbdeckung: {coverage_pct.toValue():.2f}%")