# Copyright (c) 2024 FassihFayyaz
# This file is part of Shorts Creator.
# Shorts Creator is licensed under the MIT License. See the LICENSE file for details.

import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QLabel, QScrollArea, QTimeEdit, QMessageBox, 
                             QLineEdit, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QPixmap, QIcon
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, ColorClip
from moviepy.video.tools.subtitles import SubtitlesClip
import moviepy.config as conf
import whisper
import webbrowser

# Set the path to ImageMagick binary
# Replace 'C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe' with the actual path on your system
conf.change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

class TimestampWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()

        self.time_edit_start = QTimeEdit()
        self.time_edit_start.setDisplayFormat("HH:mm:ss")
        self.time_edit_start.setTimeRange(QTime(0, 0, 0), QTime(23, 59, 59))

        self.time_edit_end = QTimeEdit()
        self.time_edit_end.setDisplayFormat("HH:mm:ss")
        self.time_edit_end.setTimeRange(QTime(0, 0, 0), QTime(23, 59, 59))

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter title here")

        layout.addWidget(QLabel("Start:"))
        layout.addWidget(self.time_edit_start)
        layout.addWidget(QLabel("End:"))
        layout.addWidget(self.time_edit_end)
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_edit)
        self.setLayout(layout)

    def get_start_time(self):
        time = self.time_edit_start.time()
        return time.hour() * 3600 + time.minute() * 60 + time.second()

    def get_end_time(self):
        time = self.time_edit_end.time()
        return time.hour() * 3600 + time.minute() * 60 + time.second()

    def get_title(self):
        return self.title_edit.text().strip()

class VideoClipper(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.output_folder = ""
        self.timestamp_pairs = []
        self.video_fps = None
        self.whisper_model = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Shorts Creator By FF')
        self.setGeometry(100, 100, 600, 600)

        layout = QVBoxLayout()

        # Video selection
        self.video_label = QLabel('No video selected')
        layout.addWidget(self.video_label)

        video_button = QPushButton('Browse Video')
        video_button.clicked.connect(self.browse_video)
        layout.addWidget(video_button)

        # Output folder selection
        self.output_label = QLabel('No output folder selected')
        layout.addWidget(self.output_label)

        output_button = QPushButton('Choose Output Folder')
        output_button.clicked.connect(self.choose_output_folder)
        layout.addWidget(output_button)

        # Resolution and Aspect Ratio
        resolution_layout = QHBoxLayout()
        self.resolution_edit = QLineEdit()
        self.resolution_edit.setPlaceholderText("Enter resolution (e.g., 1080x1920)")
        resolution_layout.addWidget(QLabel("Resolution:"))
        resolution_layout.addWidget(self.resolution_edit)

        self.aspect_ratio_edit = QLineEdit()
        self.aspect_ratio_edit.setPlaceholderText("Enter aspect ratio (e.g., 9:16)")
        resolution_layout.addWidget(QLabel("Aspect Ratio:"))
        resolution_layout.addWidget(self.aspect_ratio_edit)
        layout.addLayout(resolution_layout)

        # Alignment options
        alignment_layout = QHBoxLayout()
        alignment_layout.addWidget(QLabel("Alignment:"))
        self.alignment_combo = QComboBox()
        self.alignment_combo.addItems(["None", "Left", "Right"])
        alignment_layout.addWidget(self.alignment_combo)
        layout.addLayout(alignment_layout)

        # Timestamp section
        self.timestamp_layout = QVBoxLayout()
        self.add_timestamp_pair()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(self.timestamp_layout)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Add more timestamps button
        add_timestamp_button = QPushButton('Add More Timestamps')
        add_timestamp_button.clicked.connect(self.add_timestamp_pair)
        layout.addWidget(add_timestamp_button)

        # Subtitle options
        self.create_subtitles_checkbox = QCheckBox('Create Subtitles')
        layout.addWidget(self.create_subtitles_checkbox)

        self.burn_subtitles_checkbox = QCheckBox('Burn Subtitles')
        layout.addWidget(self.burn_subtitles_checkbox)

        # Cut video button
        cut_button = QPushButton('Create Clips')
        cut_button.clicked.connect(self.cut_video)
        layout.addWidget(cut_button)

        # Add Buy Me a Coffee button
        coffee_button = QPushButton("Buy Me a Coffee")
        coffee_button.setFixedSize(217, 60)  # Set the button size
        
        # Create QIcon from QPixmap
        coffee_pixmap = QPixmap('path_to_buymeacoffee_button_image.png')  # Replace with actual path
        coffee_icon = QIcon(coffee_pixmap)
        
        coffee_button.setIcon(coffee_icon)
        coffee_button.setIconSize(coffee_pixmap.size())
        coffee_button.setStyleSheet("""
            QPushButton {
                background-color: #FFDD00;
                border: none;
                border-radius: 5px;
                padding: 10px;
                color: #000000;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFE838;
            }
        """)
        coffee_button.clicked.connect(self.open_buymeacoffee)
        layout.addWidget(coffee_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def open_buymeacoffee(self):
        webbrowser.open('https://buymeacoffee.com/fassih')

    def browse_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.video_path = file_name
            self.video_label.setText(f'Selected video: {os.path.basename(file_name)}')
            
            # Verify that the video can be opened and get its FPS
            try:
                with VideoFileClip(self.video_path) as video:
                    self.video_fps = video.fps
                    if self.video_fps is None or self.video_fps <= 0:
                        self.video_fps = self.estimate_fps(video)
                    QMessageBox.information(self, "Info", f"Video FPS: {self.video_fps}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open video file: {str(e)}")
                self.video_path = ""
                self.video_label.setText('No video selected')

    def estimate_fps(self, video):
        # Attempt to estimate FPS by analyzing a few frames
        try:
            frame_count = 0
            for i, frame in enumerate(video.iter_frames()):
                frame_count += 1
                if i >= 100:  # Analyze up to 100 frames
                    break
            estimated_fps = frame_count / video.duration
            if estimated_fps <= 0:
                estimated_fps = 30  # Fallback to default if estimation fails
            return estimated_fps
        except:
            return 30  # Fallback to default if any error occurs

    def choose_output_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder_name:
            self.output_folder = folder_name
            self.output_label.setText(f'Output folder: {folder_name}')

    def add_timestamp_pair(self):
        timestamp_widget = TimestampWidget()
        self.timestamp_layout.addWidget(timestamp_widget)
        self.timestamp_pairs.append(timestamp_widget)

    def crop_video(self, clip, target_width, target_height, alignment):
        current_w, current_h = clip.w, clip.h
        target_aspect_ratio = target_width / target_height
        current_aspect_ratio = current_w / current_h

        if current_aspect_ratio > target_aspect_ratio:
            # Video is wider than target, crop the width
            new_w = int(current_h * target_aspect_ratio)
            new_h = current_h
            x_center = current_w // 2
            if alignment == "Left":
                x1 = 0
            elif alignment == "Right":
                x1 = current_w - new_w
            else:  # Center
                x1 = x_center - (new_w // 2)
            y1 = 0
        else:
            # Video is taller than target, crop the height
            new_w = current_w
            new_h = int(current_w / target_aspect_ratio)
            y_center = current_h // 2
            x1 = 0
            y1 = y_center - (new_h // 2)

        return clip.crop(x1=x1, y1=y1, width=new_w, height=new_h)

    def cut_video(self):
        if not self.video_path or not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select a video and output folder.")
            return

        if self.video_fps is None or self.video_fps <= 0:
            QMessageBox.warning(self, "Warning", "Invalid FPS detected. Using default value of 30.")
            self.video_fps = 30

        resolution = self.resolution_edit.text().strip()
        if resolution:
            try:
                target_width, target_height = map(int, resolution.split('x'))
            except ValueError:
                QMessageBox.warning(self, "Warning", "Invalid resolution format. Please use 'widthxheight'.")
                return
        else:
            target_width, target_height = None, None

        alignment = self.alignment_combo.currentText()

        try:
            video = VideoFileClip(self.video_path)
            
            # Transcribe the entire video once
            if self.create_subtitles_checkbox.isChecked():
                if not self.whisper_model:
                    self.whisper_model = whisper.load_model("base")
                result = self.whisper_model.transcribe(self.video_path)

            for i, timestamp_widget in enumerate(self.timestamp_pairs):
                start_time = timestamp_widget.get_start_time()
                end_time = timestamp_widget.get_end_time()
                title = timestamp_widget.get_title()
                if not title:
                    title = f"clip_{i+1}"

                if start_time >= end_time:
                    QMessageBox.warning(self, "Warning", f"Invalid timestamp range for clip {i+1}.")
                    continue

                subclip = video.subclip(start_time, end_time)

                if target_width and target_height:
                    subclip = self.crop_video(subclip, target_width, target_height, alignment)

                subclip_path = os.path.join(self.output_folder, f"{title}.mp4")

                if self.create_subtitles_checkbox.isChecked():
                    subtitles_path = os.path.join(self.output_folder, f"{title}.srt")
                    self.create_subtitles_for_clip(result, subtitles_path, start_time, end_time)
                    if self.burn_subtitles_checkbox.isChecked():
                        subclip = self.burn_subtitles(subclip, subtitles_path)

                subclip.write_videofile(subclip_path, fps=self.video_fps)
                QMessageBox.information(self, "Success", f"Clip {title} created successfully!")

            video.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the video: {str(e)}")

    def create_subtitles_for_clip(self, transcription_result, subtitles_path, start_time, end_time):
        with open(subtitles_path, 'w', encoding='utf-8') as f:
            subtitle_id = 1
            for segment in transcription_result["segments"]:
                segment_start = segment["start"]
                segment_end = segment["end"]
                
                # Check if the segment overlaps with the clip
                if segment_end > start_time and segment_start < end_time:
                    # Adjust timings relative to the clip start
                    adjusted_start = max(0, segment_start - start_time)
                    adjusted_end = min(end_time - start_time, segment_end - start_time)
                    
                    # Format timings as SRT format (HH:MM:SS,mmm)
                    start_str = self.format_time(adjusted_start)
                    end_str = self.format_time(adjusted_end)
                    
                    f.write(f"{subtitle_id}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{segment['text'].strip()}\n\n")
                    
                    subtitle_id += 1

    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

    def time_to_seconds(self, time_str):
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s.replace(',', '.'))

    def create_word_clip(self, word, start, end, video_size, font_size=30, bold=False, bottom_gap=50):
        font = 'Arial-Bold' if bold else 'Arial'
        
        def make_animation(t):
            if t < 0.1:  # Duration of pop-up effect (100ms)
                return 1 + 0.3 * (1 - t/0.1)  # Start 30% larger and shrink to normal size
            else:
                return 1

        txt_clip = (TextClip(word, font=font, fontsize=font_size, color='yellow')
                    .set_position(('center', video_size[1] - bottom_gap))  # Customizable bottom gap
                    .set_start(start)
                    .set_end(end)
                    .resize(make_animation))

        return txt_clip

    def word_by_word_subtitles(self, video_clip, subtitles_path, font_size=30, bold=False, bottom_gap=50):
        word_clips = []
        video_size = video_clip.size
        
        with open(subtitles_path, 'r', encoding='utf-8') as file:
            content = file.read()

        subtitle_blocks = re.split(r'\n\n+', content.strip())
        
        for block in subtitle_blocks:
            lines = block.split('\n')
            if len(lines) >= 3:  # Ensure it's a valid subtitle block
                timing = lines[1]
                text = ' '.join(lines[2:])
                
                start_time, end_time = map(self.time_to_seconds, timing.split(' --> '))
                words = text.split()
                
                if words:
                    word_duration = (end_time - start_time) / len(words)
                    
                    for i, word in enumerate(words):
                        word_start = start_time + i * word_duration
                        word_end = word_start + word_duration
                        word_clips.append(self.create_word_clip(word, word_start, word_end, video_size, 
                                                                font_size=font_size, bold=bold, bottom_gap=bottom_gap))

        return CompositeVideoClip([video_clip] + word_clips)

    def burn_subtitles(self, video_clip, subtitles_path, font_size=48, bold=True, bottom_gap=80):
        return self.word_by_word_subtitles(video_clip, subtitles_path, font_size=font_size, bold=bold, bottom_gap=bottom_gap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoClipper()
    ex.show()
    sys.exit(app.exec_())
