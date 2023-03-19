from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel, validator, constr 
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from typing import Optional

import joblib
import os
import numpy as np
import boto3
import psycopg2
#import json

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
    insert_device = f"INSERT INTO device (device_name,status,device_type) VALUES \
        ('{device_name}','{status}','{device_type}');COMMIT;"
    
    # Execute the query and insert
    cur = conn.cursor()
    cur.execute(insert_device)
   
    return {"device": "inserted"}

# insert a new device
@app.post("/upd_device")
async def new_device(input : upd_device):
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
