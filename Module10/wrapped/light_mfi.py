# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 09:46:26 2024

@author: EDY
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.patches import Rectangle
import math
import matplotlib
import transbigdata as tbd
from Utils.config import cfg

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def light_mfi(data1, start_lon, start_lat, end_lon, end_lat, point_list, save_path):
    #---------- 计算部分
    # tbd.set_mapboxtoken(cfg.INFO.MAPBOX_TOKEN)
    # tbd.set_imgsavepath(cfg.INFO.TILE_PATH)

    #--- 计算
    def sample(x):
        x = x.to_frame().T
        # 计算距离
        lon1 = x['lon'].values
        lat1 = x['lat'].values
        lon2 = data1['Lon'].values
        lat2 = data1['Lat'].values
        dlat = (lat2 - lat1)**2
        dlon = (lon2 - lon1)**2
        distance = (np.sqrt(dlat+dlon))*111000
        # 计算电磁强度
        H = (data1['Lit_Current'].abs().values*1000)/(np.pi*2*distance)
        H = H.max().round(3)
        return H
    
    lonlat = np.array(point_list)
    lonlat = pd.DataFrame(lonlat)
    lonlat.columns = ['lon','lat']
    lonlat['value'] = lonlat.apply(sample,axis=1)
        
    #-- 画图
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    contourf_obj = ax.scatter(lonlat['lon'], lonlat['lat'], c=lonlat['value'], cmap='rainbow', label='目标位置', transform=ccrs.PlateCarree())
    l2 = ax.legend()
    cb = fig.colorbar(contourf_obj, ax=ax, shrink=0.95)
    g1 = ax.gridlines(draw_labels=True, linewidth=1, color='grey', alpha=0.4, linestyle='--', x_inline=False, y_inline=False)
    g1.top_labels = False
    g1.right_labels = False
    g1.xformatter = LONGITUDE_FORMATTER
    g1.yformatter = LATITUDE_FORMATTER
    g1.rotate_labels = False

    # 设置图表范围（根据需要调整）
    # bounds = [start_lon, start_lat, end_lon, end_lat]
    # tbd.plot_map(plt, bounds, zoom=9, style=2)
    ax.set_extent([start_lon, end_lon, start_lat, end_lat], crs=ccrs.PlateCarree())

    save_path_picture_p = os.path.join(save_path, '最大电磁场强度分布图.png')
    plt.savefig(save_path_picture_p, bbox_inches='tight', dpi=200)
    plt.cla()
    plt.close('all')
    
    lonlat.columns = ['经度','纬度','电磁强度']
    
    return lonlat, save_path_picture_p


if __name__ == '__main__':
    
    def adtd_data_proccessing(data):
        data = data[data['Lit_Prov'] == '青海省']
        data = data[['Lat', 'Lon', 'Year', 'Mon', 'Day', 'Hour', 'Min', 'Second', 'Lit_Current']]
        time = {"Year": data["Year"], "Month": data["Mon"], "Day": data["Day"], "Hour": data["Hour"], "Minute": data["Min"], "Second": data["Second"]}
        data['Datetime'] = pd.to_datetime(time)
        data.set_index('Datetime', inplace=True)
        data.sort_index(inplace=True)
    
        if 'Unnamed: 0' in data.columns:
            data.drop(['Unnamed: 0'], axis=1, inplace=True)
    
        return data
    
    start_lon = 100.8
    end_lon = 101.9
    start_lat = 36.2
    end_lat = 37.5
    path = r'C:/Users/MJY/Desktop/adtd.csv'
    df = pd.read_csv(path)
    df = adtd_data_proccessing(df)
    point_list = [[101.25,37.02],[101.349,36.81]]
    save_path = r'C:/Users/MJY/Desktop/adtd'
    lonlat, save_path_picture_p = light_mfi(df, start_lon, start_lat, end_lon, end_lat, point_list, save_path)

