class InventoryValidationError(Exception):
    pass

class ValidateNewSource():

    def __init__(self, json):
        if type(json) != dict:
            raise ValueError
        self.json = json
        for key, val in json.items():
            setattr(self, key, val)

    def check_channel(self):
        if self.channel == 'facebook':
            pass