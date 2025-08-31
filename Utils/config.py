import os
from Utils.ordered_easydict import OrderedEasyDict as edict

# 基础路径
os.environ['PROJ_LIB'] = '/home/user/miniconda3/envs/myconda/share/proj'
basedir = os.path.abspath(os.path.dirname(__file__))
current_file = os.path.abspath(__file__)  # 获取当前文件的绝对路径
current_dir = os.path.dirname(current_file)  # 获取当前文件所在目录
current_obj = os.path.dirname(current_dir)  # 获取当前文件所在项目
data_file_dir = os.path.join(current_obj, 'Files')

# 生成字典
__C = edict()
cfg = __C
flag = 'QH'

# 信息配置
__C.INFO = edict()
__C.INFO.NUM_THREADS = 30  # 多线程数量
__C.INFO.MAPBOX_TOKEN = 'pk.eyJ1IjoiZGFpbXUiLCJhIjoiY2x3MWV6Y3YxMDF5aDJxcWI2c3c3eWh4dSJ9.DWzNsJKgNetnDZi4ZKV2Yg'

if flag == 'HX': # 公司服务器
    __C.INFO.IN_UPLOAD_FILE = '/zipdata' # 上传数据路径
    __C.INFO.OUT_UPLOAD_FILE = '/mnt/PRESKY/project/bgdb/qihou/zipdata'
    __C.INFO.IN_DATA_DIR = '/data' # 容器内保存文件夹
    __C.INFO.OUT_DATA_DIR = '/home/bgdb/dockercp/qhkxxlz/data' # 容器外挂载保存文件夹
    __C.INFO.OUT_DATA_URL = 'http://1.119.169.101:10036/img'
    __C.INFO.REDIS_HOST = '192.168.1.119'
    __C.INFO.REDIS_PORT = '8086'
    __C.INFO.REDIS_PWD = 'hC%34okFq&'
    __C.INFO.DB_USER = 'postgres'
    __C.INFO.DB_PWD = '2023p+yuiL34gf+hx+##!!'
    __C.INFO.DB_HOST = '192.168.1.122' # 内网
    __C.INFO.DB_PORT = '5432'
    __C.INFO.DB_NAME = 'postgres'
    __C.INFO.SCHEMA_NAME = 'public'
    __C.INFO.READ_LOCAL = True
    __C.INFO.SAVE_RESULT = False
    __C.INFO.TILE_PATH = os.path.join(data_file_dir, 'mapbox_tile/')

elif flag == 'LOCAL': # 自己电脑
    __C.INFO.IN_UPLOAD_FILE = 'C:/Users/MJY/Desktop/qhkxxlz/zipdata'  # 上传数据路径
    __C.INFO.OUT_UPLOAD_FILE = 'C:/Users/MJY/Desktop/qhkxxlz/zipdata'
    __C.INFO.IN_DATA_DIR = '/data'  # 容器内保存文件夹
    __C.INFO.OUT_DATA_DIR = 'C:/Users/MJY/Desktop/qhkxxlz/data'  # 容器外挂载保存文件夹
    __C.INFO.OUT_DATA_URL = 'http://1.119.169.101:10036/img'
    __C.INFO.REDIS_HOST = '172.17.0.2'
    __C.INFO.REDIS_PORT = '6379'
    __C.INFO.REDIS_PWD = ''
    __C.INFO.DB_USER = 'postgres'
    __C.INFO.DB_PWD = '2023p+yuiL34gf+hx+##!!'
    __C.INFO.DB_HOST = '1.119.169.101'
    __C.INFO.DB_PORT = '10089'
    __C.INFO.DB_NAME = 'postgres'
    __C.INFO.SCHEMA_NAME = 'public'
    __C.INFO.READ_LOCAL = True
    __C.INFO.SAVE_RESULT = False
    __C.INFO.TILE_PATH = os.path.join(data_file_dir, 'mapbox_tile\\')

elif flag == 'QH': # 青海服务器 XJ
    __C.INFO.IN_UPLOAD_FILE = '/zipdata'
    __C.INFO.OUT_UPLOAD_FILE = 'E:/hxkj/xinjiang/zipdata'
    __C.INFO.IN_DATA_DIR = '/data' # 容器内保存文件夹
    __C.INFO.OUT_DATA_DIR = 'E:/hxkj/xinjiang/data' # 容器外挂载保存文件夹
    __C.INFO.OUT_DATA_URL = 'http://10.185.104.228/img'
    __C.INFO.REDIS_HOST = '10.185.104.228' # docker machine ip 192.168.99.100
    __C.INFO.REDIS_PORT = '6379'
    __C.INFO.REDIS_PWD = 'xjqxfwzx890*()' # 'hC%34okFq&'
    __C.INFO.DB_USER = 'postgres'
    __C.INFO.DB_PWD = 'hxkj123..'
    __C.INFO.DB_HOST = '10.185.104.228'
    __C.INFO.DB_PORT = '5432'
    __C.INFO.DB_NAME = 'postgres'
    __C.INFO.SCHEMA_NAME = 'public'
    __C.INFO.READ_LOCAL = False
    __C.INFO.SAVE_RESULT = False
    __C.INFO.TILE_PATH = os.path.join(data_file_dir, 'mapbox_tile\\') # 容器内地址

# 静态文件路径
__C.FILES = edict()
__C.FILES.FONT = os.path.join(data_file_dir, 'fonts/simhei.ttf')
__C.FILES.T_DISTR_TABLE = os.path.join(data_file_dir, 't_distribution_table.csv')
__C.FILES.ELEMENT_CH = os.path.join(data_file_dir, 'element_ch.csv')

# 样例数据路径
__C.FILES.QH_DATA_HOUR = os.path.join(data_file_dir, 'test_data/qh_hour.csv')
__C.FILES.QH_DATA_DAY = os.path.join(data_file_dir, 'test_data/qh_day.csv')
__C.FILES.QH_DATA_MONTH = os.path.join(data_file_dir, 'test_data/qh_mon.csv')
__C.FILES.QH_DATA_YEAR = os.path.join(data_file_dir, 'test_data/qh_year.csv')
__C.FILES.QH_DATA_RADI = os.path.join(data_file_dir, 'test_data/qh_radi.csv')
__C.FILES.WIND_TOWER = os.path.join(data_file_dir, 'test_data/格尔木风冷')
__C.FILES.PRE_MIN = os.path.join(data_file_dir, 'test_data/rain_min')
__C.FILES.ADTD = os.path.join(data_file_dir, 'adtd.csv')
__C.FILES.ADTD_PARAM = os.path.join(data_file_dir, 'adtd_parameters.csv')
__C.FILES.ADTD_FACTOR = os.path.join(data_file_dir, 'adtd_factors.npy')

# report
__C['report'] = dict()
__C['report']['picture'] = os.path.join(current_obj, 'Report', 'picture')
__C['report']['template'] = os.path.join(current_obj, 'Report', 'template')
__C['report']['report'] = os.path.join(current_obj, 'Report', 'report')
