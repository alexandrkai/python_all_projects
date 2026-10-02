import os
from pathlib import Path

current_file = Path(__file__).resolve()

PATH_APPLICATION_FOLDER = current_file.parent.parent
PATH_CONFIG_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "config")
PATH_DATA_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "data")
PATH_LOG_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "logs")