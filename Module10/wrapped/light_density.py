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
    # 计算年数，避免除零错误
    num_years = len(data1.index.year.unique())
    if num_years == 0:
        num_years = 1
    
    lightning_grid = H_total / (resolution * 111 * resolution * 111 * num_years)
    x, y = np.meshgrid(Lons[:-1], Lats[:-1])
    
    # 调试信息（可选）
    # print(f"Lightning grid stats: min={lightning_grid.min():.6f}, max={lightning_grid.max():.6f}, mean={lightning_grid.mean():.6f}")
    # print(f"Non-zero values: {np.count_nonzero(lightning_grid)}")
    # print(f"Total grid points: {lightning_grid.size}")

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
    # 根据实际数据范围动态设置色标
    data_max = lightning_grid.max()
    data_min = lightning_grid.min()
    
    if data_max > 0:
        # 如果有数据，使用动态levels
        if data_max <= 1:
            levels = [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9]
            if data_max > 0.9:
                levels.append(data_max)
            else:
                levels = [l for l in levels if l <= data_max] + [data_max]
        elif data_max <= 10:
            levels = [0, 0.8, 2, 2.8, 5, 8]
            if data_max > 8:
                levels.append(data_max)
            else:
                levels = [l for l in levels if l <= data_max] + [data_max]
        else:
            levels = [0, 0.8, 2, 2.8, 5, 8, 11, 15]
            if data_max > 15:
                levels.append(data_max)
            else:
                levels = [l for l in levels if l <= data_max] + [data_max]
        
        # 确保levels严格递增且去重
        levels = sorted(list(set(levels)))
        # 如果只有一个level，添加一个稍大的值
        if len(levels) <= 1:
            levels = [0, max(data_max, 0.1)]
    else:
        # 如果没有数据，使用默认levels
        levels = [0, 0.8, 2, 2.8, 5, 8, 11, 15, 100]
    
    colors = [[204, 204, 204], [60, 130, 255], [0, 255, 255], [255, 255, 0], [255, 170, 0], [255, 0, 255], [170, 0, 0], [100, 0, 0]]
    # 确保颜色数量与levels匹配
    colors = colors[:len(levels)-1]
    colors = [[r / 255.0, g / 255.0, b / 255.0, 0.7] for r, g, b in colors]
    
    # print(f"Using levels: {levels}")
    # print(f"Using {len(colors)} colors")

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    mesh = ax.contourf(x, y, lightning_grid, levels=levels, colors=colors, extend='both', transform=ccrs.PlateCarree())
    ax.scatter(lonlat['lon'], lonlat['lat'], c='red', s=40, marker='p', label='目标位置', transform=ccrs.PlateCarree())
    l2 = ax.legend()

    legend_patches = [Rectangle((0, 0), 1, 1, fc=color) for color in colors]
    # 动态生成图例标签
    legend_labels = []
    for i in range(len(levels)-1):
        if i == len(levels)-2:
            legend_labels.append(f'≥{levels[i]}')
        else:
            legend_labels.append(f'{levels[i]}-{levels[i+1]}')
    
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
    light_density_picture = light_density(adtd_df, start_lon=73, start_lat=34, end_lon=96, end_lat=49, point_list=point_list, resolution=0.005, save_path=r'C:\Users\mjynj\Desktop\aaa')
