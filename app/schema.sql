DROP TABLE IF EXISTS Video;
DROP TABLE IF EXISTS Subtitle;
DROP TABLE IF EXISTS ObjectDetectionModel;
DROP TABLE IF EXISTS Process;

CREATE TABLE Video (
    video_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    fps INTEGER,
    width INTEGER,
    height INTEGER,
    frames_path TEXT,
    labels_path TEXT
);

CREATE TABLE Subtitle (
    subtitle_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    preprocessed_subtitle_path TEXT,
    font_color TEXT,
    default_position INTEGER,
    bg_transparency INTEGER,
    positioned_subtitle_path TEXT
);

CREATE TABLE ObjectDetectionModel (
    model_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    filepath TEXT NOT NULL
);

CREATE TABLE Process (
    process_id INTEGER PRIMARY KEY,
    url_path TEXT UNIQUE NOT NULL,
    video_id INTEGER,
    subtitle_id INTEGER,
    model_id INTEGER,
    object_detect TEXT,
    FOREIGN KEY (video_id) REFERENCES Video(video_id) ON DELETE CASCADE,
    FOREIGN KEY (subtitle_id) REFERENCES Subtitle(subtitle_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES ObjectDetectionModel(model_id)
);

INSERT INTO ObjectDetectionModel (name, filepath)
VALUES
    ('yolov7', 'static/model/yolov7.pt'),
    ('yolov7-tiny', 'static/model/yolov7-tiny.pt');