import datetime
import os
import requests
import json
# first create a backup folder, e.g. /mnt/public
# chmod +777 /mnt/public/

with open('tools/backup.json', 'rb') as f:
    config = json.load(f)

dgraph = "http://localhost:8080/admin"
backup_timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
backupfolder = os.path.abspath(config['backup_path'] + backup_timestamp)

query = 'mutation { export(input: {destination: "' + backupfolder + '"}) { response { message code } } }'

payload = {"query": query}

r = requests.post(dgraph, json=payload)

if r.status_code != 200:
    print('fail')

if "errors" in r.json().keys():
    print('fail')

output_folder = os.path.join(backupfolder, os.listdir(backupfolder)[0])
files = os.listdir(output_folder)

folder_token = config['ucloud_token']
ucloud_url = config['ucloud_url']

upload_session = requests.Session()
upload_session.auth = (folder_token, '')

upload_url = f'{ucloud_url}{backup_timestamp}/'
upload_session.request('MKCOL', upload_url)

for item in files:
    item_path = os.path.join(output_folder, item)
    with open(item_path, 'rb') as f:
        destination_file = upload_url + item
        upload = upload_session.put(destination_file, f)

if upload.status_code != 201:
    error_msg = f"Could not upload Backup to ucloud"


# except Exception as e:
#     error_msg = f"Could not upload to GDrive! {e}"
#     logger.error(error_msg)
#     os.remove(OUTPUT_ARTICLES)
#     if input_args.comments:
#         os.remove(OUTPUT_COMMENTS)
#     if input_args.ticker:
#         os.remove(OUTPUT_TICKER)
#     if input_args.comments and input_args.ticker:
#         os.remove(OUTPUT_TICKERCOMMENTS)
#     logjob_object.handle_error(error_msg)