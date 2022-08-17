class InventoryValidationError(Exception):
    def __init__(self, msg='Value provided could not be validated', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)

class InventoryPermissionError(Exception):
    def __init__(self, msg='You do not have the required permissions', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)

class InventoryDatabaseError(Exception):
    def __init__(self, msg='Could not get entry from database', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
