import inspect

class AccessLevel(object):
    Anon = 0
    User = 1
    Reviewer = 2
    Admin = 10

    def __init__(self):
        attributes = inspect.getmembers(self, lambda a:not(inspect.isroutine(a)))
        self.list_of_tuples = [a for a in attributes if not(a[0].startswith('__') and a[0].endswith('__'))]
        self.list_of_tuples_b = [(a, b) for b, a in self.list_of_tuples]
        self.dict = {key: value for key, value in attributes if not(key.startswith('__') and key.endswith('__'))}

    def __repr__(self) -> str:
        return '<Access Level>'


ACCESS_LEVEL = AccessLevel()
