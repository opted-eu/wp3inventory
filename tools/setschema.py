import sys
from os.path import dirname
sys.path.append(dirname(sys.path[0]))

import pydgraph
import colorama
from colorama import Fore, Style
from flaskinventory.main.model import Schema

def main():
    colorama.init()
    print(Fore.RED + 'WARNING!' + Style.RESET_ALL + " You are about to delete all data in DGraph.")
    user_warning = input('Are you sure you want to proceed? (y/n): ')
    
    if user_warning.lower() != 'y':
        print('Aborted')
        sys.exit()
    
    # load schema
    # with open('./data/schema.dgraph', 'r') as f:
    #     schema = f.read()
    schema = Schema.generate_dgraph_schema()
    
    client_stub = pydgraph.DgraphClientStub('localhost:9080')
    client = pydgraph.DgraphClient(client_stub)
    # Drop All - discard all data and start from a clean slate.
    client.alter(pydgraph.Operation(drop_all=True))

    # Set schema.
    client.alter(pydgraph.Operation(schema=schema))
    client_stub.close()
    print(Fore.GREEN + 'DONE!' + Style.RESET_ALL)
    colorama.deinit()

if __name__ == '__main__':
    main()