import os
import sys
import subprocess
import re
import shutil
import tempfile
import traceback
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
import seaborn as sns
from tkinter import ttk
from tkinter.messagebox import askyesno
from natsort import natsorted
from tqdm import tqdm
from scipy.special import erf

script_dirpath = os.path.dirname(os.path.realpath(__file__))
src_path = os.path.join(os.path.dirname(script_dirpath))
sys.path.insert(0, src_path)

import apps, prompts, load

# expand dataframe beyond page width in the terminal
# pd.set_option('display.max_columns', 20)
# pd.set_option('display.max_rows', 300)
# pd.set_option('display.precision', 3)
# pd.set_option('display.expand_frame_repr', False)

# Select experiment path
src_listdir = os.listdir(src_path)
main_idx = [i for i, f in enumerate(src_listdir) if f.find('main_') !=- 1][0]
main_filename = src_listdir[main_idx]
NUM = re.findall('v(\d+).py', main_filename)[0]
vNUM = f'v{NUM}'
run_num = prompts.single_entry_messagebox(
    entry_label='Analysis run number: ', input_txt='1', toplevel=False
).entry_txt

h5_name = '4_spotFIT_data'
h5_filename = f'{run_num}_{h5_name}_{vNUM}.h5'

selected_path = prompts.folder_dialog(
    title='Select folder with multiple experiments, the TIFFs folder or '
    'a specific Position_n folder'
)

if not selected_path:
    exit('Execution aborted.')

selector = load.select_exp_folder()

(main_paths, prompts_pos_to_analyse, run_num, tot,
is_pos_path, is_TIFFs_path) = load.get_main_paths(selected_path, vNUM)

TIFFs_paths = main_paths

dfs = []
keys = []
for TIFFs_path in TIFFs_paths:
    exp_path = os.path.dirname(TIFFs_path)
    exp_name = os.path.basename(exp_path)
    TIFFs_path = os.path.join(exp_path, 'TIFFs')
    pos_filenames = [
        p for p in os.listdir(TIFFs_path)
        if p.find('Position_')!=-1
        and os.path.isdir(os.path.join(TIFFs_path, p))
    ]
    # print(f'Loading experiment {os.path.dirname(TIFFs_path)}...')
    for pos in tqdm(pos_filenames, ncols=100):
        spotmax_out_path = os.path.join(TIFFs_path, pos, 'spotMAX_output')
        h5_path = os.path.join(spotmax_out_path, h5_filename)
        if os.path.exists(h5_path):
            try:
                df_h5 = pd.read_hdf(h5_path, key='frame_0')
            except Exception as e:
                print('')
                print('-------------------------')
                traceback.print_exc()
                print('-------------------------')
                continue

            A_fit = df_h5['A_fit']
            s_z = df_h5['sigma_z_fit']
            s_y = df_h5['sigma_y_fit']
            s_x = df_h5['sigma_x_fit']
            B_fit = df_h5['B_fit']

            wrong_I_foregr = df_h5['I_foregr'].copy()

            zyx_sigma = np.array([s_z, s_y, s_x])
            zyx_c1 = -1.96 * zyx_sigma
            zyx_c2 = 1.96 * zyx_sigma

            # Substitute variable x --> t to apply erf
            t_z1, t_y1, t_x1 = zyx_c1 / (np.sqrt(2)*zyx_sigma)
            t_z2, t_y2, t_x2 = zyx_c2 / (np.sqrt(2)*zyx_sigma)
            s_tz, s_ty, s_tx = (zyx_sigma) * np.sqrt(np.pi/2)
            D_erf_z = erf(t_z2)-erf(t_z1)
            D_erf_y = erf(t_y2)-erf(t_y1)
            D_erf_x = erf(t_x2)-erf(t_x1)
            I_foregr = A_fit*s_tz*s_ty*s_tx*D_erf_z*D_erf_y*D_erf_x
            I_tot = I_foregr + (B_fit*np.prod(zyx_c2-zyx_c1, axis=0))

            df_h5['I_foregr'] = I_foregr
            df_h5['I_tot'] = I_tot

            temp_dirpath = tempfile.mkdtemp()
            HDF_temp_path = os.path.join(temp_dirpath, h5_filename)
            store_HDF = pd.HDFStore(
                HDF_temp_path, mode='w', complevel=5, complib='zlib'
            )
            store_HDF.append('frame_0', df_h5)
            store_HDF.close()
            shutil.move(HDF_temp_path, h5_path)
            shutil.rmtree(temp_dirpath)
