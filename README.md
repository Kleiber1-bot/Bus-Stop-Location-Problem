# Bus-Stop-Location-Problem
Mathematical Model which extends the traditional MCLP, using a multi objective approach
====================================================================
Instructions for Running the Bus Stop Location MIRO App
====================================================================

Because this MIRO application relies on a custom Python model (GAMSPy), 
it requires a local Python environment to run the optimization backend. 
Please follow these three steps to set it up on your machine.

--------------------------------------------------------------------
STEP 1: Prerequisites
--------------------------------------------------------------------
Before starting, ensure you have the following installed on your computer:
1. GAMS 
2. GAMS MIRO
3. GAMSPy
4. A valid GAMS license configured on your machine
5. Python 3.10 or higher

For the GAMSPy installation follow the information on the official website: 
https://gamspy.readthedocs.io/en/latest/user/installation.html

After installing everything -> Step 2

--------------------------------------------------------------------
STEP 2: Link MIRO to the Environment
--------------------------------------------------------------------
Finally, tell the GAMS MIRO application to use this specific Python 
environment when solving the model.

1. Open the GAMS MIRO desktop application.
2. Open the Preferences menu.
3. Look for the "Paths".
4. Look for the "Python path"
5. Paste the absolute path to the Python executable located inside 
   the 'miro_env' folder you just created:
   
   -> Mac/Linux Example: 
      /Users/YourName/path/to/miro_env/bin/python3
   
   -> Windows Example: 
      C:\Users\YourName\path\to\miro_env\Scripts\python.exe

6. Save the preferences and close the settings window.

You are all set! You can now double-click the .miroapp file to open 
the dashboard, configure your parameters, and click "Solve".
