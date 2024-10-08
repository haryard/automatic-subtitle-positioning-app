from enum import unique
import os
import re
import subprocess
import pysubs2
import numpy as np
from pysubs2 import SSAEvent
from pysubs2 import time as timeSub
from flask import current_app
 
def hex_to_rgba(hex_color, alpha_percent):
    hex_color = hex_color.lstrip('#')
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    alpha = int(255 - (alpha_percent * 255 / 100))
    return red, green, blue, alpha
 
def process_convert_to_ass(subtitle_path: str, width: int, height: int):
    subtitle_name = os.path.splitext(os.path.basename(subtitle_path))[0]
    subtitle_dir = os.path.dirname(subtitle_path)
    
    # convert subtitle
    path = current_app.root_path
    command = ['mono', os.path.join(path, "ext/YTSubConverter/YTSubConverter.exe"), subtitle_path, os.path.join(subtitle_dir, f"{subtitle_name}.ass")]
    subprocess.run(command, check=True)
    
    subtitle = pysubs2.load(os.path.join(subtitle_dir, f"{subtitle_name}.ass"))
    new_subtitle = pysubs2.SSAFile()
    
    # process autogenerate sub from youtube
    regex_check = r'\\(an|pos|move)([1-9]|\((((\d+(\.\d+)?),*){2})(((\d+(\.\d+)?),*){2})?((\d+,*){2})?\))'
    if(subtitle[0].end == subtitle[2].start) and (re.search(regex_check, subtitle[0].text) or re.search(regex_check, subtitle[2].text)) is None:
        sub_index = 0
        while sub_index <= len(subtitle):
            if sub_index + 2 > len(subtitle) - 1:
                start = subtitle[-1].start
                end = subtitle[-1].end
                text = subtitle[-1].text
                new_line = SSAEvent(start=start, end=end, text=text)
                new_subtitle.append(new_line)
                break
            if (subtitle[sub_index].end == subtitle[sub_index + 2].start):
                start = subtitle[sub_index].start
                end = subtitle[sub_index].end
                text = subtitle[sub_index].text + "\\N" + subtitle[sub_index + 1].text
                new_line = SSAEvent(start=start, end=end, text=text)
                new_subtitle.append(new_line)
                sub_index = sub_index + 2
            elif (subtitle[sub_index].end == subtitle[sub_index + 1].end):
                start = subtitle[sub_index].start
                end = subtitle[sub_index].end
                text = subtitle[sub_index].text + "\\N" + subtitle[sub_index + 1].text
                new_line = SSAEvent(start=start, end=end, text=text)
                new_subtitle.append(new_line)
                sub_index = sub_index + 2
            else:
                sub_index = sub_index + 1
        new_subtitle.info['PlayResX'] = width 
        new_subtitle.info['PlayResY'] = height
    else:
        new_subtitle = subtitle
        
    # add basic style
    fontSize = round(int(new_subtitle.info['PlayResX']) * 0.0296875, 2)
    marginH  = int(int(new_subtitle.info['PlayResX']) * 0.0234375)
    marginV  = int(int(new_subtitle.info['PlayResY']) * 0.034722)
    outlineW = round(int(new_subtitle.info['PlayResX']) * 0.002344, 2)
    shadowD  = round(int(new_subtitle.info['PlayResX']) * 0.003906, 2)
    base = pysubs2.SSAStyle(fontsize=fontSize, primarycolor=pysubs2.Color(255, 255, 255), backcolor=pysubs2.Color(0,0,0,128), borderstyle=1, outline=outlineW, shadow=shadowD, marginl=marginH, marginr=marginH, marginv=marginV)
    base_bg = pysubs2.SSAStyle(fontsize=fontSize, primarycolor=pysubs2.Color(255, 255, 255), backcolor=pysubs2.Color(0,0,0,128), borderstyle=3, outlinecolor=pysubs2.Color(0,0,0,255), outline=outlineW, shadow=shadowD, marginl=marginH, marginr=marginH, marginv=marginV)
    new_subtitle.styles["base"] = base
    new_subtitle.styles["base-bg"] = base_bg
    
    # assign new style to subtitle
    for line in new_subtitle:
        if re.search(regex_check, line.text) is None:
            line.text = re.sub(r'\{.*?\}', '', line.text)
            line.style = "base"
        else:
            line.text = line.text
    
    new_subtitle_path = os.path.join(subtitle_dir,f"{subtitle_name}_processed.ass")
    new_subtitle.save(new_subtitle_path)
    
    return new_subtitle_path
 
def get_detected_object(label_path: str, frame_start: int, frame_end: int, width: int, height: int, class_list: list):
    data_dict = {}
    file_names = [file for file in os.listdir(label_path) if file.endswith('.txt')]
    for file_number in range(frame_start, frame_end + 1):
        file_name = f'{file_number}.txt'
        if file_name in file_names:
            file_path = os.path.join(label_path, file_name)
            data_list = []
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    parts = line.split()
                    class_number, x_mid, y_mid, w, h = map(float, parts)
                    if int(class_number) in class_list:
                        x1, y1 = x_mid - w/2, y_mid - h/2
                        x2, y2 = x_mid + w/2, y_mid + h/2
                        data_list.append({
                        'x_mid' : round(x_mid, 2),
                        'y_mid' : round(y_mid, 2),
                        'width' : round(w, 2),
                        'height': round(h, 2),
                        'x1': round(x1, 2),
                        'x2': round(x2, 2),
                        'y1': round(y1, 2),
                        'y2': round(y2, 2)})
                    else: continue
            if len(data_list) > 0: data_dict[file_number] = data_list
            else: continue
 
    return data_dict
 
def get_possible_subtitle_position(width: int, height:int):
    box_width = 0.6 * width
    box_height = 0.12 * height
    margin_top = (height - (8 * box_height)) / 2
    margin_top = round(margin_top, 2)
 
    box_info = {}
 
    for row in range(8):
        for col in range(3):
            box_count = row * 3 + col
            
            x_start = col * 0.2 * width
            x_end   = x_start + box_width
            y_start = margin_top + row * box_height
            y_end   = y_start + box_height
            x_mid   = (x_start + x_end) / 2
            y_mid   = (y_start + y_end) / 2
 
            x_mid_percent   = round(x_mid / width, 2)
            y_mid_percent   = round(y_mid / height, 2)
            width_percent   = round(box_width / width, 2)
            height_percent  = round(box_height / height, 2)
            x_start_percent = round(x_start / width, 2)
            x_end_percent   = round(x_end / width, 2)
            y_start_percent = round(y_start / height, 2)
            y_end_percent   = round(y_end / height, 2)
 
            box_info[box_count + 1] = ({
            'x_mid': x_mid_percent,
            'y_mid': y_mid_percent,
            'width': width_percent,
            'height': height_percent,
            'x1': x_start_percent,
            'x2': x_end_percent,
            'y1': y_start_percent,
            'y2': y_end_percent
            })
 
    return box_info
 
def get_order_position(sub_pos:list, default_pos:int):
    list_sub_pos   = list(sub_pos.keys())
    sub_pos_matrix = [list_sub_pos[i:i+(len(list_sub_pos)//3)] for i in range(0, len(list_sub_pos), 3)]
    order_pos      = []
    for row in (sub_pos_matrix if default_pos == 0 else reversed(sub_pos_matrix)):
      order_pos.append(row[1])
      order_pos.append(row[2])
      order_pos.append(row[0])
    return order_pos
 
def calculate_iou(box1, box2):
    area_box1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area_box2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    x_intersection = max(0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
    y_intersection = max(0, min(box1[3], box2[3]) - max(box1[1], box2[1]))
    area_intersection = x_intersection * y_intersection
    iou = area_intersection / (area_box1 + area_box2 - area_intersection)
    return round(iou, 7)
 
def get_best_subtitle_position(sub_pos: list, order_pos: list, frames_dict: list):
    position       = order_pos[0]
    prev_order_pos = [x for x in order_pos]
    frames_list    = list(frames_dict.keys())
    # check if object in one of subtitle position set to that position if that position empty for all frame
    while order_pos:
        pos = order_pos.pop(0)
        for frame in range(len(frames_list)):
            list_iou = []
            for obj in frames_dict[frames_list[frame]]:
                bbox_pos = np.array([sub_pos[pos]['x1'], sub_pos[pos]['y1'], sub_pos[pos]['x2'], sub_pos[pos]['y2']])
                bbox_obj = np.array([obj['x1'], obj['y1'], obj['x2'], obj['y2']])
                iou = calculate_iou(bbox_pos, bbox_obj)
                if iou >= 0.01: list_iou.append(iou)
            if len(list_iou) == 0 and frames_list[frame] == frames_list[-1]: 
                position = pos
                break
            elif len(list_iou) > 0: 
                break  
            else: 
                continue
        if len(list_iou) == 0 and frames_list[frame] == frames_list[-1]:
            break
        else:
            continue
    # check probability of each position if all area detected set set position to the lowest average iou position
    if len(order_pos) == 0:
        prob_pos = {}
        for pos in prev_order_pos:
            prob_frame = []
            for frame in range(len(frames_list)):
                for obj in frames_dict[frames_list[frame]]:
                    bbox_pos = np.array([sub_pos[pos]['x1'], sub_pos[pos]['y1'], sub_pos[pos]['x2'], sub_pos[pos]['y2']])
                    bbox_obj = np.array([obj['x1'], obj['y1'], obj['x2'], obj['y2']])
                    iou = calculate_iou(bbox_pos, bbox_obj)
                    if iou > 0: prob_frame.append(iou)
            if len(prob_frame) > 0: 
                average_iou = sum(prob_frame) / len(prob_frame)
            else: 
                average_iou = 0
            prob_pos[pos] = average_iou
        position = min(prob_pos, key=prob_pos.get)
    return position
 
def get_postioned_ass_tags(sub_pos: list, position: int, width:int, height: int, margin_x:int):
    an_tag = ""
    pos_tag = ""
    list_sub_pos   = list(sub_pos.keys())
    sub_pos_matrix = [list_sub_pos[i:i+(len(list_sub_pos)//3)] for i in range(0, len(list_sub_pos), 3)]
    for row_left in range(len(sub_pos_matrix)):
        if position == sub_pos_matrix[row_left][0]:
            an_tag = "\\an4"
            pos_tag = f"\\pos({margin_x}, {round(sub_pos[position]['y_mid'] * height, 2)})"
        elif position == sub_pos_matrix[row_left][1]:
            an_tag = "\\an5"
            pos_tag = f"\\pos({round(sub_pos[position]['x_mid'] * width, 2)}, {round(sub_pos[position]['y_mid'] * height, 2)})"
        elif position == sub_pos_matrix[row_left][2]:
            an_tag = "\\an6"
            pos_tag = f"\\pos({width - margin_x}, {round(sub_pos[position]['y_mid'] * height, 2)})"
 
    ass_tags = f"{an_tag}{pos_tag}"
    return ass_tags
 
def get_positioned_subtitle(subtitle_path: str, fps: float, label_path: str, default_pos: int, class_selected: list):
    # parsing subtitle name and dir
    sub_dir  = os.path.dirname(subtitle_path)
    sub_name = os.path.splitext(os.path.basename(subtitle_path))[0]
 
    # load and initialize generated positioned subtitle
    subtitle                     = pysubs2.load(subtitle_path)
    positioned_subtitle          = subtitle
    sub_width, sub_height        = int(subtitle.info['PlayResX']), int(subtitle.info['PlayResY'])
    margin_x, margin_y           = positioned_subtitle.styles["base"].marginl, positioned_subtitle.styles["base"].marginv
 
    # set subtitle position
    possible_position = get_possible_subtitle_position(sub_width, sub_height)
    prev_position     = None
 
    # process subtitle
    for line in range(len(positioned_subtitle)):
        # if pattern found in that line continue to next line
        pattern_positioning_tag = r'\\(an|pos|move)([1-9]|\((((\d+(\.\d+)?),*){2})(((\d+(\.\d+)?),*){2})?((\d+,*){2})?\))'
        if re.search(pattern_positioning_tag, positioned_subtitle[line].text) is not None: continue
 
        # set initial value
        frame_start = timeSub.ms_to_frames(positioned_subtitle[line].start, fps)
        frame_end   = timeSub.ms_to_frames(positioned_subtitle[line].end, fps)  
        frames_list = []
        order_pos   = get_order_position(possible_position, default_pos)
        if prev_position is not None: 
          order_pos.insert(1, prev_position)
          unique_list = []
          [unique_list.append(x) for x in order_pos if x not in unique_list]
          order_pos = unique_list
        frames_dict = get_detected_object(label_path, frame_start, frame_end, sub_width, sub_height, class_selected)
        position    = get_best_subtitle_position(possible_position, order_pos, frames_dict) if len(frames_dict) != 0 else order_pos[0]
 
        # positioning subtitle
        prev_position = position
        ass_tag   = get_postioned_ass_tags(possible_position, position, sub_width, sub_height, margin_x)
        positioned_subtitle[line].text = f"{{ {ass_tag} }}{positioned_subtitle[line].text}"
        if len(order_pos) == 0: 
            positioned_subtitle[line].style = "base-bg"
        else: 
            positioned_subtitle[line].style = "base"
 
    positioned_subtitle.save(f'{sub_dir}/{sub_name}_positioned.ass')
    return f'{sub_dir}/{sub_name}_positioned.ass'
 
def set_style(subtitle_path: str, font_color: str, background_transparency: int):
    subtitle = pysubs2.load(subtitle_path)
    fontr, fontg, fontb, bgalpha = hex_to_rgba(font_color, background_transparency)
    style_1 = subtitle.styles["base"].copy()
    style_2 = subtitle.styles["base-bg"].copy()
    style_1.primarycolor = pysubs2.Color(fontr,fontg,fontb)
    style_2.primarycolor = pysubs2.Color(fontr,fontg,fontb)
    style_2.backcolor    = pysubs2.Color(0,0,0,bgalpha)
    subtitle.styles["base"]    = style_1
    subtitle.styles["base-bg"] = style_2 
    subtitle.save(subtitle_path)
