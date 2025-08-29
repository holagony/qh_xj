import numpy as np
import pandas as pd
from typing import Tuple


class check:
    '''
    数据订正 (天擎 or 数据库)
    场景：
    数据经过check后，自定义选择相关方法进行订正；
    单站订正；
    保存原始数据和订正后的数据到数据库。
    '''

    def __init__(self, data, type, start_date, end_date, elements, methods, database_info: dict):
        '''
        data 原始数据 传进来 or 在这个里面直接下载data
        type 数据类型 年/月/日/小时
        start_date 原始的输入时间
        end_date 原始的输出时间
        elements 选择的气象要素
        methods 选择的订正方法，可填'Auto'
        database_info 数据库信息
        '''
        self.data = data
        self.type = type
        self.start_date = start_date
        self.end_date = end_date
        self.elements = elements
        self.methods = methods
        self.database_info = database_info

    def get_move_records(self):
        '''
        从数据库里面搜索传入的站号，是否有沿革记录，有的话提取迁站时间；
        传入的是小时和日数据的时候激活（迁站记录精确到日，默认认为年/月数据经过订正）
        '''

    def processing(self):
        '''
        数据处理，目前在data_processing.py里面，todo移进来
        '''

    def qianzhan(self):
        '''
        根据站点沿革数据，迁站订正（回归/比值/差值法）
        '''

    def interp(self):
        '''
        缺失值填充，插值
        '''

    def save_data(self):
        '''
        将原始数据和订正后的数据分别保存到数据库
        '''
        # 写入数据库

    def run(self):
        '''
        1.检查是否有沿革记录
        2.如果有迁站订正，如果没有就pass
        3.数据本身订正，缺失值处理
        4.保存订正前后数据到数据库
        '''
