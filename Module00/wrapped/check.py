import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Tuple, List
from tqdm import tqdm
from Utils.get_local_data import get_local_data
from Utils.cost_time import cost_time
from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import yearly_data_processing, monthly_data_processing, daily_data_processing, hourly_data_processing


class check:
    '''
    天擎数据缺失情况检查，多站，多要素
    注意：传进来的df里面的异常值一定要先处理成np.nan，以免有未知问题！！

    场景：
        选定站号和要素后，检查所有要素的数据缺失情况；
        选择的站号和要素可以和后续的算法无关；
        一次只能支持一种类型的数据(年/月/日/小时)。
    todo: 是否需要支持数据库数据
    '''

    def __init__(
            self,
            df: pd.DataFrame,
            date_type: str,  # H小时 D天 MS月 YS年 MS/DS设定为月初
            elements: list,
            sta_ids: list,
            start_date: str,  # %Y or %Y%m%d%H%M%S 两种形式
            end_date: str):
        '''
        df 传进来的原始数据dataframe
        date_type 数据的时间类型 年/月/日/小时
        elements 选择的气象要素
        sta_ids 站号列表
        start_date 原始的输入时间
        end_date 原始的输出时间
        '''
        self.df = df
        self.date_type = date_type
        self.elements = elements
        self.sta_ids = sta_ids
        self.start_date = start_date
        self.end_date = end_date

        if len(self.start_date) == 4:
            self.start_date += '0101000000'
        if len(self.end_date) == 4:
            self.end_date += '1231235959'

        assert type(self.df.index) == pd.core.indexes.datetimes.DatetimeIndex, 'df的index不是datetimeindex'

    def reindex_date(self, st_id):
        '''
        re-datetimeindex
        '''
        df_sta = self.df[self.df['Station_Id_C'] == st_id]
        df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复

        # 新增补全数据时间
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq=self.date_type)
        df_sta = df_sta.reindex(dates, fill_value=np.nan)

        return df_sta

    def data_check(self, df, element, ch):
        '''
        数据的缺测时间统计和完整率统计
        '''
        try:
            dates = df[(df.loc[:, element].isna()) | (df[element]=='nan') | (df[element]=='空记录')].index.to_frame().reset_index(drop=True)

            # 1.完整率统计
            total_num = df.shape[0]  # 应测数据
            actual_num = df[~((df.loc[:, element].isna()) | (df[element]=='nan') | (df[element]=='空记录'))].shape[0]  # 实测数据
            leak_num = total_num - actual_num  # 缺测数据
            complete_rate = round((actual_num / total_num) * 100, 1)
            records = pd.DataFrame([total_num, actual_num, leak_num, complete_rate]).T
            records.columns = ['应测数据(条)', '实测数据(条)', '缺测数据(条)', '数据完整率%']
            records.insert(loc=0, column='天擎英文要素名', value=element)
            records.insert(loc=0, column='天擎中文要素名', value=ch)

            # 2.缺测时间统计
            if len(dates) != 0:
                deltas = dates.diff()[1:]  # timedelta64[ns] 类型 所以只能用timedelta，不能用relativedelta/pd.DateOffset

                if self.date_type == 'h':
                    gaps = deltas[deltas > timedelta(hours=1)]  # days/hours
                else:
                    gaps = deltas[deltas > timedelta(days=1)]

                gaps_idx = gaps.dropna().index

                # 正常流程--小时/日/年的处理
                if len(gaps_idx) == 0:
                    start = dates.iloc[0, 0]
                    end = dates.iloc[-1, 0]
                    num_hours = len(dates)
                    time = [start, end, num_hours]
                    time = np.array(time).reshape(1, -1)
                    time_periods = pd.DataFrame(time, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计'])

                else:
                    periods_list = []
                    for i in range(0, len(gaps_idx) + 1):
                        if i == 0:
                            temp = dates[0:gaps_idx[i]].reset_index(drop=True)
                        elif (i > 0) and (i < len(gaps_idx)):
                            temp = dates[gaps_idx[i - 1]:gaps_idx[i]].reset_index(drop=True)
                        elif i == len(gaps_idx):
                            temp = dates[gaps_idx[i - 1]:].reset_index(drop=True)

                        start = temp.iloc[0, 0]
                        end = temp.iloc[-1, 0]
                        num_hours = len(temp)
                        time = [start, end, num_hours]
                        periods_list.append(time)
                        time_periods = pd.DataFrame(periods_list, columns=['缺测起始时间', '缺测终止时间', '缺测时间总计'])

                time_periods['缺测起始时间'] = time_periods['缺测起始时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
                time_periods['缺测终止时间'] = time_periods['缺测终止时间'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # 额外流程--针对月数据的统计结果修改
                # 手动合成连续的时间段 (如果是月数据，time_periods显示的是缺失时间点，而非时间段)
                if self.date_type == 'MS' and len(time_periods) > 1:
                    timeStamp = pd.to_datetime(time_periods['缺测起始时间'])
                    time_range = []
                    timeNode = [
                        timeStamp[0],
                    ]  # 缺测起始时间点

                    for j in range(1, timeStamp.shape[0]):
                        if timeStamp[j] - pd.DateOffset(months=1) != timeStamp[j - 1]:
                            time_range.append([timeNode[-1], timeStamp[j - 1]])
                            timeNode.append(timeStamp[j])

                    time_range.append([timeNode[-1], timeStamp[j]])  # 缺测时间段
                    tmp = pd.DataFrame(time_range)
                    tmp.columns = ['缺测起始时间', '缺测终止时间']
                    tmp['缺测起始时间'] = tmp['缺测起始时间'].dt.strftime('%Y-%m')
                    tmp['缺测终止时间'] = tmp['缺测终止时间'].dt.strftime('%Y-%m')
                    tmp['缺测时间总计'] = tmp.apply(lambda x: (int(x['缺测终止时间'][:4]) - int(x['缺测起始时间'][:4])) * 12 + (int(x['缺测终止时间'][5:]) - int(x['缺测起始时间'][5:]) + 1), axis=1)
                    time_periods = tmp

                # 额外流程--针对年数据的统计结果修改
                if self.date_type == 'YS' and len(time_periods) != 0:
                    time_periods['缺测起始时间'] = time_periods['缺测起始时间'].apply(lambda x: x[:4])
                    time_periods['缺测终止时间'] = time_periods['缺测终止时间'].apply(lambda x: x[:4])

            else:
                # records = pd.DataFrame()
                time_periods = pd.DataFrame()

        except Exception as e:
            logging.exception(e)
            records = pd.DataFrame()
            time_periods = pd.DataFrame()

        return records, time_periods

    @cost_time
    def run(self):
        '''
        主流程
        '''
        result = edict()
        # result['date_type'] = self.date_type
        element_ch = pd.read_csv(cfg.FILES.ELEMENT_CH, header=None)
        element_ch.columns = ['英文', '中文']
        element_ch = element_ch.set_index(['英文'])['中文'].to_dict()

        for st_id in self.sta_ids:
            # df_sta = self.reindex_date(st_id)
            df_sta = self.df[self.df['Station_Id_C'] == st_id]
            df_sta = df_sta[~df_sta.index.duplicated()]  # 数据去除重复
            result[st_id] = edict()

            all_records = []
            for element in self.elements:
                # 跳过空字符串元素
                if not element or element.strip() == '':
                    continue
                    
                # 检查元素是否在字典中存在
                if element not in element_ch:
                    logging.warning(f"Element '{element}' not found in element_ch dictionary, skipping...")
                    continue
                    
                ch = element_ch[element]
                records, time_periods = self.data_check(df_sta, element, ch)
                all_records.append(records)
                result[st_id][ch] = edict()
                result[st_id][ch]['缺失时间段统计'] = time_periods.to_dict(orient='records')

            all_recodrs = pd.concat(all_records, axis=0)
            result[st_id]['所有要素完整率统计'] = all_recodrs.to_dict(orient='records')

        return result


if __name__ == '__main__':
    sta_ids = '56151'
    years = '1950,2023'
    path = r'C:\Users\MJY\Desktop\qhkxxlz\app\Files\test_data\qh_mon.csv'
    month_eles = ('Station_Id_C,Station_Name,Lat,Lon,Datetime,Year,Mon,' + 'PRE_Days,Hail_Days').split(',')
    df = pd.read_csv(path, low_memory=False)
    monthly_df = get_local_data(df, sta_ids, month_eles, years, 'Month')
    start_date = '1950'
    end_date = '2023'
    date_type = 'MS'  # h小时 D天 MS月 YS年
    elements = ['PRE_Days', 'Hail_Days']
    sta_ids = ['56151']
    check_day = check(monthly_df, date_type, elements, sta_ids, start_date, end_date)
    result = check_day.run()