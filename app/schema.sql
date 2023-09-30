DROP TABLE IF EXISTS Video;
DROP TABLE IF EXISTS Subtitle;
DROP TABLE IF EXISTS Frame;
DROP TABLE IF EXISTS ObjectDetectionModel;
DROP TABLE IF EXISTS ObjectDetect;
DROP TABLE IF EXISTS Process;
DROP TABLE IF EXISTS DetailProcess;

CREATE TABLE Video (
    video_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    fps INTEGER,
    width INTEGER,
    height INTEGER
);

CREATE TABLE Subtitle (
    subtitle_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    processed_subtitle_path TEXT,
    font_color TEXT,
    default_position TEXT,
    bg_transparency TEXT,
    generated_subtitle_path TEXT
);

CREATE TABLE Frame (
    frame_id INTEGER PRIMARY KEY,
    video_id INTEGER,
    subtitle_id INTEGER,
    frame_position INTEGER,
    filepath TEXT NOT NULL,
    label_path TEXT,
    FOREIGN KEY (video_id) REFERENCES Video(video_id),
    FOREIGN KEY (subtitle_id) REFERENCES Subtitle(subtitle_id)
);

CREATE TABLE ObjectDetectionModel (
    model_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    filePath TEXT NOT NULL
);

CREATE TABLE ObjectDetect (
    object_id INTEGER PRIMARY KEY,
    model_id INTEGER,
    class TEXT,
    name TEXT,
    FOREIGN KEY (model_id) REFERENCES ObjectDetectionModel(model_id)
);

CREATE TABLE Process (
    process_id INTEGER PRIMARY KEY,
    random_url TEXT UNIQUE NOT NULL,
    video_id INTEGER,
    subtitle_id INTEGER,
    model_id INTEGER,
    FOREIGN KEY (video_id) REFERENCES Video(video_id),
    FOREIGN KEY (subtitle_id) REFERENCES Subtitle(subtitle_id),
    FOREIGN KEY (model_id) REFERENCES ObjectDetectionModel(model_id)
);

CREATE TABLE DetailProcess (
    detailprocess_id INTEGER PRIMARY KEY,
    process_id INTEGER,
    object_id INTEGER,
    FOREIGN KEY (process_id) REFERENCES Process(process_id),
    FOREIGN KEY (object_id) REFERENCES ObjectDetect(object_id)
);
