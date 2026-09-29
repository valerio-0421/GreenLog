import os
import mysql.connector


conn = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    user=os.environ["DB_USER"],
    root=os.environ["DB_ROOT"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"]
)
cursor = conn.cursor()

q = """SELECT t.make, t.model_year, t.fuel_type, AVG(tu.average_l_100km)
    FROM trucks t 
    JOIN truck_utilization_metrics tu 
    ON t.truck_id = tu.truck_id
    GROUP BY t.make, t.model_year, t.fuel_type"""