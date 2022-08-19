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
    with open('./data/sample_data.rdf', 'r') as f:
        sample_data = [line.strip() for line in f]

    # skip first two lines and last line
    sample_data = sample_data[2:]
    sample_data = sample_data[:-3]
    sample_data = "\n".join(sample_data)

    with open('./data/countries_sample.json', 'r') as f:
        countries = json.load(f)
    
    with open('./data/countries_nonopted.json', 'r') as f:
        non_optedcountries = json.load(f)
    
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

    txn = client.txn()

    try:
        txn.mutate(set_obj={'set': non_optedcountries})
        txn.commit()
    finally:
        txn.discard()

    # change all object's entry_review_status to "accepted"
    txn = client.txn()

    query = """{
        q(func: has(dgraph.type)) @filter(NOT type(User) AND NOT type(dgraph.graphql)) { v as uid } }"""
    nquad = """
        uid(v) <entry_review_status> "accepted" .
        uid(v) <dgraph.type> "Entry" .
        """
    mutation = txn.create_mutation(set_nquads=nquad)
    request = txn.create_request(query=query, mutations=[mutation], commit_now=True)
    txn.do_request(request)    

    # change all entry_added to Admin
    txn = client.txn()

    query = """{
        q(func: eq(email, "wp3@opted.eu")) { v as uid }
        s(func: has(dgraph.type)) @filter(NOT type(User) AND NOT type(dgraph.graphql)) { u as uid } }"""
    nquad = """
        uid(u) <entry_added> uid(v) .
        """
    mutation = txn.create_mutation(set_nquads=nquad)
    request = txn.create_request(query=query, mutations=[mutation], commit_now=True)
    txn.do_request(request)    


    print(Fore.GREEN + 'DONE!' + Style.RESET_ALL)
    deinit()

if __name__ == '__main__':
    main()