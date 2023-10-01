import os
import cv2

def get_fps(video_path: str):
    cap = cv2.VideoCapture(video_path)
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    cap.release()
    return fps

def get_width(video_path: str):
    cap = cv2.VideoCapture(video_path)
    height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    return height

def get_height(video_path: str):
    cap = cv2.VideoCapture(video_path)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return height

def extract_frames(video_path: str, frames_list: list, frame_out_path: str):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0

    if not os.path.exists(frame_out_path): 
        os.makedirs(frame_out_path)

    while True:
        cap.read()
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1

        if frame_count in frames_list:
            frame_filename = os.path.join(frame_out_path, f"{frame_count}.jpg")
            cv2.imwrite(frame_filename, frame)

        if frame_count > frames_list[-1]: break

    cap.release()
    return frame_out_path