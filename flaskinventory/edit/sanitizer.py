from flaskinventory.flaskdgraph.dgraph_types import (UID, dict_to_nquad, Scalar)
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory.main.sanitizer import Sanitizer
from flaskinventory.users.constants import USER_ROLES
from flaskinventory import dgraph

import datetime
from dateutil import parser as dateparser


class EditAudienceSizeSanitizer(Sanitizer):

    def __init__(self, uid, data):

        from flask_login import current_user
        from flaskinventory.misc import get_ip

        self.user = current_user
        self.user_ip = get_ip()

        check = self._check_entry(uid)
        if not check:
            raise InventoryValidationError(
                f'Entry can not be edited! UID does not exist: {data["uid"]}')

        if current_user.user_role < USER_ROLES.Reviewer:
            if check.get('entry_added').get('uid') != current_user.id:
                raise InventoryPermissionError(
                    'You do not have the required permissions to edit this entry!')

        self.is_upsert = True
        self.entry_uid = UID(uid)

        self._check_channel()

        self.entry = {"uid": self.entry_uid}
        self.entry = self._add_entry_meta(self.entry)
        if type(data) is not list:
            raise InventoryValidationError('Invalid Data Provided.')
        if len(data) == 0:
            raise InventoryValidationError('No Data Provided.')

        self.data = data

        self.overwrite = {self.entry['uid']: ['audience_size']}

        self.parse_audience_size()

        self.delete_nquads = self._make_delete_nquads()
        nquads = dict_to_nquad(self.entry)
        self.set_nquads = " \n ".join(nquads)

    def _add_entry_meta(self, entry):
        facets = {'timestamp': datetime.datetime.now(
            datetime.timezone.utc),
            'ip': self.user_ip}
        entry['entry_edit_history'] = UID(self.user.uid, facets=facets)

        return entry

    def _make_delete_nquads(self):
        # for upserts, we first have to delete all list type predicates
        # otherwise, the user cannot remove relationships, but just add to them
        del_obj = []
        if not self.upsert_query:
            self.upsert_query = ''

        for key, val in self.overwrite.items():
            for predicate in val:
                del_obj.append({'uid': key, predicate: '*'})

        nquads = [" \n ".join(dict_to_nquad(obj)) for obj in del_obj]
        return " \n ".join(nquads)

    def _check_channel(self):
        query_string = f'{{ q(func: uid({self.entry_uid.query})) {{ channel {{ unique_name }} }} }}'
        channel = dgraph.query(query_string)

        self.channel = channel['q'][0]['channel']['unique_name']

        if self.channel not in ['print', 'facebook']:
            raise InventoryValidationError('Wrong channel! Only Print and Facebook can be edited.')

    def parse_audience_size(self):
        self.entry['audience_size'] = []
        for item in self.data:
            if type(item) is not dict:
                continue
            if 'date' not in item.keys():
                continue
            date = item.pop('date')
            date = dateparser.parse(date)
            facets = {}
            for key, val in item.items():
                if key in ['count']:
                    try:
                        val = int(val)
                    except:
                        raise InventoryValidationError('Wrong data entered! Make sure you only entered whole numbers.')
                facets[key] = val
            self.entry['audience_size'].append(Scalar(date, facets=facets))
        if len(self.entry['audience_size']) == 0:
            raise InventoryValidationError('Invalid Data! None of the provided data points could be parsed.')    
        