# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 14:21:00 2024

@author: EDY
"""
from Report.code.Module07.heat_island_month_report import heat_island_month_report
from Report.code.Module07.heat_island_season_report import heat_island_season_report
from Report.code.Module07.heat_island_year_report import heat_island_year_report
from docx import Document
from docxcompose.composer import Composer
import os
from Utils.config import cfg

# data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module07'

def heat_island_report(time_resolution,all_result,df_day, main_st_ids,data_types,data_dir):
    
    pathz=[os.path.join(cfg['report']['template'],'Module07','heat_island_1.docx')]
    for i in time_resolution:
        if i == 'year':
            report_path=heat_island_year_report(all_result,df_day, main_st_ids,data_types,data_dir)
            pathz.append(report_path)
        elif i == 'season':
            report_path=heat_island_season_report(all_result,df_day, main_st_ids,data_types,data_dir)
            pathz.append(report_path)           
        elif i == 'month':
            report_path=heat_island_month_report(all_result,df_day, main_st_ids,data_types,data_dir)
            pathz.append(report_path)  
    
    
    new_docx_path=os.path.join(data_dir,'heat_island.docx')
    master = Document(pathz[0])
    middle_new_docx = Composer(master)
    for word in pathz[1:]:  # 从第二个文档开始追加
        word_document = Document(word)
        # 删除手动添加分页符的代码
        middle_new_docx.append(word_document)
    middle_new_docx.save(new_docx_path)
    
    return new_docx_path
