import sys
import pydgraph
from colorama import init, deinit, Fore, Style

def main():
    init()
    print(Fore.RED + 'WARNING!' + Style.RESET_ALL + " You are about to delete all data in DGraph.")
    user_warning = input('Are you sure you want to proceed? (y/n): ')
    
    if user_warning.lower() != 'y':
        print('Aborted')
        sys.exit()
    
    # load schema
    with open('./data/schema.dgraph', 'r') as f:
        schema = f.read()
    
    client_stub = pydgraph.DgraphClientStub('localhost:9080')
    client = pydgraph.DgraphClient(client_stub)
    # Drop All - discard all data and start from a clean slate.
    client.alter(pydgraph.Operation(drop_all=True))

    # Set schema.
    client.alter(pydgraph.Operation(schema=schema))
    client_stub.close()
    print(Fore.GREEN + 'DONE!' + Style.RESET_ALL)
    deinit()

if __name__ == '__main__':
    main()