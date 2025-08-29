# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 14:01:23 2024

@author: EDY

雷电灾害风险区划

静态数据网格数：557，335
"""
import pandas as pd
from Utils.config import cfg
import numpy as np
from Module10.wrapped.Calc import calc_intensity_and_density
import jenkspy
import transbigdata as tbd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from matplotlib.patches import Rectangle
import os

plt.rcParams['font.sans-serif'] = ['SimHei']  
plt.rcParams['axes.unicode_minus'] = False  
#%% 计算部分
def get_regional_risk(data,weights,start_lon,end_lon,start_lat,end_lat,data_dir):
    
   
    #顺序Conductivity_norm,DEM_norm,Topography_norm,Human_density_norm,GDP_norm,Life_loss_idx,Economy_loss_idx,Land_type_norm
    factors_path =cfg.FILES.ADTD_FACTOR
    factors = np.load(factors_path)

    # 进行一次范围选择
    lon = np.linspace(89, 104, 557)  
    lat = np.linspace(31, 40, 335)  
    lat = np.flipud(lat)              

    # 找出在给定范围内的经度和纬度的索引
    lon_indices = np.where((lon >= start_lon) & (lon <= end_lon))[0]
    lat_indices = np.where((lat >= start_lat) & (lat <= end_lat))[0]

    lon_m=lon[np.append(lon_indices,lon_indices[-1]+1)]+0.027/2
    lat_m=lat[np.append(lat_indices,lat_indices[-1]+1)]+0.027/2

    calc = calc_intensity_and_density(start_lon, start_lat, end_lon, end_lat,lon_m,lat_m)
    lightning_intensity, lightning_density = calc.run(data)

    factors=factors[:,lat_indices[0]:lat_indices[-1]+1:,lon_indices[0]:lon_indices[-1]+1:]
    RH = (lightning_density*weights['wd'] + lightning_intensity*weights['wn']) * (factors[0]*weights['ws'] + factors[1]*weights['we'] + factors[2]*weights['wt'])
    RE = factors[3]*weights['wp'] + factors[4]*weights['wg']
    RF = factors[5]*weights['wc'] + factors[6]*weights['wm'] + (1-factors[7])*weights['wp1']
    LDRI = RH*weights['wh'] * (RE*weights['we1'] + RF*weights['wf'])
    risk_levels = np.ones(LDRI.shape)

    if weights['calc_breaks'] == 1 and weights['levels'] == 5: #实时断点
        breaks = jenkspy.jenks_breaks(LDRI.flatten(), n_classes=3)

        idx_A = np.argwhere(LDRI<=breaks[1])
        idx_B = np.argwhere((LDRI>breaks[1]) & (LDRI<=breaks[2]))
        idx_C = np.argwhere((LDRI>breaks[2]) & (LDRI<=breaks[3]))
        idx_D = np.argwhere((LDRI>breaks[3]) & (LDRI<=breaks[4]))
        idx_E = np.argwhere(LDRI>breaks[4])

        lst = [idx_A,idx_B,idx_C,idx_D,idx_E]

        for num, ele in enumerate(lst):
            for j in range(len(ele)):
                idx = ele[j]
                risk_levels[idx[0]][idx[1]] = num

        weights['l5_break1'] = breaks[1]
        weights['l5_break2'] = breaks[2]
        weights['l5_break3'] = breaks[3]
        weights['l5_break4'] = breaks[4]


    elif weights['calc_breaks'] == 0 and weights['levels'] == 5:
        idx_A = np.argwhere(LDRI<=weights['l5_break1'])
        idx_B = np.argwhere((LDRI>weights['l5_break1']) & (LDRI<=weights['l5_break2']))
        idx_C = np.argwhere((LDRI>weights['l5_break2']) & (LDRI<=weights['l5_break3']))
        idx_D = np.argwhere((LDRI>weights['l5_break3']) & (LDRI<=weights['l5_break4']))
        idx_E = np.argwhere(LDRI>weights['l5_break4'])

        lst = [idx_A,idx_B,idx_C,idx_D,idx_E]

        for num, ele in enumerate(lst):
            for j in range(len(ele)):
                idx = ele[j]
                risk_levels[idx[0]][idx[1]] = num
                
                
    # figure
    tbd.set_mapboxtoken(cfg.INFO.MAPBOX_TOKEN)
    tbd.set_imgsavepath(cfg.INFO.TILE_PATH)
    
    lon_m2=lon[lon_indices]
    lat_m2=lat[lat_indices]
    X,Y = np.meshgrid(lon_m2,lat_m2)


    levels = [0,1, 2, 3,4,5]
    colors = [[0,176,80],[1,112,192],[255,255,0],[255,192,0],[255,0,0]]
    colors = [[r/255.0, g/255.0, b/255.0,0.7] for r, g, b in colors]
    
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
    mesh = ax.contourf(X, Y, risk_levels, levels=levels, colors=colors, extend='both', transform=ccrs.PlateCarree())
    
    legend_patches = [Rectangle((0, 0), 1, 1, fc=color) for color in colors]
    legend_labels = ['Ⅰ级', 'Ⅱ级', 'Ⅲ级', 'Ⅳ级', 'Ⅴ级']
    legend = ax.legend([legend_patches[i] for i in range(len(legend_labels))], legend_labels, title="雷电风险区划",bbox_to_anchor=(1, 1), framealpha=1)
    g1 = ax.gridlines(draw_labels=True, linewidth=0.8, color='grey', alpha=0.5, linestyle='--')
    g1.top_labels=False
    g1.right_labels=False
    g1.xformatter=LONGITUDE_FORMATTER
    g1.yformatter=LATITUDE_FORMATTER
    g1.rotate_labels=False
    
 
    # 设置图表范围（根据需要调整）
    bounds = [start_lon, start_lat,end_lon, end_lat]
    tbd.plot_map(plt, bounds, zoom=7, style=2)
    ax.set_extent([start_lon, end_lon, start_lat, end_lat],crs=ccrs.PlateCarree())
    
 
    save_path_picture_p=os.path.join(data_dir,'雷电风险区划.png')
    plt.savefig(save_path_picture_p, bbox_inches='tight', dpi=200)
    

    return risk_levels, LDRI,save_path_picture_p

if __name__ == '__main__':
    data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Modules10'
    filename=cfg.FILES.ADTD
    data=pd.read_csv(filename, low_memory=False)
    data=data[['Lat','Lon','Year','Mon','Day','Hour','Min','Second','Lit_Current']]
    time = {
        "Year": data["Year"],
        "Month": data["Mon"],
        "Day": data["Day"],
        "Hour": data["Hour"],
        "Minute": data["Min"],
        "Second": data["Second"]
    }
    df_time = pd.to_datetime(time)
    
    periods = pd.PeriodIndex(df_time, freq="U")
    data = data.set_index(periods)
    
    
    start_lon = 90
    end_lon = 95
    start_lat = 32
    end_lat = 36
    #%% 数据输入
    #-权重
    wd = 3.2156 #地闪密度权重
    wn = 3.3211 #地闪强度权重
    ws = 0.4525 #土壤电导率权重
    we = 1.6433 #海拔高度权重
    wt = 1.3712 #地形起伏权重
    wp = 4.0373 #人口密度权重
    wg = 5.6234 #GPD权重
    wc = 1.5697 #生命idx权重
    wm = 2.5697 #经济idx权重
    wp1 = 0.5697 #防护力idx权重
    wh = 1.3233 #危险性权重
    we1 = 3.1183 #暴露度权重
    wf = 1.4237 #脆弱性权重
    
    calc_breaks = 0 #0使用预设数值分段，1实时自然断点
    levels = 5 #默认5不变，分成5段
    
    l5_break1 = 136 #断点1
    l5_break2 = 158 #断点2
    l5_break3 = 178 #断点3
    l5_break4 = 199 #断点4
    
    
    
    
    #%% 输入数据处理
    weights = dict()
    
    weights['wd'] = wd
    weights['wn'] = wn
    weights['ws'] = ws
    weights['we'] = we
    weights['wt'] = wt
    weights['wp'] = wp
    weights['wg'] = wg
    weights['wc'] = wc
    weights['wm'] = wm
    weights['wp1'] = wp1
    weights['wh'] = wh
    weights['we1'] = we1
    weights['wf'] = wf
    
    weights['calc_breaks'] = calc_breaks
    weights['levels'] = levels
    
    weights['l5_break1'] = l5_break1
    weights['l5_break2'] = l5_break2
    weights['l5_break3'] = l5_break3
    weights['l5_break4'] = l5_break4

    risk_levels, LDRI,save_path_picture_p=get_regional_risk(data,weights,start_lon,end_lon,start_lat,end_lat,data_dir)