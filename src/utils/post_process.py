import os
import sys
import subprocess
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesno
from natsort import natsorted
from tqdm import tqdm

script_dirpath = os.path.dirname(os.path.realpath(__file__))
src_path = os.path.dirname(script_dirpath)
sys.path.insert(0, src_path)

import load, prompts, apps, core

class listbox_selector:
    def __init__(
            self, label_txt, lb_items, win_title='Listbox',
            selectmode='browse'
        ):
        root = tk.Tk()
        root.geometry('+800+400')
        root.title(win_title)
        root.lift()
        root.attributes("-topmost", True)
        self.selectmode = selectmode
        tk.Label(root,
                 text=label_txt,
                 font=(None, 11)
                 ).grid(row=0, column=0, pady=(10, 5), padx=10)

        width = max([len(item) for item in lb_items])+5

        self.lb = tk.Listbox(
            root, width=width, selectmode=selectmode
        )
        self.lb.grid(row=1, column=0, pady=(0,10))

        for i, item in enumerate(lb_items):
            self.lb.insert(i+1, item)

        ttk.Button(root, text='   Ok   ', command=self._close
                  ).grid(row=2, column=0, pady=(0,10))

        root.protocol("WM_DELETE_WINDOW", self._abort)
        self.root = root
        root.mainloop()

    def _close(self):
        if self.selectmode == 'extended':
            sel_idx = self.lb.curselection()
            self.lb_selection = [self.lb.get(i) for i in sel_idx]
        else:
            self.lb_selection = self.lb.get(self.lb.curselection())
        self.root.quit()
        self.root.destroy()

    def _abort(self):
        self.root.quit()
        self.root.destroy()
        exit('Execution aborted by the user')

class beyond_listdir_pos:
    def __init__(self, folder_path, spotMAX_data_foldername):
        self.bp = apps.tk_breakpoint()
        self.folder_path = folder_path
        self.TIFFs_paths = []
        self.count_recursions = 0
        self.spotMAX_data_foldername = spotMAX_data_foldername
        self.listdir_recursion(folder_path)
        if not self.TIFFs_paths:
            raise FileNotFoundError(f'Path {folder_path} is not valid!')
        self.all_exp_info = self.count_analysed_pos()

    def listdir_recursion(self, folder_path):
        if os.path.isdir(folder_path):
            listdir_folder = natsorted(os.listdir(folder_path))
            contains_pos_folders = any([name.find('Position_')!=-1
                                        for name in listdir_folder])
            if not contains_pos_folders:
                contains_TIFFs = any([name=='TIFFs'
                                      for name in listdir_folder])
                contains_mitoQ_data = any([name==self.spotMAX_data_foldername
                                           for name in listdir_folder])
                rec_count_ok = self.count_recursions < 15
                if contains_TIFFs and contains_mitoQ_data and rec_count_ok:
                    self.TIFFs_paths.append(f'{folder_path}/'
                                            f'{self.spotMAX_data_foldername}')
                elif contains_TIFFs and rec_count_ok:
                    self.TIFFs_paths.append(f'{folder_path}/TIFFs')
                elif rec_count_ok:
                    for name in listdir_folder:
                        subfolder_path = f'{folder_path}/{name}'
                        self.listdir_recursion(subfolder_path)
                    self.count_recursions += 1
                else:
                    raise RecursionError(
                          'Recursion went too deep and it was aborted '
                          'Check that the experiments contains the TIFFs folder')
            else:
                exp_path = os.path.dirname(os.path.dirname(folder_path))
                contains_mitoQ_data = any([name==self.spotMAX_data_foldername
                                           for name in listdir_folder])
                self.TIFFs_paths.append(exp_path)

    def get_rel_path(self, path):
        rel_path = ''
        parent_path = path
        count = 0
        while parent_path != self.folder_path or count==10:
            if count > 0:
                rel_path = f'{os.path.basename(parent_path)}/{rel_path}'
            parent_path = os.path.dirname(parent_path)
            count += 1
        rel_path = f'.../{rel_path}'
        return rel_path

    def count_analysed_pos(self):
        all_exp_info = []
        valid_TIFFs_path = []
        for path in self.TIFFs_paths:
            rel_path = self.get_rel_path(path)
            foldername = os.path.basename(path)
            if foldername == self.spotMAX_data_foldername:
                exp_info = f'{rel_path} (All Pos. DataFrames ALREADY generated)'
            else:
                exp_info = f'{rel_path} (DataFrames NOT present!)'
            all_exp_info.append(exp_info)
        return all_exp_info

#expand dataframe beyond page width in the terminal
pd.set_option('display.max_columns', 20)
pd.set_option('display.max_rows', 300)
pd.set_option('display.precision', 3)
pd.set_option('display.expand_frame_repr', False)

# Select experiment path
src_listdir = os.listdir(src_path)
main_idx = [i for i, f in enumerate(src_listdir) if f.find('main_') !=- 1][0]
main_filename = src_listdir[main_idx]
NUM = re.findall('v(\d+).py', main_filename)[0]
vNUM = f'v{NUM}'
selected_path = prompts.folder_dialog(
    title="Select folder containing valid experiments"
)
spotMAX_data_foldername = ''
if selected_path.find('TIFFs') != -1:
    selected_paths = [selected_path]
    TIFFs_path = selected_path
else:
    beyond_listdir_pos = beyond_listdir_pos(
        selected_path, spotMAX_data_foldername
    )
    selector = load.select_exp_folder()
    selector.run_widget(beyond_listdir_pos.all_exp_info,
                        title='Post-process spotMAX results',
                        label_txt='Select experiment to post-process',
                        full_paths=beyond_listdir_pos.TIFFs_paths,
                        showinexplorer_button=True,
                        all_button=True)
    selected_paths = selector.paths
    TIFFs_path = beyond_listdir_pos.TIFFs_paths[0]

foldername = os.path.basename(TIFFs_path)
if foldername.find('Position_') != -1:
    TIFFs_path = os.path.dirname(TIFFs_path)
    pos_foldernames = [foldername]
else:
    ls_TIFFs_path = os.listdir(TIFFs_path)
    pos_foldernames = [
        p for p in ls_TIFFs_path
        if p.find('Position_') != -1
        and os.path.isdir(os.path.join(TIFFs_path, p))
    ]

pos_path = os.path.join(TIFFs_path, pos_foldernames[0])
scan_run_num = prompts.scan_run_nums(vNUM)
run_nums = scan_run_num.scan(pos_path)
if len(run_nums) > 1:
    run_num = scan_run_num.prompt(
        run_nums, msg='Select run number to post-process: '
    )
else:
    run_num = 1

gop_metrics = [
    'effsize_cohen_s',
    'effsize_hedge_s',
    'effsize_glass_s',
    'effsize_cliffs_s',
    'effsize_cohen_pop',
    'effsize_hedge_pop',
    'effsize_glass_pop',
    'vox_spot',
    'peak_to_background ratio',
    '|spot|:|ref| p-value (t)'
]

gop_metrics_selected = listbox_selector(
    'Select numerical features to use for fitlering\n'
    '(you can select multiple items with Ctrl+click)',
    gop_metrics,
    win_title='Select file name',
    selectmode='extended'
).lb_selection

gop_limits = prompts.multi_entry_messagebox(
    title='Filtering thresholds',
    entries_labels=[f'"{m}" limit:' for m in gop_metrics_selected],
    default_entries=['' for _ in gop_metrics_selected],
    toplevel=False
).entries_txt
gop_limits = [float(m) for m in gop_limits]

h5_name = listbox_selector(
    'Select .h5 file name to post-process:',
    ['0_Orig_data', '1_ellip_test_data',
    '2_p-_test_data', '3_p-_ellip_test_data',
    '4_spotFIT_data'],
    win_title='Select file name').lb_selection

h5_filename = f'{run_num}_{h5_name}_{vNUM}.h5'
ref_csv_filename = f'{run_num}_3_p-_ellip_test_data_Summary_{vNUM}.csv'
new_filename = f'{run_num}_5_post_process_data_Summary_{vNUM}.csv'

spotMAX_data_foldername = f'spotMAX_{vNUM}_run-num{run_num}'

for selected_path in tqdm(selected_paths, ncols=100, unit='experiment'):
    foldername = os.path.basename(selected_path)
    if foldername == spotMAX_data_foldername:
        TIFFs_path = f'{os.path.dirname(selected_path)}/TIFFs'
        pos_foldernames = natsorted([
            p for p in ls_TIFFs_path
            if p.find('Position_') != -1
            and os.path.isdir(os.path.join(TIFFs_path, p))
        ])
    elif foldername == 'TIFFs':
        TIFFs_path = selected_path
        pos_foldernames = natsorted([
            p for p in ls_TIFFs_path
            if p.find('Position_') != -1
            and os.path.isdir(os.path.join(TIFFs_path, p))
        ])
    elif foldername.find('Position_') != -1:
        pos_foldernames = [foldername]
        TIFFs_path = os.path.dirname(selected_path)

    for pos in tqdm(pos_foldernames, ncols=100):
        spotmax_out_path = os.path.join(TIFFs_path, pos, 'spotMAX_output')
        h5_path = os.path.join(spotmax_out_path, h5_filename)
        if not os.path.exists(h5_path):
            print('')
            print('-------------------------')
            print(f'WARNING:  File not found "{h5_path}"')
            print('-------------------------')
            continue
        try:
            df_h5 = pd.read_hdf(h5_path, key='frame_0')
        except Exception as e:
            print('')
            print('-------------------------')
            traceback.print_exc()
            print('-------------------------')
            continue

        df_ref_csv_path = os.path.join(spotmax_out_path, ref_csv_filename)
        df_summary = pd.read_csv(df_ref_csv_path, index_col='Cell_ID')
        df_filtered = df_h5.copy()
        for metric, limit in zip(gop_metrics_selected, gop_limits):
            if metric.find('p-value') != -1:
                df_filtered = df_filtered[df_filtered[metric] < limit]
            else:
                df_filtered = df_filtered[df_filtered[metric] > limit]

            df_summary[f'{metric}_limit'] = limit

        df_summary['num_spots'] = 0
        for ID, df in df_filtered.groupby(level=0):
            df_summary.at[ID, 'num_spots'] = len(df)

        post_process_csv_path = os.path.join(spotmax_out_path, new_filename)
        df_summary.to_csv(post_process_csv_path)
