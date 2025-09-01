import os
import glob
import logging
import numpy as np
import pandas as pd
import psycopg2
from io import StringIO
from psycopg2 import sql
from sqlalchemy import create_engine
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader import get_connection
from Utils.my_server import get_server_sshtunnel


def wind_tower_upload(paths, sta_id, lon=None, lat=None):
    '''
    读取测风塔数据文件夹，处理数据，入库
    paths: 测风塔数据文件夹，格式为样例数据形式
    sta_id: 定义的站名/站号
    lon: 定义的经度
    lat: 定义的纬度
    '''
    if lon is None:
        lon = np.nan
    if lat is None:
        lat = np.nan

    total_path = glob.glob(os.path.join(paths, '*.xls'))
    df_all = []
    for path in total_path:
        df = pd.read_excel(path, header=2)
        df = df.iloc[3:,:-4]
        df_all.append(df)
            
    df_trans = pd.concat(df_all, axis=0)
    df_trans['时间'] = pd.to_datetime(df_trans['时间'], format='%Y-%m-%d %H:%M')
    df_trans.set_index('时间', inplace=True)

    df_trans['datetime'] = df_trans.index
    df_trans = pd.melt(df_trans, id_vars=['datetime'], var_name='高度层', value_name='数值')
    df_trans = df_trans.set_index(['datetime', '数值'])['高度层'].str.split('层', expand=True).reset_index()
    df_trans = df_trans.set_index(['datetime', 0, 1]).unstack()
    df_trans.columns = df_trans.columns.droplevel(0)
    df_trans = df_trans.rename_axis(columns=None).reset_index()
    df_trans.columns = ['datetime', '高度层', '10分风向', '10分风速']

    # 将中文数字转换为阿拉伯数字
    def chinese_to_number(text):
        chinese_num_map = {'第一': 1, '第二': 2, '第三': 3, '第四': 4, '第五': 5,
                        '第六': 6, '第七': 7, '第八': 8, '第九': 9, '第十': 10,
                        '第十一': 11, '第十二': 12, '第十三': 13, '第十四': 14, '第十五': 15}
        return chinese_num_map[text]

    df_trans['高度层'] = df_trans['高度层'].apply(chinese_to_number)
    df_trans['station_id'] = sta_id
    df_trans['lon'] = lon
    df_trans['lat'] = lat
    df_trans['对应高度'] = np.nan
    df_trans['datetime'] = df_trans['datetime'].dt.strftime('%Y%m%d%H%M%S')
    df_trans['2分风向'] = np.nan
    df_trans['2分风速'] = np.nan
    df_trans['最大风向'] = np.nan
    df_trans['最大风速'] = np.nan
    df_trans['极大风向'] = np.nan
    df_trans['极大风速'] = np.nan
    df_trans['瞬时风向'] = np.nan
    df_trans['瞬时风速'] = np.nan
    df_trans = df_trans[['station_id', 'lon', 'lat', 'datetime', '高度层', '对应高度', '10分风向', '10分风速', '2分风向', '2分风速', '最大风向', '最大风速', '极大风向', '极大风速', '瞬时风向', '瞬时风速']]

    # 数据处理后入库
    try:
        conn = psycopg2.connect(database=cfg.INFO.DB_NAME, user=cfg.INFO.DB_USER, password=cfg.INFO.DB_PWD, host=cfg.INFO.DB_HOST, port=cfg.INFO.DB_PORT)
        cur = conn.cursor()
        f1 = StringIO()
        df_trans.to_csv(f1, sep='\t', index=False, header=False)
        f1.seek(0)
        cur.copy_from(file=f1,
                      table='qhkxxlz_wind_tower',
                      null='',
                      columns=('station_id', 'lon', 'lat', 'datetime', 'height_level', 'height', 'wd_10min', 'ws_10min', 'wd_2min', 'ws_2min', 'wd_max', 'ws_max', 'wd_inst_max', 'ws_inst_max', 'wd_inst', 'ws_inst'))
        conn.commit()
        cur.close()
        conn.close()
        print('入库finished')
    except Exception as e:
        logging.exception(e)
        raise Exception('入库error')

    # return df_all, df_trans


def set_data_heights(sta_id, cur_val, new_val):
    '''
    修改数据库测风塔数据的高度值
    一次只能改一个高度
    cur_val = "5"
    new_val = "NUll"
    '''
    new_val = None if new_val == 'NUll' else int(new_val)

    conn = psycopg2.connect(database=cfg.INFO.DB_NAME, user=cfg.INFO.DB_USER, password=cfg.INFO.DB_PWD, host=cfg.INFO.DB_HOST, port=cfg.INFO.DB_PORT)
    cur = conn.cursor()
    query = sql.SQL("UPDATE public.qhkxxlz_wind_tower SET height = %s WHERE height_level = %s AND station_id = %s")
    cur.execute(query, (new_val, cur_val, sta_id))
    conn.commit()
    cur.close()
    conn.close()
    print('更新成功')


def get_data_postgresql(sta_id, time_range):
    '''
    从数据库读取上传的测风塔数据，可以读取多个站
    time_range: '20230801,20240630'
    '''
    times = time_range.split(',')
    start = times[0] + '000000'
    end = times[1] + '235959'

    if isinstance(sta_id, str):
        sta_id = [sta_id]
    sta_id = tuple(sta_id)

    # 读取
    conn = psycopg2.connect(database=cfg.INFO.DB_NAME, user=cfg.INFO.DB_USER, password=cfg.INFO.DB_PWD, host=cfg.INFO.DB_HOST, port=cfg.INFO.DB_PORT)
    cur = conn.cursor()
    query = sql.SQL("SELECT DISTINCT * From public.qhkxxlz_wind_tower WHERE station_id in %s AND datetime >= %s AND datetime <= %s")
    cur.execute(query, (sta_id, start, end))
    data = cur.fetchall()
    df = pd.DataFrame(data)
    df.columns = ['station_id', 'lon', 'lat', 'datetime', '高度层', '对应高度', '10分风向', '10分风速', '2分风向', '2分风速', '最大风向', '最大风速', '极大风向', '极大风速', '瞬时风向', '瞬时风速']
    df = df[['station_id', 'datetime', '对应高度', '10分风向', '10分风速', '最大风速', '极大风速']]
    # df = df.drop_duplicates()
    cur.close()
    conn.close()

    return df


def wind_tower_processing(df):
    '''
    处理从数据库读取的测风塔数据
    增加：删除高度为NULL(nan)的行
    '''
    after_process = edict()
    df_stations = df['station_id'].unique().tolist()

    for sta in df_stations:
        after_process[sta] = edict()
        sub_df = df[df['station_id'] == sta]
        sub_df.drop(columns=['station_id'], inplace=True)
        sub_df = sub_df[~sub_df['对应高度'].isna()]

        # 根据高度修改列名
        for i, group in enumerate(list(sub_df.groupby('对应高度'))):
            h = int(group[0])
            h = str(h)
            group_df = group[1]
            group_df.drop(columns=['对应高度'], inplace=True)
            group_df = group_df.rename(columns={'10分风向': h + 'm_hour_wd', '10分风速': h + 'm_hour_ws', '最大风速': h + 'm_ws_max', '极大风速': h + 'm_ws_inst_max'})

            if i == 0:
                wind = group_df
            else:
                wind = pd.merge(wind, group_df, on=['datetime'])

        wind['datetime'] = pd.to_datetime(wind['datetime'], format='%Y%m%d%H%M%S')
        wind.set_index('datetime', inplace=True)
        wind.sort_index(inplace=True)

        # df数据列拆分和列重命名
        ws_10 = wind.filter(like='hour_ws')
        wd_10 = wind.filter(like='hour_wd')
        ws_max = wind.filter(like='ws_max')
        ws_max_inst = wind.filter(like='ws_inst_max')

        after_process[sta].ws_10 = ws_10.resample('1H').mean()
        after_process[sta].wd_10 = wd_10.resample('1H').mean()
        after_process[sta].ws_max = ws_max.resample('1H').max()
        after_process[sta].ws_max_inst = ws_max_inst.resample('1H').max()

        return after_process


if __name__ == '__main__':
    path = r'C:\Users\mjynj\Desktop\dacheng\dacheng'
    wind_tower_upload(paths=path, sta_id='XJ_dabancheng') # 上传
    
    # In[] 修改高度
    set_data_heights(cur_val="4", new_val='100', sta_id='XJ_dabancheng') # 更新数据库里面的高度
    
    # In[] # 数据库获取
    df = get_data_postgresql(sta_id='XJ_dabancheng', time_range='20220701,20230731')
    after_process = wind_tower_processing(df)  # 获取后处理
