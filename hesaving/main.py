from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel, validator, constr 
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from typing import Optional
from datetime import datetime, time

import joblib
import os
import numpy as np
import boto3
import psycopg2
import json
import csv

origins = ["https://hes-ui-ymexo7.flutterflow.app",
]

middleware = [
    Middleware(
        CORSMiddleware,
        #allow_origins=origins,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET","POST"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
]
#ssm = boto3.client('ssm')

#username = os.environ.get('DB_USERNAME')
#password = os.environ.get('DB_PASSWORD')

# Connect to the DB
conn = psycopg2.connect(
    host="hes-db.cuojxnjfrbc7.us-east-1.rds.amazonaws.com",
    database="postgres",
    user=username,
    password=password,
    port=5432
)

app = FastAPI(title="Home Energy Savings App backed APIs", middleware=middleware)

class new_device(BaseModel):
    """ Schema for device input"""
    device_name: Optional[constr(curtail_length = 20)] 
    status: Optional[bool] = False
    device_type: str

class upd_device(BaseModel):
    """ Schema for device update"""
    device_id : int
    device_name: Optional[constr(curtail_length = 20)] 
    status: Optional[bool] = False
    device_type: str
    flag: str

    # flag validity check
    @validator('flag')
    def flag_valid(cls,v):
        if v not in ["U","D"]:
            raise HTTPException(status_code=422,detail="Invalid flag value not in [I,U,D]")
        return v

class results(BaseModel):
    """ Schema for results insert"""
    scenario_id: Optional[int] = 99
    timestamp: str
    pv_reward: float
    solar_action : float
    solar_available_power : float
    solar_actionable_power : float
    grid_price : float
    es_cost : float
    es_reward : float
    es_action : float
    es_power_ask : float
    es_current_storage : float
    es_solar_power_consumed : float
    es_grid_power_consumed : float
    es_post_solar_power_available : float
    es_post_grid_power_available : float
    es_post_es_power_available : float
    ev_cost : float
    ev_reward : float
    ev_action : float
    ev_power_ask : float
    ev_power_unserved : float
    ev_charging_vehicle : float
    ev_vehicle_charged : float
    ev_post_solar_power_available : float
    ev_post_es_power_available : float
    ev_post_grid_power_available : float
    ev_solar_power_consumed : float
    ev_es_power_consumed : float
    ev_grid_power_consumed : float
    oth_dev_cost : float
    oth_dev_reward : float
    oth_dev_action : float
    oth_dev_solar_power_consumed : float
    oth_dev_es_power_consumed : float
    oth_dev_grid_power_consumed : float
    oth_dev_power_ask : float
    oth_dev_post_solar_power_available : float
    oth_dev_post_es_power_available : float
    oth_dev_post_grid_power_available : float

class result_dict(BaseModel):
    """Input samples list schema"""
    result: list[results]

# get all devices
@app.get("/device")
def get_device():
    
    # Select Devices
    select_devices = "SELECT * FROM device"
    
    # Execute the query and fetch the results
    cur = conn.cursor()
    cur.execute(select_devices)
    devices = cur.fetchall()

    # Format Devices
    # like {"devices":{{"device_id":1,"device_name":"My Batt","status":False,"device_type":"BATT"},
    # {"device_id":2,"device_name":"My Batt 2","status":False,"device_type":"BATT"},...}}
    
    dev_id = [i[0] for i in devices]
    dev_name = [i[1] for i in devices]
    stat = [i[2] for i in devices]
    dev_type = [i[3] for i in devices]

    keys = ["device_id","device_name","status","device_type"]
    items = [dict(zip(keys, [i, n, s, t])) for i, n, s, t in zip(dev_id, dev_name , stat, dev_type)]
    #items = json.dumps(items)
    
    # Format the results as JSON and return them through the API
    return {"devices": items}

# health endpoint to check API
@app.get("/health")
async def app_health():
    return {"app_status": "healthy"}

# insert a new device
@app.post("/new_device")
async def new_device(input : new_device):
    device_name = dict(input).get("device_name")
    status = dict(input).get("status")
    device_type = dict(input).get("device_type")   

    # Insert new device
    insert_device = f"INSERT INTO device (device_name, status, device_type) VALUES \
        ('{device_name}','{status}','{device_type}');COMMIT;"
    
    # Execute the query and insert
    cur = conn.cursor()
    cur.execute(insert_device)
   
    return {"device": "inserted"}

# insert a new device
@app.post("/upd_device")
async def upd_device(input : upd_device):
    device_id = dict(input).get("device_id")
    device_name = dict(input).get("device_name")
    status = dict(input).get("status")
    device_type = dict(input).get("device_type")
    flag = dict(input).get("flag")      
    
    if flag == "U":
        # Update a device
        update_device = f"UPDATE device SET device_name = '{device_name}',status = '{status}', \
            device_type = '{device_type}' WHERE device_id = '{device_id}';COMMIT;"
        job = "updated"
    else:
        # Delete a device
        update_device = f"DELETE FROM device WHERE device_id = '{device_id}';COMMIT;"
        job = "deleted"
    
    # Execute the query and update/delete
    cur = conn.cursor()
    cur.execute(update_device)
   
    return {"device": job}

# insert results
@app.post("/result")
async def results(input : result_dict):

    # Select run id
    select_runid = "SELECT MAX(run_id) FROM result"
        
    # Execute the query and fetch the run id
    cur1 = conn.cursor()
    cur1.execute(select_runid)
    max_run = cur1.fetchone()[0]
    
    if max_run is None:
        run_id = 1
    else:
        run_id = int(max_run) + 1       
    
    for row in dict(input)['result']:


        scenario_id = dict(row).get("scenario_id")
        timestamp = dict(row).get("timestamp")
        pv_reward = dict(row).get("pv_reward")
        solar_action = dict(row).get("solar_action")
        solar_available_power = dict(row).get("solar_available_power")
        solar_actionable_power = dict(row).get("solar_actionable_power")
        grid_price = dict(row).get("grid_price")
        es_cost = dict(row).get("es_cost")
        es_reward = dict(row).get("es_reward")
        es_action = dict(row).get("es_action")
        es_power_ask = dict(row).get("es_power_ask")
        es_current_storage = dict(row).get("es_current_storage")
        es_solar_power_consumed = dict(row).get("es_solar_power_consumed")
        es_grid_power_consumed = dict(row).get("es_grid_power_consumed")
        es_post_solar_power_available = dict(row).get("es_post_solar_power_available")
        es_post_grid_power_available = dict(row).get("es_post_grid_power_available")
        es_post_es_power_available = dict(row).get("es_post_es_power_available")
        ev_cost = dict(row).get("ev_cost")
        ev_reward = dict(row).get("ev_reward")
        ev_action = dict(row).get("ev_action")
        ev_power_ask = dict(row).get("ev_power_ask")
        ev_power_unserved = dict(row).get("ev_power_unserved")
        ev_charging_vehicle = dict(row).get("ev_charging_vehicle")
        ev_vehicle_charged = dict(row).get("ev_vehicle_charged")
        ev_post_solar_power_available = dict(row).get("ev_post_solar_power_available")
        ev_post_es_power_available = dict(row).get("ev_post_es_power_available")
        ev_post_grid_power_available = dict(row).get("ev_post_grid_power_available")
        ev_solar_power_consumed = dict(row).get("ev_solar_power_consumed")
        ev_es_power_consumed = dict(row).get("ev_es_power_consumed")
        ev_grid_power_consumed = dict(row).get("ev_grid_power_consumed")
        oth_dev_cost = dict(row).get("oth_dev_cost")
        oth_dev_reward = dict(row).get("oth_dev_reward")
        oth_dev_action = dict(row).get("oth_dev_action")
        oth_dev_solar_power_consumed = dict(row).get("oth_dev_solar_power_consumed")
        oth_dev_es_power_consumed = dict(row).get("oth_dev_es_power_consumed")
        oth_dev_grid_power_consumed = dict(row).get("oth_dev_grid_power_consumed")
        oth_dev_power_ask = dict(row).get("oth_dev_power_ask")
        oth_dev_post_solar_power_available = dict(row).get("oth_dev_post_solar_power_available")
        oth_dev_post_es_power_available = dict(row).get("oth_dev_post_es_power_available")
        oth_dev_post_grid_power_available = dict(row).get("oth_dev_post_grid_power_available")
       
        datetime_object = datetime.strptime(timestamp, '%m-%d-%Y %H:%M:%S')
        time = datetime_object.time()
        timestamp = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

        create_ts = datetime.now()
        source = 'agent'

        # Insert new results
        insert_result = f"INSERT INTO result  \
            (run_id, scenario_id, timestamp, time, \
            pv_reward, solar_action, solar_available_power, solar_actionable_power, \
            grid_price, es_cost, es_reward, es_action, es_power_ask, \
            es_current_storage, es_solar_power_consumed, es_grid_power_consumed, \
            es_post_solar_power_available, es_post_grid_power_available, \
            es_post_es_power_available, ev_cost, ev_reward, ev_action, \
            ev_power_ask, ev_power_unserved, ev_charging_vehicle, ev_vehicle_charged, \
            ev_post_solar_power_available, ev_post_es_power_available, \
            ev_post_grid_power_available, ev_solar_power_consumed, \
            ev_es_power_consumed, ev_grid_power_consumed, oth_dev_cost, \
            oth_dev_reward, oth_dev_action, oth_dev_solar_power_consumed, \
            oth_dev_es_power_consumed, oth_dev_grid_power_consumed, oth_dev_power_ask, \
            oth_dev_post_solar_power_available, oth_dev_post_es_power_available, \
            oth_dev_post_grid_power_available, create_ts, source) VALUES \
            ('{run_id}','{scenario_id}','{timestamp}','{time}', \
            '{pv_reward}', '{solar_action}', '{solar_available_power}', '{solar_actionable_power}', \
            '{grid_price}', '{es_cost}', '{es_reward}', '{es_action}', '{es_power_ask}', \
            '{es_current_storage}', '{es_solar_power_consumed}', '{es_grid_power_consumed}', \
            '{es_post_solar_power_available}', '{es_post_grid_power_available}', \
            '{es_post_es_power_available}', '{ev_cost}', '{ev_reward}', '{ev_action}', \
            '{ev_power_ask}', '{ev_power_unserved}', '{ev_charging_vehicle}', '{ev_vehicle_charged}', \
            '{ev_post_solar_power_available}', '{ev_post_es_power_available}', \
            '{ev_post_grid_power_available}', '{ev_solar_power_consumed}', \
            '{ev_es_power_consumed}', '{ev_grid_power_consumed}', '{oth_dev_cost}', \
            '{oth_dev_reward}', '{oth_dev_action}', '{oth_dev_solar_power_consumed}', \
            '{oth_dev_es_power_consumed}', '{oth_dev_grid_power_consumed}', '{oth_dev_power_ask}', \
            '{oth_dev_post_solar_power_available}', '{oth_dev_post_es_power_available}', \
            '{oth_dev_post_grid_power_available}','{create_ts}', '{source}');COMMIT;"
        
        # Execute the query and insert
        cur2 = conn.cursor()
        cur2.execute(insert_result)
   
    return {"result": "inserted"}


# get costs
@app.get("/costs")
async def get_costs(scenario : str, source: str, interval : str):
    
    scenario = int(scenario)
    # Select max run_id for the scenario
    select_runid = f"SELECT MAX(run_id) FROM result WHERE scenario_id = '{scenario}' "
    
    # Execute the query and fetch the results
    cur1 = conn.cursor()
    cur1.execute(select_runid)
    run_id = cur1.fetchone()[0]

    # Cost grouping based on interval request

    if interval == "fivemins":
        # Execute query depending on source
        if source in {"naive","rule"}:
            # Execute the query and fetch the costs
            select_costs = f"SELECT  time::char(5), es_cost, ev_cost,oth_dev_cost  \
                FROM result WHERE scenario_id = '{scenario}' and source = '{source}' and run_id in (6,7)"
        elif source == "agent":
            select_costs = f"SELECT  time::char(5), es_cost, ev_cost,oth_dev_cost  \
                FROM result WHERE run_id = '{run_id}'"
        else:
            raise HTTPException (422, "source not recognized")

        # Execute the query and fetch the results
        cur2 = conn.cursor()
        cur2.execute(select_costs)
        costs = cur2.fetchall()

        
        # def json_serial(obj):
        #     """JSON serializer for objects not serializable by default json"""

        #     if isinstance(obj, (datetime, time)):
        #         return obj.isoformat()
        #     raise TypeError ("Type %s not serializable" % type(obj))

        # Format Costs
        # like {"costs":{{"time":"06:00"{"es_cost":0.256,"ev_cost": 0.351,"hv_cost":0.110,"totcost":xx},
        #               {"time":"06:05"{"es_cost":0.356,"ev_cost": 0.0,"hv_cost":0.110,"tot_cost":xx},...}}
        
        time = [i[0] for i in costs]
        es_cost = [i[1] for i in costs]
        ev_cost = [i[2] for i in costs]
        hv_cost = [i[3] for i in costs]
        tot_cost = [i[1]+i[2]+i[3] for i in costs]

        keys = ["time","es_cost","ev_cost","hv_cost","tot_cost"]
        items = [dict(zip(keys, [t, s, v, h, c])) for t, s, v, h, c in zip(time, es_cost, ev_cost , hv_cost, tot_cost)]
        
        #output = {"costs": json.dumps(costs, default=json_serial)}

    elif interval == "hour":
        # Execute query depending on source
        if source in {"naive","rule"}:
            # Execute the query and fetch the costs
            select_costs = f"SELECT  extract(hour from time) as time, sum (es_cost::float) as es_cost, sum(ev_cost::float) as ev_cost \
            , sum(oth_dev_cost::float) as oth_dev_cost FROM result WHERE scenario_id = '{scenario}' and source = '{source}' and run_id in (6,7) \
            group by extract(hour from time)"
        elif source == "agent":
            select_costs = f"SELECT  extract(hour from time) as time, sum (es_cost::float) as es_cost, sum(ev_cost::float) as ev_cost \
                , sum(oth_dev_cost::float) as oth_dev_cost FROM result WHERE run_id = '{run_id}' group by extract(hour from time)"
        else:
            raise HTTPException (422, "source not recognized")

        # Execute the query and fetch the results
        cur2 = conn.cursor()
        cur2.execute(select_costs)
        costs = cur2.fetchall()

        
        # def json_serial(obj):
        #     """JSON serializer for objects not serializable by default json"""

        #     if isinstance(obj, (datetime, time)):
        #         return obj.isoformat()
        #     raise TypeError ("Type %s not serializable" % type(obj))

        # Format Costs
        # like {"costs":{{"time":"06:00"{"es_cost":0.256,"ev_cost": 0.351,"hv_cost":0.110,"tot_cost":xx},
        #               {"time":"06:05"{"es_cost":0.356,"ev_cost": 0.0,"hv_cost":0.110,"tot_cost":xx},...}}
        
        time = [i[0] for i in costs]
        es_cost = [i[1] for i in costs]
        ev_cost = [i[2] for i in costs]
        hv_cost = [i[3] for i in costs]
        tot_cost = [i[1]+i[2]+i[3] for i in costs]

        keys = ["time","es_cost","ev_cost","hv_cost","tot_cost"]
        items = [dict(zip(keys, [t, s, v, h, c])) for t, s, v, h, c in zip(time, es_cost, ev_cost , hv_cost, tot_cost)]
        
        #output = {"costs": json.dumps(costs, default=json_serial)}
    
    # Format the results and return them through the API
    else:
            raise HTTPException (422, "interval not recognized")

    return {"costs": items }


    # get energy consumption
@app.get("/energy")
async def get_energy(scenario : str, source: str, interval : str):
    
    scenario = int(scenario)
    # Select max run_id for the scenario
    select_runid = f"SELECT MAX(run_id) FROM result WHERE scenario_id = '{scenario}' "
    
    # Execute the query and fetch the results
    cur1 = conn.cursor()
    cur1.execute(select_runid)
    run_id = cur1.fetchone()[0]

    # Energy grouping based on interval request

    if interval == "fivemins":
        # Execute query depending on source
        if source in {"naive","rule"}:
            # Execute the query and fetch the energy consumption
            select_energy = f"SELECT  time::char(5), (es_solar_power_consumed + es_grid_power_consumed) as batt,  \
                (ev_solar_power_consumed + ev_grid_power_consumed + ev_es_power_consumed) as ev, \
                (oth_dev_solar_power_consumed + oth_dev_es_power_consumed + oth_dev_grid_power_consumed) as hv \
                FROM result WHERE scenario_id = '{scenario}' and source = '{source}' and run_id in (6,7)"
        elif source == "agent":
            select_energy = f"SELECT  time::char(5), (es_solar_power_consumed + es_grid_power_consumed) as batt,  \
                (ev_solar_power_consumed + ev_grid_power_consumed + ev_es_power_consumed) as ev, \
                (oth_dev_solar_power_consumed + oth_dev_es_power_consumed + oth_dev_grid_power_consumed) as hv \
                FROM result WHERE run_id = '{run_id}'"
        else:
            raise HTTPException (422, "source not recognized")

        # Execute the query and fetch the results
        cur2 = conn.cursor()
        cur2.execute(select_energy)
        energy = cur2.fetchall()

        
        # def json_serial(obj):
        #     """JSON serializer for objects not serializable by default json"""

        #     if isinstance(obj, (datetime, time)):
        #         return obj.isoformat()
        #     raise TypeError ("Type %s not serializable" % type(obj))

        # Format Energy consumption
        # like {"energy":{{"time":"06:00"{"batt_ene":0.256,"ev_ene": 0.351,"hv_ene":0.110,"tot_ene":xx},
        #               {"time":"06:05"{"es_ene":0.356,"ev_ene": 0.0,"hv_ene":0.110,"tot_ene":xx},...}}
        
        time = [i[0] for i in energy]
        batt_ene = [i[1] for i in energy]
        ev_ene = [i[2] for i in energy]
        hv_ene = [i[3] for i in energy]
        tot_ene = [i[1]+i[2]+i[3] for i in energy]

        keys = ["time","batt_ene","ev_ene","hv_ene","tot_ene"]
        items = [dict(zip(keys, [t, s, v, h, c])) for t, s, v, h, c in zip(time, batt_ene, ev_ene , hv_ene, tot_ene)]
        
        #output = {"energy": json.dumps(energy, default=json_serial)}

    elif interval == "hour":
        # Execute query depending on source
        if source in {"naive","rule"}:
            # Execute the query and fetch the energy consumption
            select_energy = f"SELECT  extract(hour from time) as time, sum (es_solar_power_consumed + es_grid_power_consumed) as batt, \
                sum(ev_solar_power_consumed + ev_grid_power_consumed + ev_es_power_consumed) as ev, \
                sum(oth_dev_solar_power_consumed + oth_dev_es_power_consumed + oth_dev_grid_power_consumed) as hv \
                FROM result WHERE scenario_id = '{scenario}' and source = '{source}' and run_id in (6,7) \
                group by extract(hour from time)"
        elif source == "agent":
            select_energy = f"SELECT  extract(hour from time) as time, sum (es_solar_power_consumed + es_grid_power_consumed) as batt, \
                sum(ev_solar_power_consumed + ev_grid_power_consumed + ev_es_power_consumed) as ev, \
                sum(oth_dev_solar_power_consumed + oth_dev_es_power_consumed + oth_dev_grid_power_consumed) as hv \
                FROM result WHERE run_id = '{run_id}' \
                group by extract(hour from time)"
        else:
            raise HTTPException (422, "source not recognized")

        # Execute the query and fetch the results
        cur2 = conn.cursor()
        cur2.execute(select_energy)
        energy = cur2.fetchall()

        
        # def json_serial(obj):
        #     """JSON serializer for objects not serializable by default json"""

        #     if isinstance(obj, (datetime, time)):
        #         return obj.isoformat()
        #     raise TypeError ("Type %s not serializable" % type(obj))

        # Format energy consumption
        # like {"energy":{{"time":"06:00"{"batt_ene":0.256,"ev_ene": 0.351,"hv_ene":0.110,"tot_ene":xx},
        #               {"time":"06:05"{"es_ene":0.356,"ev_ene": 0.0,"hv_ene":0.110,"tot_ene":xx},...}}
        
        time = [i[0] for i in energy]
        batt_ene = [i[1] for i in energy]
        ev_ene = [i[2] for i in energy]
        hv_ene = [i[3] for i in energy]
        tot_ene = [i[1]+i[2]+i[3] for i in energy]

        keys = ["time","batt_ene","ev_ene","hv_ene","tot_ene"]
        items = [dict(zip(keys, [t, s, v, h, c])) for t, s, v, h, c in zip(time, batt_ene, ev_ene , hv_ene, tot_ene)]
        
        #output = {"energy": json.dumps(energy, default=json_serial)}
    
    # Format the results and return them through the API
    else:
            raise HTTPException (422, "interval not recognized")

    return {"energy_consumption": items }