import datetime
from pathlib import Path
import sys
import requests
import json
import logging
from logging.handlers import TimedRotatingFileHandler

# first create a backup folder, e.g. /mnt/public/backup

if __name__ == '__main__':

    this_file = Path(__file__).resolve()
    log_file = this_file.parent / 'backup.log'
    config_file = this_file.parent / 'backup.json'

    logger = logging.getLogger()
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=7)

    # file_handler = logging.FileHandler(LOGGING_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info('Starting backup...')

    try:
        with open(config_file, 'rb') as f:
            config = json.load(f)
    except FileNotFoundError as e:
        logger.error('Could not open config file', e)


    dgraph = "http://localhost:8080/admin"
    backup_timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
    backupfolder = Path(config['backup_path']) / backup_timestamp

    query = 'mutation { export(input: {destination: "' + str(backupfolder) + '"}) { response { message code } } }'

    payload = {"query": query}

    r = requests.post(dgraph, json=payload)

    if r.status_code != 200:
        logger.error(f'No response from DGraph! Status code: {r.status_code}')
        sys.exit(1)

    if "errors" in r.json().keys():
        logger.error(r.json()['error'])
        sys.exit(1)

    logger.info('DGraph backup successful...')

    backup_output = [child for child in backupfolder.iterdir()]

    output_folder = backup_output[0]

    logger.info('Uploading backup...')
    folder_token = config['ucloud_token']
    ucloud_url = config['ucloud_url']

    upload_session = requests.Session()
    upload_session.auth = (folder_token, '')

    upload_url = f'{ucloud_url}{backup_timestamp}/'
    upload_session.request('MKCOL', upload_url)

    for item in output_folder.iterdir():
        with open(item, 'rb') as f:
            destination_file = upload_url + item.name
            upload = upload_session.put(destination_file, f)

    if upload.status_code != 201:
        logger.error(f"Could not upload Backup to ucloud")
        sys.exit(1)
    
    logger.info('Done!')