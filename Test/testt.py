import os
import glob
import logging
import numpy as np
import pandas as pd
import psycopg2
from io import StringIO
from psycopg2 import sql


conn = psycopg2.connect(database='postgres', 
                        user='postgres', 
                        password='hxkj123..', 
                        host='10.185.104.228', 
                        port='5432')
cur = conn.cursor()
print(cur)


cur.close()
conn.close()