from pathlib import Path
import datetime
import json


this_file = Path(__file__).resolve()
log_file = this_file.parent / 'backup.log'
config_file = this_file.parent / 'backup.json'

with open(config_file, 'rb') as f:
    config = json.load(f)

print(config)

backup_timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
backupfolder = Path(config['backup_path']) / backup_timestamp

print(this_file)
print(log_file)
print(backupfolder)

folder_contents = [child for child in this_file.parent.iterdir()]

print(folder_contents)