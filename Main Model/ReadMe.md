# User Manual: Bus Stop Location Optimization Tool

Welcome to the **Bus Stop Location Optimization Tool**. This interactive dashboard allows urban planners and decision-makers to design efficient public transport networks by balancing financial costs with public accessibility. 

Follow these three steps to use the tool effectively:

![Bus Stop Location Optimization Tool](Bus-Stop-Location-Optimization-Tool_page-0001.jpg)
---

## 1. Configure Your Inputs
The tool provides flexible parameters so you can customize the optimization model to fit specific municipal needs and budgets. 

* **Weighting Factor (Alpha):** Use the slider to balance the two competing objectives. A higher value prioritizes the **Benefit for Society** (maximizing coverage and minimizing walking distance), while a lower value prioritizes **Profit/Cost Efficiency** (minimizing the number of built stops).
* **Max Walking Distance:** Set the maximum acceptable distance (in meters) a citizen should have to walk to reach a bus stop. 
* **Max Bus Stops:** Set a strict upper limit on how many bus stops can be built, acting as your budget constraint.
* **Minimum Coverage Percentage:** Guarantee a baseline service level by forcing the model to cover at least this percentage of the total population. 
* **Fixed Cost per Bus Stop:** Input the financial cost of building a single stop to calculate total network investments.

> **💡 Pro-Tip: Switch from MCLP to LSCP**
> By default, the tool solves a Maximal Covering Location Problem (MCLP) to maximize coverage within your budget. However, you can easily switch the tool to solve a Location Set Covering Problem (LSCP)—which finds the absolute minimum cost required to serve the entire city. 
> 
> *To do this: Set the **Minimum Coverage Percentage to 100%** and the **Weighting Factor (Alpha) to 0**.*

---

## 2. Analyze the Results
Once the model runs, you can evaluate the proposed network through two main views:

* **KPI Dashboard:** Review high-level metrics at a glance, including total population served, average walking distance, and total construction costs.
* **Interactive Maps:** Visually inspect the spatial distribution of the network. 
    * **Map 1:** Visualizes all potential candidate locations for bus stops.
    * **Map 2:** Shows only the optimal bus stops that the model selected to be built, allowing you to see exactly where investments will go.



---

## 3. Compare Scenarios
Decision-making requires understanding trade-offs. The tool allows you to save and compare different optimization runs side-by-side.

* Evaluate the **marginal change** in each objective (e.g., "How much more coverage do we get if we build exactly one more stop?").
* Compare a heavily budget-constrained scenario against a highly service-oriented scenario to find the perfect political and financial middle ground.


