# -*- coding: utf-8 -*-
"""
Created on Mon May 13 11:14:42 2024

@author: EDY
"""
import os
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import transbigdata as tbd
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.patches import Rectangle
from Utils.config import cfg

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


def light_density(data1, start_lon, start_lat, end_lon, end_lat, resolution, point_list, save_path):
    #---------- 计算部分
    # tbd.set_mapboxtoken(cfg.INFO.MAPBOX_TOKEN)
    # tbd.set_imgsavepath(cfg.INFO.TILE_PATH)
    lonlat = np.array(point_list)
    lonlat = pd.DataFrame(lonlat)
    lonlat.columns = ['lon','lat']

    #-- 计算
    Lons = np.arange(start_lon, end_lon + resolution, resolution)
    Lats = np.arange(start_lat, end_lat + resolution, resolution)
    H_total, xedges, yedges = np.histogram2d(data1['Lon'], data1['Lat'], bins=(Lons, Lats))
    H_total = H_total.T
    lightning_grid = H_total / (resolution * 111 * resolution * 111 * len(data1.index.year.unique()))
    x, y = np.meshgrid(Lons[:-1], Lats[:-1])

    #-- 计算雷电流的平均值
    A_total = np.zeros_like(H_total)
    data_np = data1[['Lon', 'Lat', 'Lit_Current']].to_numpy()
    lon_idxs = np.digitize(data_np[:, 0], Lons) - 1
    lat_idxs = np.digitize(data_np[:, 1], Lats) - 1

    valid_idx = (lon_idxs >= 0) & (lon_idxs < H_total.shape[1]) & (lat_idxs >= 0) & (lat_idxs < H_total.shape[0])
    valid_lon_idxs = lon_idxs[valid_idx]
    valid_lat_idxs = lat_idxs[valid_idx]
    valid_currents = data_np[:, 2][valid_idx]
    A_total[valid_lat_idxs, valid_lon_idxs] += abs(valid_currents)
    # A_avg = np.where(H_total > 0, A_total / H_total, 0)

    #-- 画图
    levels = [0, 0.8, 2, 2.8, 5, 8, 11, 15, 100]
    colors = [[204, 204, 204], [60, 130, 255], [0, 255, 255], [255, 255, 0], [255, 170, 0], [255, 0, 255], [170, 0, 0], [100, 0, 0]]
    colors = [[r / 255.0, g / 255.0, b / 255.0, 0.7] for r, g, b in colors]

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    mesh = ax.contourf(x, y, lightning_grid, levels=levels, colors=colors, extend='both', transform=ccrs.PlateCarree())
    ax.scatter(lonlat['lon'], lonlat['lat'], c='red', s=40, marker='p', label='目标位置', transform=ccrs.PlateCarree())
    l2 = ax.legend()

    legend_patches = [Rectangle((0, 0), 1, 1, fc=color) for color in colors]
    legend_labels = ['0-0.8', '0.8-2', '2-2.8', '2.8-5', '5-8', '8-11', '11-15.5', '≥15.5']
    l1 = ax.legend([legend_patches[i] for i in range(len(legend_labels))], legend_labels, title="地闪密度（次平方千米每年）", loc="upper left", bbox_to_anchor=(1, 1), framealpha=0)
    g1 = ax.gridlines(draw_labels=True, linewidth=1, color='grey', alpha=0.4, linestyle='--', x_inline=False, y_inline=False)
    g1.top_labels = False
    g1.right_labels = False
    g1.xformatter = LONGITUDE_FORMATTER
    g1.yformatter = LATITUDE_FORMATTER
    g1.rotate_labels = False

    # 设置图表范围（根据需要调整）
    # bounds = [start_lon, start_lat, end_lon, end_lat]
    # tbd.plot_map(plt, bounds, zoom=12, style=2)
    ax.set_extent([start_lon, end_lon, start_lat, end_lat], crs=ccrs.PlateCarree())
    plt.gca().add_artist(l2)

    save_path_picture_p = os.path.join(save_path, '地闪密度.png')
    plt.savefig(save_path_picture_p, bbox_inches='tight', dpi=200)
    plt.cla()
    plt.close('all')

    # fig1 = plt.figure(figsize=(7, 5))
    # ax2 = fig1.add_subplot(111, projection=ccrs.PlateCarree())
    # mesh = ax2.contourf(x, y, A_avg, extend='both', transform=ccrs.PlateCarree())
    # cbar = plt.colorbar(mesh, ax=ax2, shrink=0.7)

    # g1 = ax2.gridlines(draw_labels=True, linewidth=1, color='none', alpha=0.5, linestyle='--', x_inline=False, y_inline=False)
    # g1.top_labels = False
    # g1.right_labels = False
    # g1.xformatter = LONGITUDE_FORMATTER
    # g1.yformatter = LATITUDE_FORMATTER
    # g1.rotate_labels = False

    # 设置图表范围（根据需要调整）
    # bounds = [start_lon, start_lat, end_lon, end_lat]
    # tbd.plot_map(plt, bounds, zoom=7, style=2)
    # ax2.set_extent([start_lon, end_lon, start_lat, end_lat], crs=ccrs.PlateCarree())

    # save_path_picture_l = os.path.join(save_path, '雷电流.png')
    # plt.savefig(save_path_picture_l, bbox_inches='tight', dpi=200)
    # plt.cla()
    # plt.close('all')

    return save_path_picture_p#, save_path_picture_l


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
    resolution = 0.005
    path = r'C:/Users/MJY/Desktop/adtd.csv'
    df = pd.read_csv(path)
    df = adtd_data_proccessing(df)
    point_list = [[101.25,37.02],[101.349,37.31]]
    save_path = r'C:/Users/MJY/Desktop/adtd'
    light_density_picture = light_density(df, start_lon, start_lat, end_lon, end_lat, resolution, point_list, save_path)
