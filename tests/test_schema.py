# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__":
    from sys import path
    from os.path import dirname
    from flask import request, url_for
    import unittest

    path.append(dirname(path[0]))
    from test_setup import BasicTestSetup
    from flaskinventory import dgraph
    from flaskinventory.main.model import Schema


class TestSchema(BasicTestSetup):

    def test_schema_generation(self):
        Schema.generate_dgraph_schema()

if __name__ == "__main__":
    unittest.main(verbosity=1)
