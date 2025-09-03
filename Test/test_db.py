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
                        password='2023p+yuiL34gf+hx+##!!', 
                        host='192.168.1.122', 
                        port='5432')
print("数据库连接成功！")
print(f"连接信息: 主机={conn.get_dsn_parameters()['host']}, 数据库={conn.get_dsn_parameters()['dbname']}")
cur = conn.cursor()
print(f"游标创建成功: {cur}")


cur.close()
conn.close()