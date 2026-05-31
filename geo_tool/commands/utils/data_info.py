# ENA API document https://docs.google.com/document/d/1CwoY84MuZ3SdKYocqssumghBF88PWxUZ/edit?pli=1
import requests
import pandas as pd
from io import StringIO
import xml.etree.ElementTree as ET
import time
import re
import os
import logging
from lxml import etree

def get_info_ena(project,output_path):
    if not os.path.exists(os.path.join(output_path, f"{project}_sample_full_metadata.csv")):
        API_URL = "https://www.ebi.ac.uk/ena/portal/api/search"
        params = {
            # "result": "sample",  # 目标层级：read_run（和你选中的 returnFields 接口一致） # 这里可以改其他的
            "result": "read_run",
            "query": f'study_accession="{project}"',  # 按项目ID筛选
            "fields": "all",  # 直接返回该层级所有可返回字段，无需提前查 returnFields # 也可以不用下载所有的，可以指定
            "format": "tsv"
        }
        # 直接发起请求，无需额外的 returnFields 调用
        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()
        # 解析并保存所有字段的 Metadata
        df = pd.read_csv(StringIO(response.text), sep="\t")
        # generate a dict like {'SRRXXXX': {fastq_aspera:'fasp.sra.xxx', 'sample_alias': 'PRJNA810439'}} 
        metadata_dict = {}
        for index, row in df.iterrows():
            metadata_dict[row['run_accession']] = {
                'fastq_aspera': row['fastq_aspera'].split(';'),
                'sample_alias': row['sample_alias'],
                'fastq_md5': row['fastq_md5'].split(';')
            }
        # another way to generate a dict
        # metadata_dict = df[['run_accession', 'fastq_aspera', 'sample_alias']].set_index('run_accession').to_dict('index')
        df.to_csv(output_path+"/" + f"{project}_sample_full_metadata.csv",
                index=False)
        print(f"✅ 下载完成：{len(df.columns)} 个字段的 read_run 层级 Metadata")
        print("所有字段列表：")
        print(df.columns.tolist())
    else:
        print(f"✅ 已存在 {project}_sample_full_metadata.csv，无需重复下载")
        metadata_dict = {}
        df = pd.read_csv(os.path.join(output_path, f'{project}_sample_full_metadata.csv'),sep=',')
        for index, row in df.iterrows():
            metadata_dict[row['run_accession']] = {
                'fastq_aspera': row['fastq_aspera'].split(';'),
                'sample_alias': row['sample_alias'],
                'fastq_md5': row['fastq_md5'].split(';')
            }
    return metadata_dict

def generate_gsm_srr_file(srr_gsm_dict,output_path):
    """生成 GSM 到 SRR 映射文件"""
    gsm_srr_dict = {}
    for srr, gsm in srr_gsm_dict.items():
        if gsm not in gsm_srr_dict:
            gsm_srr_dict[gsm] = []
        gsm_srr_dict[gsm].append(srr)
    with open(output_path+"/gsm_srr.txt", "w", encoding="utf-8") as f:
        for gsm, srrs in gsm_srr_dict.items():
            f.write(f"{gsm}\t{' '.join(srrs)}\n")

def esearch_sra_uids(bioproject: str, retmax: int = 100000) -> list:
    """
    使用 ESearch 获取 Bioproject 下所有 SRA Run 的 UID（数字ID）
    """
    term = f"{bioproject}[Bioproject]"
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "sra",
        "term": term,
        "retmax": retmax
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    tree = ET.fromstring(response.content)
    uids = [elem.text for elem in tree.findall(".//Id") if elem.text]
    print(f"Found {len(uids)} SRA runs for {bioproject}")
    return uids


def efetch_sra_data(uids: list, rettype: str) -> str:
    """
    使用 EFetch 获取数据
    rettype: "acc" -> accession list (text)
             "runinfo" -> metadata (CSV)
    """
    if not uids:
        return ""
    batch_size = 5000
    all_results = []
    for i in range(0, len(uids), batch_size):
        batch = uids[i:i + batch_size]
        id_str = ",".join(batch)
        params = {
            "db": "sra",
            "id": id_str,
            "rettype": rettype,
            "retmode": "text"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        content = response.text
        all_results.append(content)
        if i + batch_size < len(uids):
            time.sleep(0.35)
    return "".join(all_results)


def prjna_info(bioproject: str, output_path: str):
    if not os.path.exists(os.path.join(output_path, f"{bioproject}_metadata.csv")):
        uids = esearch_sra_uids(bioproject)
        if not uids:
            print("No SRA runs found.")
            return False
        '''
        print("Downloading Accession List...")
        accessions = efetch_sra_data(uids, "acc")
        with open(f"{bioproject}_accessions.txt", "w") as f:
            f.write(accessions)
        print(f"Saved to {bioproject}_accessions.txt")
        '''
        print("Downloading Metadata...")
        metadata = efetch_sra_data(uids, "runinfo")
        with open(f"{output_path}/{bioproject}_metadata.csv", "w") as f:
            f.write(metadata)
        print(f"Saved to {output_path}/{bioproject}_metadata.csv")
        df = pd.read_csv(f"{output_path}/{bioproject}_metadata.csv", sep=',')
        metadata_dict = {}
        for index, row in df.iterrows():
            metadata_dict[row['Run']] = row['SampleName']
        generate_gsm_srr_file(metadata_dict, output_path)
    else:
        print(f"✅ 已存在 {bioproject}_metadata.csv，无需重复下载")
        df = pd.read_csv(f"{output_path}/{bioproject}_metadata.csv", sep=',')
        metadata_dict = {}
        for index, row in df.iterrows():
            metadata_dict[row['Run']] = row['SampleName']
        generate_gsm_srr_file(metadata_dict, output_path)
    return metadata_dict



# 下面是针对输入GEO，如果输入PRJNA1135255 就按上面来，有无原始   如果输入GEO就按下面来，有无原始，有原始时就按上面的下载临床数据
def judge_geo_data_availability(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    # 初始化结果字典
    data_result = {
        "has_raw_data": False,
        "raw_data_note": "",
        "has_processed_data": False,
        "processed_data_notes": []
    }
    try:
        # 1. 请求页面，获取完整HTML文本（无需解析，直接用于正则匹配）
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_text = response.text
        # 预处理HTML：去除多余空格和换行，便于正则匹配
        clean_html = re.sub(r'\s+', ' ', html_text).strip()
        print("页面请求成功，开始快速判断数据可用性...")
        # 2. 第一步：正则匹配「SRA Run Selector」（核心原始数据标识）
        sra_pattern = r'SRA Run Selector'
        sra_match = re.search(sra_pattern, clean_html, re.IGNORECASE)  # re.IGNORECASE：不区分大小写
        if sra_match:
            # 存在SRA标识，直接判定有原始数据，无需后续解析
            data_result["has_raw_data"] = True
            data_result["raw_data_note"] = "存在SRA Run Selector，原始数据归档于SRA数据库"
            print("🔍 检测到「SRA Run Selector」，直接判定有原始数据！")
            # 到达新的页面获得临床数据
            # 增强版正则：兼容空格、换行、属性顺序变化
            # pattern = r'<a[^>]*href="(/Traces/study/\?acc=PRJNA\d+)"[^>]*>SRA Run Selector</a>'
            pattern = r'<a\s+href="(/Traces/study/\?acc=(PRJNA\d+))">SRA Run Selector</a>'
            # 执行匹配（re.IGNORECASE可选，防止文本大小写变化）
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                traces_path = match.group(1).strip()
                prjna_id = traces_path.split("acc=")[-1]
                return(prjna_id)
            else:
                raise RuntimeError(
                    "解析出错！检测到页面应包含原始数据，但未匹配到SRA Run Selector链接。\n")
        else:
            return('processed')
    except requests.exceptions.HTTPError as e:
        print(f"页面请求失败（HTTP错误）：{e.response.status_code}")
        return None
    except Exception as e:
        print(f"未知错误：{str(e)}")
        return None

def get_info(project_id,output_path,database_name='geo'):
    os.makedirs(output_path, exist_ok=True)
    if database_name == 'ena':
        return get_info_ena(project_id,output_path) 
    elif database_name == 'geo':
        if project_id.startswith('PRJNA'):
            return prjna_info(project_id,output_path)
        elif project_id.startswith('GSE'):
            GEO_url='https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+project_id
            geo_data = judge_geo_data_availability(GEO_url)
            if geo_data is None:
                raise ValueError("页面解析失败：内容不符合预期。")
            elif geo_data == 'processed':
                pass
            else:
                return prjna_info(geo_data,output_path)
    else:
        raise ValueError(f"不支持的数据库：{database_name}")    

def load_srr_gsm_from_local(output_path, gse_id):
    """
    从本地 gsm_srr.txt 加载 SRR-GSM 映射字典
    example:
    GSMXXX SRRXXX1 SRRXXX2 
    GSMXX2 SRRXXX3 SRRXXX4
    """
    txt_path = os.path.join(output_path, 'gsm_srr.txt')
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"未找到 {txt_path} 文件，请先生成这个文件")
    srr_gsm_dict = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                gsm = parts[0]
                srrs = parts[1].split()
                for srr in srrs:
                    srr_gsm_dict[srr] = gsm
    return srr_gsm_dict