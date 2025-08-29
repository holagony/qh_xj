import os
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
import shapefile
import shapely.geometry as geometry
from tqdm import tqdm
from Utils.config import cfg
import matplotlib.pyplot as plt

class calc_intensity_and_density():
    def __init__(self, start_lon, start_lat, end_lon, end_lat, lon_m,lat_m):
        self.start_lon = start_lon
        self.start_lat = start_lat
        self.end_lon = end_lon
        self.end_lat = end_lat
        self.Lons = lon_m
        self.Lats = np.flipud(lat_m)

        lonlat_range = [start_lon, end_lon, start_lat, end_lat]
        self.lonlat_range = lonlat_range
        
    def generate_data_grid(self, picked_data):
        level1 = np.percentile(picked_data[:,2], 60)
        level2 = np.percentile(picked_data[:,2], 80)
        level3 = np.percentile(picked_data[:,2], 90)
        level4 = np.percentile(picked_data[:,2], 95)
        #print('百分位数断点：' + str(level1), str(level2), str(level3), str(level4)) #百分位60% 80% 90% 95%

        data_part0 = picked_data[picked_data[:,2]<=level1]
        data_part1 = picked_data[(picked_data[:,2]>level1) & (picked_data[:,2]<=level2)]
        data_part2 = picked_data[(picked_data[:,2]>level2) & (picked_data[:,2]<=level3)]
        data_part3 = picked_data[(picked_data[:,2]>level3) & (picked_data[:,2]<=level4)]
        data_part4 = picked_data[picked_data[:,2]>level4]

        Lons = self.Lons
        Lats = self.Lats
        H_total, xedges, yedges = np.histogram2d(picked_data[:,0], picked_data[:,1], bins=(Lons, Lats))
        H0, _, _ = np.histogram2d(data_part0[:,0], data_part0[:,1], bins=(Lons, Lats))
        H1, _, _ = np.histogram2d(data_part1[:,0], data_part1[:,1], bins=(Lons, Lats))
        H2, _, _ = np.histogram2d(data_part2[:,0], data_part2[:,1], bins=(Lons, Lats))
        H3, _, _ = np.histogram2d(data_part3[:,0], data_part3[:,1], bins=(Lons, Lats))
        H4, _, _ = np.histogram2d(data_part4[:,0], data_part4[:,1], bins=(Lons, Lats))

        H_total = H_total.T
        H0 = H0.T.reshape(1, (len(Lats)-1), (len(Lons)-1))
        H1 = H1.T.reshape(1, (len(Lats)-1), (len(Lons)-1))
        H2 = H2.T.reshape(1, (len(Lats)-1), (len(Lons)-1))
        H3 = H3.T.reshape(1, (len(Lats)-1), (len(Lons)-1))
        H4 = H4.T.reshape(1, (len(Lats)-1), (len(Lons)-1))

        percentile_grid = np.concatenate((H0,H1,H2,H3,H4),axis=0) #不同百分位数的网格
        lightning_grid =  H_total

        return percentile_grid, lightning_grid

    def normalization(self, original_data):
        _range = np.max(original_data) - np.min(original_data)
        new_data = 0.5 + (0.5*(original_data - np.min(original_data))) / _range
        return new_data

    def calc_intensity(self, data):
        lightning_intensity = (1/15)*data[0] + (2/15)*data[1] + (3/15)*data[2] + (4/15)*data[3] + (5/15)*data[4]
        return lightning_intensity

    def calc_density(self, lighting_data,adtd):
        # 计算密度
        # 计算密度
        start_index = adtd.index.sort_values()[0]
        end_index = adtd.index.sort_values()[-1]
        
        # 计算时间差
        time_difference = end_index - start_index
        
        # 使用 pandas 的 Timedelta 对象计算年份差
        # 注意：这里假设一年有 365.25 天，以考虑到闰年
        num_year = time_difference / pd.Timedelta(days=365.25)

        lightning_density = lighting_data/num_year
        return lightning_density

    def run(self,adtd):
        lon_min = self.start_lon
        lon_max = self.end_lon
        lat_min = self.start_lat
        lat_max = self.end_lat
        adtd_data = adtd[(adtd['Lon']>lon_min) & (adtd['Lon']<lon_max) & 
                         (adtd['Lat']>lat_min) & (adtd['Lat']<lat_max) & 
                         (np.abs(adtd['Lit_Current']<200)) & 
                         (np.abs(adtd['Lit_Current']>2))]
        
        lon_points = np.array(adtd_data['Lon'].astype(float))[:, np.newaxis]
        lat_points = np.array(adtd_data['Lat'].astype(float))[:, np.newaxis]
        intensity = np.array(np.abs(adtd_data['Lit_Current']).astype(float))[:, np.newaxis]
        data_points = np.concatenate((lon_points,lat_points,intensity), axis=1)

        #计算强度结果 先归一化
        percentile_grid, lightning_counts = self.generate_data_grid(picked_data=data_points)
        norm_data = self.normalization(original_data=percentile_grid)
        lightning_intensity = self.calc_intensity(data=norm_data)
        lightning_intensity = np.flipud(lightning_intensity)

        #计算密度结果 后归一化
        lightning_density = self.calc_density(lighting_data=lightning_counts,adtd=adtd)
        lightning_density = np.flipud(lightning_density)
        lightning_density_norm = self.normalization(original_data=lightning_density)

        return lightning_intensity, lightning_density_norm

def filter_point_out_shape(original_data):
    shp = shapefile.Reader(cfg.shp_file, encoding='gbk')
    qh_shp = shp.shapeRecords()[20].shape

    index = []
    in_shape_points = []

    for idx, point in tqdm(enumerate(original_data)):
        if geometry.Point(point[0:2]).within(geometry.shape(qh_shp)):
            in_shape_points.append(point)
            index.append(idx)

    return index, in_shape_points
