import logging
import uuid
import os
import json
import simplejson
import numpy as np
import pandas as pd
from datetime import timedelta
from flask import Blueprint, request, jsonify
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_loader_with_threads import get_cmadaas_radi_data, get_cmadaas_daily_data
from Utils.get_local_data import get_local_data
from Utils.data_processing import daily_data_processing
from Module12.wrapped.radiation_stats import radiation_stats
from Utils.get_url_path import save_cmadaas_data


def radi_data_processing(df):
    '''
    辐射数据处理
    '''
    try:
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df.set_index('Datetime', inplace=True)
    except:
        pass
    
    df['Year'] = df.index.year
    df['Mon'] = df.index.month
    df['Day'] = df.index.day
    df['Hour'] = df.index.hour
    df['Station_Id_C'] = df['Station_Id_C'].astype(str)
    df['Year'] = df['Year'].map(int)
    df['Mon'] = df['Mon'].map(int)
    df['Day'] = df['Day'].map(int)
    df['Hour'] = df['Hour'].map(int)
    df['Lon'] = df['Lon'].astype(float)
    df['Lat'] = df['Lat'].astype(float)
    df['V14311'] = df['V14311'].apply(lambda x: np.nan if x > 999 else x)
    df.rename(columns={'V14311': '总辐射'}, inplace=True)

    return df


def radiation_handler(data_json):
    '''
    辐射统计接口
    '''
    json_str = request.get_data(as_text=True)  # 获取JSON字符串

    if json_str:
        code = 200
        msg = '获取数据成功'

        # 读取json中的信息
        data_json = json.loads(json_str)
        sta_ids = data_json['sta_ids']
        years = data_json['years']
        param_a = data_json['param_a']
        param_b = data_json['param_b']
        divide_flag = data_json['divide_flag']

        uuid4 = uuid.uuid4().hex
        data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            os.chmod(data_dir, 0o007 | 0o070 | 0o700)

        if isinstance(sta_ids, list):
            sta_ids = [str(ids) for ids in sta_ids]
            sta_ids = ','.join(sta_ids)
        if isinstance(sta_ids, int):
            sta_ids = str(sta_ids)

        # 下载数据
        # 首先下载气象站日数据
        daily_elements = 'SSH'
        hourly_elements = 'V14311'

        if cfg.INFO.READ_LOCAL:
            day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements).split(',')
            daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
            daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')

            if sta_ids in ['52866', '56029', '52863', '52754', '52818', '52874', '56043', '56065']:
                radi_df = pd.read_csv(cfg.FILES.QH_DATA_RADI)
                radi_df = radi_data_processing(radi_df)
                radi_df = radi_df[radi_df['Station_Id_C']==sta_ids]
                sp_years = years.split(',')
                radi_df = radi_df[(radi_df.index.year >= int(sp_years[0])) & (radi_df.index.year <= int(sp_years[1]))]
            else:
                radi_df = None

        else:
            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids) # 站点数据下载
            daily_df = daily_data_processing(daily_df, years)

            if sta_ids in ['51058', '51076', '51133', '51358', '51431', '51463', '51567', '51573', '51628', '51709', '51777', '51828', '52203']:
                years_split = years.split(',')
                num_years = int(years_split[1]) - int(years_split[0]) + 1
                start_date = years_split[0] + '010100000'
                radi_df = get_cmadaas_radi_data(start_date, num_years, hourly_elements, sta_ids)
                radi_df = radi_data_processing(radi_df)
            else:
                radi_df = None

        # 生成结果
        try:
            result_dict = radiation_stats(daily_df, radi_df, sta_ids, param_a, param_b, divide_flag)
            result_dict['uuid'] = uuid4
            # 7.结果保存
            if cfg.INFO.SAVE_RESULT:
                result_dict['csv'] = save_cmadaas_data(data_dir, day_data=daily_df, radi_data=radi_df)
        except Exception:
            raise Exception('无法在数据库中检索到自建站数据，请检查和记录选取的站号、时间和要素，进行反馈排查')

    else:
        code = 500
        msg = '获取数据失败'
        result_dict = None

    # 转成JSON字符串
    return_data = simplejson.dumps({'code': code, 'msg': msg, 'data': result_dict}, ensure_ascii=False, ignore_nan=True)

    return return_data


if __name__ == '__main__':
    d = {'code': None, 'msg': '中文'}
    # '{"code": null, "msg": "\\u4e2d\\u6587"}'
    # a = simplejson.dumps(d)

    # '{"code": null, "msg": "中文"}'
    # a = simplejson.dumps(d, ensure_ascii=False)

    # '{"code": null, "msg": "中文"}'
    a = simplejson.dumps(d, ensure_ascii=False, ignore_nan=True)
    print(a)
