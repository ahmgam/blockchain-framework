
CREATE TABLE IF NOT EXISTS states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    timecreated TEXT NOT NULL,
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    details TEXT
);
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    timecreated TEXT NOT NULL,
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    needed_uav INTEGER NOT NULL,
    needed_ugv INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS task_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    timecreated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    node_type TEXT NOT NULL,
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    target_id INTEGER NOT NULL,
    commit_id INTEGER NOT NULL,
    path_points TEXT NOT NULL,
    distance REAL NOT NULL,
    timecreated TEXT NOT NULL
);
