# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 15:02:21 2024

@author: EDY
"""
import os
import uuid
import pandas as pd
from Utils.config import cfg
from collections import OrderedDict
from Utils.get_url_path import get_url_path
from Report.code.Module.report import combine


def combine_deal(data_json):

    uuid4 = uuid.uuid4().hex
    data_dir = os.path.join(cfg.INFO.IN_DATA_DIR, uuid4)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        os.chmod(data_dir, 0o007 | 0o070 | 0o700)

    # 获取参数
    all_file_path = data_json['all_file_path']

    new_docx_path=os.path.join(data_dir,'1.docx')
    result_path=os.path.join(data_dir,'report.docx')

    # 生成结果
    result_dict=dict()
    try:
        report_path = combine(new_docx_path,result_path,all_file_path)
        report_path = report_path.replace(cfg.INFO.IN_DATA_DIR, cfg.INFO.OUT_DATA_DIR)
        result_dict['report'] = report_path.replace(cfg.INFO.OUT_DATA_DIR, cfg.INFO.OUT_DATA_URL)
    except:
        result_dict['report'] = None



    result_dict['uuid'] = uuid4

    return result_dict


