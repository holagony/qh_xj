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
import xarray as xr

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
        
        # 过滤掉无效数据
        valid_mask = (~np.isnan(data1['Lit_Current'].values)) & (distance > 0)
        if not valid_mask.any():
            return 0.0  # 如果没有有效数据，返回0
        
        # 计算电磁强度
        valid_current = data1['Lit_Current'].values[valid_mask]
        valid_distance = distance[valid_mask]
        H = (np.abs(valid_current)*1000)/(np.pi*2*valid_distance)
        H = H.max().round(3)
        return H
    
    lonlat = np.array(point_list)
    lonlat = pd.DataFrame(lonlat)
    lonlat.columns = ['lon','lat']
    lonlat['value'] = lonlat.apply(sample,axis=1)
        
    #-- 画图
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    
    # 加载DEM数据作为背景
    try:
        dem_file = cfg.FILES.XJ_DEM
        dem_data = xr.open_dataset(dem_file)
        
        # 提取DEM数据
        dem_lon = dem_data['lon'].values
        dem_lat = dem_data['lat'].values
        dem_elevation = dem_data['dem'].values
        
        # 创建DEM背景图（不添加colorbar）
        dem_contour = ax.contourf(dem_lon, dem_lat, dem_elevation, 
                                  levels=50, cmap='terrain', alpha=0.7, 
                                  transform=ccrs.PlateCarree(), add_colorbar=False)
        
        dem_data.close()
    except Exception as e:
        print(f"警告：无法加载DEM数据: {e}")
    
    # 绘制电磁强度散点图
    contourf_obj = ax.scatter(lonlat['lon'], lonlat['lat'], c=lonlat['value'], 
                             cmap='rainbow', label='目标位置', s=100, 
                             edgecolors='black', linewidth=0.5,
                             transform=ccrs.PlateCarree())
    
    l2 = ax.legend()
     
    # 创建电磁强度的colorbar，显示分级变化
    cb = fig.colorbar(contourf_obj, ax=ax, shrink=0.8, label='电磁强度')
    cb.set_label('电磁强度', rotation=270, labelpad=15)
    
    g1 = ax.gridlines(draw_labels=True, linewidth=1, color='grey', alpha=0.4, linestyle='--', x_inline=False, y_inline=False)
    g1.top_labels = False
    g1.right_labels = False
    g1.xformatter = LONGITUDE_FORMATTER
    g1.yformatter = LATITUDE_FORMATTER
    g1.rotate_labels = False

    # 设置图表范围
    ax.set_extent([start_lon, end_lon, start_lat, end_lat], crs=ccrs.PlateCarree())
    
    # 添加标题
    ax.set_title('目标位置电磁场强度分布', fontsize=12, pad=10)

    save_path_picture_p = os.path.join(save_path, '最大电磁场强度分布图.png')
    plt.savefig(save_path_picture_p, bbox_inches='tight', dpi=200)
    plt.cla()
    plt.close('all')
    
    lonlat.columns = ['经度','纬度','电磁强度']
    
    return lonlat, save_path_picture_p


if __name__ == '__main__':
    
    def adtd_data_proccessing(data, years):
        data['Datetime'] = pd.to_datetime(data['Datetime'])
        data.set_index('Datetime', inplace=True)
        data.sort_index(inplace=True)
        data['Lon'] = data['Lon'].astype(float)
        data['Lat'] = data['Lat'].astype(float)
        data.rename(columns={'强度': 'Lit_Current'}, inplace=True)
        data['Year'] = data.index.year
        data['Mon'] = data.index.month
        data['Day'] = data.index.day

        start_year = years.split(',')[0]
        end_year = years.split(',')[1]
        data = data[data.index.year >= int(start_year)]
        data = data[data.index.year <= int(end_year)]

        if 'Unnamed: 0' in data.columns:
            data.drop(['Unnamed: 0'], axis=1, inplace=True)
        
        return data

    adtd_df = pd.read_csv(cfg.FILES.ADTD)
    adtd_df = adtd_data_proccessing(adtd_df, '2000,2025')

    point_list = [[87,43]]
    save_path = r'C:/Users/MJY/Desktop/adtd'
    lonlat, save_path_picture_p = light_mfi(adtd_df, start_lon=86.37, start_lat=42.75, end_lon=88.58, end_lat=44.08, point_list=point_list, save_path=r'C:\Users\mjynj\Desktop\aaa')

