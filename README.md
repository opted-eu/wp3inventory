# Introduction

This is the code repository for the WP3 Inventory, which will contain an interlinked knowledge graph of news sources, media organizations, and data archives in Europe (for details see the [OPTED main page](https://opted.eu/)). Currently, this is a prototype / work in progress.

The WP3 Inventory is a web based application that allows users to

- browse & query the WP3 database
- Add new entries to the database
- edit and update existing entries

## Technical Details

- developed in the Python framework [Flask](https://flask.palletsprojects.com/en/2.0.x/) (most recent version)
- uses [DGraph](https://dgraph.io/) as backend / data storage

# Getting started

1. Clone the repository
2. Install the requirements via pip (`python3 -m pip install -r requirements.txt`)
3. Install DGraph on your local machine (see [official documentation](https://dgraph.io/downloads/))
4. Launch your local DGraph instances (alpha and zero)
5. Launch the inventory via `python3 run.py` 
      - alternatively you can specify a configuration via `python3 run.py --config config.json`
6. Set the data schema to your DGraph instance via `python3 tools/setschema.py`
7. Add sample data to your DGraph instance using `python3 tools/sample_data.py`
8. Open your browser at your localhost with port 5000 (http://127.0.0.1:5000)

# Quick Codebase Walkthrough

```
├── data                  # contains sample data in various formats and the dgraph schem
├── flaskinventory        # root folder for flask
├── README.md             # this file
├── requirements.txt      # python requirements
├── run.py                # Flask launcher
└── tools                 # collection of helper scripts and files for server deployment
```

## Contributing & Bug Fixes

Please contact Paul Balluff for contribution. If you found a problem, just raise an issue here in this repository.

# Other Notes


## User Permissions

Level | Name | Permissions
------|------|------------
0     | Anonymous | View entries
1     | Contributor  | Add entries
2     | Reviewer | + Review & Edit Entries, Invite Users
10    | Admin   | + Change User Permissions 


## Web Dependencies

- Bootstrap 5
- Font Awesome
- Tom-Select
- jquery typeahead
- [bibtex-js](https://github.com/digitalheir/bibtex-js)

## Backups

Currently backups are uploaded to ucloud (for data safety and convenience). If the amount of database dumps gets too large, a different solution would be preferred.

Backups are run by a user with root privileges, because database dumps are created by the `dgraph` user and thus, cannot be manipulated directly by other users. Of course it would be possible to run some `chown` magic though.

Make sure that the `requests` module is installed for the root user.

### Create Backup Settings

create a settings file (`backup.json`) inside the tools folder:

```json
{
    "ucloud_url": "https://ucloud.univie.ac.at/public.php/webdav/",
    "ucloud_token": "secret",
    "backup_path": "/mnt/public/backup/"
}
```

Make sure the directory `backup_path` exists and that the `dgraph` user has rights to write to it.

### Run backup

Simply execute the script `tools/backup.py`.

Add it as cronjob with `crontab -e`

```
0 1 * * * /usr/bin/python3 /home/user/wp3inventory/tools/backup.py
```