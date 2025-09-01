import os
import uuid
import numpy as np
import pandas as pd
from collections import OrderedDict
from Module00.wrapped.check import check
from Module02.wrapped.gst_statistics import basic_gst_statistics
from Module02.wrapped.pre_statistics import basic_pre_statistics
from Module02.wrapped.prs_statistics import basic_prs_statistics
from Module02.wrapped.rh_statistics import basic_rh_statistics
from Module02.wrapped.snow_statistics import basic_snow_statistics
from Module02.wrapped.tem_statistics import basic_tem_statistics
from Module02.wrapped.vapor_statistics import basic_vapor_statistics
from Module02.wrapped.win_freq_statistics import basic_win_freq_statistics
from Module02.wrapped.win_statistics import basic_win_statistics
from Module02.wrapped.ssh_statistics import basic_ssh_statistics

from Utils.config import cfg
from Utils.ordered_easydict import OrderedEasyDict as edict
from Utils.data_processing import yearly_data_processing, monthly_data_processing, daily_data_processing
from Utils.get_url_path import get_url_path
from Utils.get_local_data import get_local_data
from Utils.data_loader_with_threads import get_cmadaas_yearly_data, get_cmadaas_monthly_data, get_cmadaas_daily_data
from Report.code.Module02.wind import win_report
from Utils.get_url_path import save_cmadaas_data

def feature_stats_handler(data_json):
    '''
    基本气象条件分析组件
    '''
    result_dict = edict()

    # 1.读取参数
    years = data_json['years']  # 选择的数据年份
    sta_ids = data_json['station_ids']  # 选择的站号
    elements = data_json['elements']  # 选择的气象要素

    # 2.参数处理
    if isinstance(elements, str):
        elements = [elements]

    uuid4 = uuid.uuid4().hex
    result_dict['uuid'] = uuid4
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)
    
    if isinstance(sta_ids, list):
        sta_ids = [str(ids) for ids in sta_ids]
        sta_ids = ','.join(sta_ids)
    if isinstance(sta_ids, int):
        sta_ids = str(sta_ids)

    # 3.拼接需要下载的参数
    yearly_elements = ''
    monthly_elements = ''
    daily_elements = ''
    yearly_df = None
    monthly_df = None
    daily_df = None

    for ele in elements:
        if ele == 'PRS':
            # yearly_elements += 'PRS_Avg,PRS_Max,PRS_Max_Odate,PRS_Min,PRS_Min_Odate,'
            monthly_elements += 'PRS_Avg,PRS_Max,PRS_Min,PRS_Max_ODay_C,PRS_Min_ODay_C,'
            daily_elements += 'PRS_Avg,PRS_Max,PRS_Min,'

        elif ele == 'TEM':
            # yearly_elements += 'TEM_Avg,TEM_Max_Avg,TEM_Min_Avg,TEM_Max,V12011_067,TEM_Min,V12012_067,'
            monthly_elements += 'TEM_Avg,TEM_Max,TEM_Min,TEM_Max_Avg,TEM_Min_Avg,TEM_Max_ODay_C,TEM_Min_ODay_C,'
            daily_elements += 'TEM_Avg,TEM_Max,TEM_Min,'

        elif ele == 'WIND':
            # yearly_elements += 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,V11042_067,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODate_C,WIN_D_Max_C,WIN_D_Max_Freq,'
            monthly_elements += 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max_C,WIN_S_Max_ODay_C,WIN_S_Inst_Max,WIN_D_INST_Max_C,WIN_S_INST_Max_ODay_C,WIN_D_Max_C,WIN_D_Max_Freq,WIN_NNE_Freq,WIN_NE_Freq,WIN_ENE_Freq,WIN_E_Freq,WIN_ESE_Freq,WIN_SE_Freq,WIN_SSE_Freq,WIN_S_Freq,WIN_SSW_Freq,WIN_SW_Freq,WIN_WSW_Freq,WIN_W_Freq,WIN_WNW_Freq,WIN_NW_Freq,WIN_NNW_Freq,WIN_N_Freq,WIN_C_Freq,WIN_S_Avg_NNE,WIN_S_Avg_NE,WIN_S_Avg_ENE,WIN_S_Avg_E,WIN_S_Avg_ESE,WIN_S_Avg_SE,WIN_S_Avg_SSE,WIN_S_Avg_S,WIN_S_Avg_SSW,WIN_S_Avg_SW,WIN_S_Avg_WSW,WIN_S_AVG_W,WIN_S_Avg_WNW,WIN_S_Avg_NW,WIN_S_Avg_NNW,WIN_S_Avg__N,'
            daily_elements += 'WIN_S_2mi_Avg,WIN_S_Max,WIN_D_S_Max,WIN_S_Inst_Max,WIN_D_INST_Max,'
            
        elif ele == 'VAPOR':
            daily_elements += 'VAP_Avg,'

        elif ele == 'PRE':
            # yearly_elements += 'PRE_Time_2020,PRE_Max_Day,V13052_067,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,PRE_LCDays_EMon,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EMon,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EMon,PRE_Coti_Max_EDay,'
            monthly_elements += 'PRE_Time_2020,PRE_Max_Day,PRE_Max_ODay_C,PRE_A0p1mm_Days,PRE_A10mm_Days,PRE_A25mm_Days,PRE_A50mm_Days,PRE_A100mm_Days,PRE_A150mm_Days,Days_Max_Coti_PRE,PRE_Conti_Max,EDay_Max_Coti_PRE,NPRE_LCDays,NPRE_LCDays_EDay,PRE_Max_Conti,Days_Max_Conti_PRE,PRE_Coti_Max_EDay,'
            daily_elements += 'PRE_Time_2020,'
            
        elif ele == 'RH':
            # yearly_elements += 'RHU_Avg,RHU_Min,V13007_067,'
            monthly_elements += 'RHU_Avg,RHU_Min,RHU_Min_ODay_C,'
            daily_elements += 'RHU_Avg,RHU_Min,'

        elif ele == 'GST':
            # yearly_elements += 'GST_Avg,EGST_Max_Avg_Mon,GST_Min_Avg,GST_Max,V12311_067,GST_Min,V12121_067,'
            monthly_elements += 'GST_Avg,EGST_Max_Avg_Mon,GST_Min_Avg,GST_Max,EGST_Max_ODay_C,GST_Min,GST_Min_Ten_ODay_C,'
            daily_elements += 'GST_Avg,GST_Max,GST_Min,'

        elif ele == 'SSH':
            # yearly_elements += 'Snow_Depth_Max,V13334_067,'
            daily_elements += 'SSH,'
            
        elif ele == 'SNOW':
            # yearly_elements += 'Snow_Depth_Max,V13334_067,'
            monthly_elements += 'Snow_Depth_Max,V13334_060_C,'
            daily_elements += 'Snow_Depth,'
            
    # 4.数据获取
    if cfg.INFO.READ_LOCAL:
        
        # year_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,' + yearly_elements[:-1]).split(',')
        month_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,' + monthly_elements[:-1]).split(',')
        day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')

        daily_df = pd.read_csv(cfg.FILES.QH_DATA_DAY)
        
        if 'WIND' in elements:
            daily_df['WIN_D_INST_Max'] = np.random.randint(0,361,size=len(daily_df))
        elif 'GST' in elements:
            daily_df['GST_Avg'] = daily_df['GST_Min']
            daily_df['GST_Max'] = daily_df['GST_Min']
        elif 'SNOW' in elements:
            daily_df['Snow_Depth'] = 20
            
        daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
        
        # 水汽压的时候不读取
        if elements[0] not in ['VAPOR','SSH']:
            monthly_df = pd.read_csv(cfg.FILES.QH_DATA_MONTH, low_memory=False)
            monthly_df = get_local_data(monthly_df, sta_ids, month_eles, years, 'Month')
    else:
        day_ele_list = ['VAPOR','SSH']
        other_ele_list = ['PRS', 'TEM', 'WIND', 'PRE', 'RH', 'GST', 'SNOW']

        # 天擎数据下载 and 数据前处理
        try:
            # if len(set(other_ele_list) & set(elements)) != 0:  # 取交集，如果选中的要素同样在month_ele_list中，下载年/月数据
            # yearly_df = get_cmadaas_yearly_data(years, yearly_elements, sta_ids)
            # yearly_df = yearly_data_processing(yearly_df, years)
            if elements[0] not in ['VAPOR','SSH']:
                monthly_df = get_cmadaas_monthly_data(years, monthly_elements, sta_ids)
                monthly_df = monthly_data_processing(monthly_df, years)

            daily_df = get_cmadaas_daily_data(years, daily_elements, sta_ids)
            daily_df = daily_data_processing(daily_df, years)

        except Exception as e:
            raise Exception('天擎数据下载或处理失败')

    # 5.计算之前先检测数据完整率 check h小时 D天 MS月 YS年
    years = years.split(',')
    result_dict.check_result = edict()
    yearly_elements = yearly_elements[:-1]
    monthly_elements = monthly_elements[:-1]
    daily_elements = daily_elements[:-1]
    
    # if yearly_df is not None and len(yearly_df) != 0 and 'VAPOR' not in elements:
    #     checker = check(yearly_df, 'YS', yearly_elements.split(','), [sta_ids], years[0], years[1])
    #     check_result = checker.run()
    #     result_dict.check_result['使用的天擎年要素'] = check_result

    if monthly_df is not None and len(monthly_df) != 0:
        checker = check(monthly_df, 'MS', monthly_elements.split(','), [sta_ids], years[0], years[1])
        check_result = checker.run()
        result_dict.check_result['使用的天擎月要素'] = check_result

    if daily_df is not None and len(daily_df) != 0:
        checker = check(daily_df, 'D', daily_elements.split(','), [sta_ids], years[0], years[1])
        check_result = checker.run()
        result_dict.check_result['使用的天擎日要素'] = check_result

    # 6.结果生成
    result_list = []  # 用于生成所有保存路径
    for ele in elements:
        if ele == 'PRS':
            result_dict.pressure = edict()
            basic_prs_yearly, basic_prs_accum, report_path = basic_prs_statistics(daily_df, monthly_df, data_dir)
            result_dict.pressure['历年'] = basic_prs_yearly
            result_dict.pressure['累年各月'] = basic_prs_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.pressure['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.pressure['report'] = None

            result_list.append(OrderedDict(zip(['历年气压统计', '累年各月气压统计'], [basic_prs_yearly, basic_prs_accum])))

        elif ele == 'TEM':
            result_dict.temperature = edict()
            basic_tem_yearly, basic_tem_accum, report_path = basic_tem_statistics(daily_df, monthly_df, data_dir)
            result_dict.temperature['历年'] = basic_tem_yearly
            result_dict.temperature['累年各月'] = basic_tem_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.temperature['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.temperature['report'] = None

            result_list.append(OrderedDict(zip(['历年气温统计', '累年各月气温统计'], [basic_tem_yearly, basic_tem_accum])))

        elif ele == 'WIND':
            result_dict.wind_speed = edict()
            # 风速
            basic_win_yearly, basic_win_accum = basic_win_statistics(daily_df, monthly_df)
            result_dict.wind_speed['历年'] = basic_win_yearly
            result_dict.wind_speed['累年各月'] = basic_win_accum
            result_list.append(OrderedDict(zip(['历年风速统计', '累年各月风速统计'], [basic_win_yearly, basic_win_accum])))

            # 风向频率
            basic_win_d_accum, basic_win_s_accum = basic_win_freq_statistics(monthly_df)
            result_dict.wind_freq_table = basic_win_d_accum
            result_dict.wind_freq_speed_table = basic_win_s_accum

            # report
            try:
                report_path = win_report(basic_win_yearly, basic_win_accum, monthly_df, basic_win_d_accum, basic_win_s_accum, data_dir)
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict['report'] = None

            result_list.append(OrderedDict(zip(['累年各月风向频率统计', '累年各月风向对应风速统计'], [basic_win_d_accum, basic_win_s_accum])))

        elif ele == 'VAPOR':
            result_dict.water_vapor_pressure = edict()
            basic_vapor_yearly, basic_vapor_accum, report_path = basic_vapor_statistics(daily_df, data_dir)
            result_dict.water_vapor_pressure['历年'] = basic_vapor_yearly
            result_dict.water_vapor_pressure['累年各月'] = basic_vapor_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.water_vapor_pressure['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.water_vapor_pressure['report'] = None

            result_list.append(OrderedDict(zip(['历年水气压统计', '累年各月水气压统计'], [basic_vapor_yearly, basic_vapor_accum])))

        elif ele == 'SSH':
            result_dict.water_vapor_pressure = edict()
            basic_vapor_yearly, basic_vapor_accum, report_path = basic_ssh_statistics(daily_df, data_dir)
            result_dict.water_vapor_pressure['历年'] = basic_vapor_yearly
            result_dict.water_vapor_pressure['累年各月'] = basic_vapor_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.water_vapor_pressure['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.water_vapor_pressure['report'] = None

            result_list.append(OrderedDict(zip(['历年日照时统计', '累年各月日照时统计'], [basic_vapor_yearly, basic_vapor_accum])))


        elif ele == 'PRE':
            result_dict.precipitation = edict()
            basic_pre_yearly, basic_pre_accum, report_path = basic_pre_statistics(daily_df, monthly_df, data_dir)
            result_dict.precipitation['历年'] = basic_pre_yearly
            result_dict.precipitation['累年各月'] = basic_pre_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.precipitation['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.precipitation['report'] = None

            result_list.append(OrderedDict(zip(['历年降水统计', '累年各月降水统计'], [basic_pre_yearly, basic_pre_accum])))

        elif ele == 'RH':
            result_dict.relative_humidity = edict()
            basic_rh_yearly, basic_rh_accum, report_path = basic_rh_statistics(daily_df, monthly_df, data_dir)
            result_dict.relative_humidity['历年'] = basic_rh_yearly
            result_dict.relative_humidity['累年各月'] = basic_rh_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.relative_humidity['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.relative_humidity['report'] = None

            result_list.append(OrderedDict(zip(['历年气压统计', '累年各月气压统计'], [basic_rh_yearly, basic_rh_accum])))

        elif ele == 'GST':
            result_dict.ground_surface_temperature = edict()
            basic_gst_yearly, basic_gst_accum, report_path = basic_gst_statistics(daily_df, monthly_df, data_dir)
            result_dict.ground_surface_temperature['历年'] = basic_gst_yearly
            result_dict.ground_surface_temperature['累年各月'] = basic_gst_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.ground_surface_temperature['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.ground_surface_temperature['report'] = None

            result_list.append(OrderedDict(zip(['历年地面温度统计', '累年各月地面温度统计'], [basic_gst_yearly, basic_gst_accum])))

        elif ele == 'SNOW':
            result_dict.snow_depth = edict()
            basic_snow_yearly, basic_snow_accum, report_path = basic_snow_statistics(daily_df, monthly_df, data_dir)
            result_dict.snow_depth['历年'] = basic_snow_yearly
            result_dict.snow_depth['累年各月'] = basic_snow_accum

            try:
                report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
                result_dict.snow_depth['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
            except:
                result_dict.snow_depth['report'] = None

            result_list.append(OrderedDict(zip(['历年积雪深度统计', '累年各月积雪深度统计'], [basic_snow_yearly, basic_snow_accum])))

    # 6.结果保存
    if cfg.INFO.SAVE_RESULT:
        result_dict['csv'] = save_cmadaas_data(data_dir, mon_data=monthly_df, day_data=daily_df)

    return result_dict

if __name__=='__main__':
    
    data_json={
  "years": "1985,2009",
  "station_ids": "52754",
  "elements": "SNOW",
  "id": "uuid",
  "is_async": 0,
  "staValueName": [
    "青海省",
    "海北藏族自治州",
    "刚察县",
    "52754"
  ],
  "stationName": "刚察_52754",
  "staValue": "国家站"
}
    
    