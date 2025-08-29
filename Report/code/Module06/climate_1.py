# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 14:56:12 2024

@author: EDY
"""


import matplotlib
matplotlib.use('Agg')
from docxtpl import DocxTemplate
import os
from Utils.config import cfg



# data_dir=r'D:\Project\3_项目\2_气候评估和气候可行性论证\qhkxxlz\Report\report\Module06'
def climate_1_report(daily_df,data_dir):

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
      
    doc_path=os.path.join(cfg['report']['template'],'Module06','climate_1.docx')
    doc=DocxTemplate(doc_path)
    
    dic=dict()

    dic['start_year']=daily_df.index.year[0]
    dic['end_year']=daily_df.index.year[-1]
    dic['station_name']=daily_df['Station_Name'][0]
    
   
    # 模版文件读取写入字典
    doc.render(dic)
    # 保存结果到新的docx文件
    report=os.path.join(data_dir,'climate_1.docx')
    doc.save(report)
    
    
    return report