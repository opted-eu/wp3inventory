import sys
import json
import pydgraph
from colorama import init, deinit, Fore, Style

def main():
    init()
    print(Fore.RED + 'WARNING!' + Style.RESET_ALL + " You are about to bulk insert test data.")
    user_warning = input('Are you sure you want to proceed? (y/n): ')
    
    if user_warning.lower() != 'y':
        print('Aborted')
        sys.exit()
    
    # load sample_data
    with open('./data/sample_data_plain.rdf', 'r') as f:
        sample_data = f.read()

    with open('./data/countries_noaustria.json', 'r') as f:
        countries = json.load(f)
    
    client_stub = pydgraph.DgraphClientStub('localhost:9080')
    client = pydgraph.DgraphClient(client_stub)
    
    # create transaction
    txn = client.txn()

    try:
        txn.mutate(set_nquads=sample_data)
        txn.commit()
    finally:
        txn.discard()
    
    txn = client.txn()

    try:
        txn.mutate(set_obj=countries)
        txn.commit()
    finally:
        txn.discard()    

    print(Fore.GREEN + 'DONE!' + Style.RESET_ALL)
    deinit()

if __name__ == '__main__':
    main()