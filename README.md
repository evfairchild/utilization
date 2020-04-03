# Airbus Engine and Airframe Flight Hour and Flight Cycle Utilization
This is a monthly report provided by reliability engineering to the Alaska Airlines records and finance departments.  

The Airframe report tables monthly flight hour and flight cycle totals for all aircraft on the Alaska Airlines Ops Spec.

The Engine report tables monthly flight hour and flight cycle totals for all ESN (engine serial numbers) in the rotable parts fleet history.  Engine installs and removals are also provided for the month queried.   

# Windows
## **Install Python**
I recommend installing the entire anaconda data science package: https://docs.anaconda.com/anaconda/install/windows/ 
This will take some time.

# Mac
`sudo easy_install pip`

**To Run (windows only):**

`pip install -r requirements.txt`
`python reports.py`

The script will produce a single Excel workbook with Engine and Airframe worksheets, containing flight hours and flight cycles for the month requested and the aggregate totals for the fleet's entire history.   The third worksheet listed Engine removals and installs for the month requested.  


