import pydgraph
import json
import sys
from colorama import init, deinit, Fore, Style

def main():
    init()
    print(Fore.RED + 'WARNING!' + Style.RESET_ALL + " You are about to irreversibly change all entries.")
    user_warning = input('Are you sure you want to proceed? (y/n): ')
    
    if user_warning.lower() != 'y':
        print('Aborted')
        sys.exit()


    client_stub = pydgraph.DgraphClientStub('localhost:9080')
    client = pydgraph.DgraphClient(client_stub)

    print(Fore.YELLOW + 'Running: Websites: Daily Visitors ' + Style.RESET_ALL)

    query_string = """
    query {
        c(func: eq(unique_name, "website")) {
            u as uid
        }
        q(func: type("Source")) 
            @filter(has(audience_size) AND uid_in(channel, uid(u))) @cascade {
                uid
                audience_size @facets(gt(daily_visitors, 0)) @facets
        }
    }
    """

    res = client.txn().query(query_string)

    result = json.loads(res.json)

    for e in result['q']:
        e['audience_size|count'] = e['audience_size|daily_visitors']
        e['audience_size|unit'] = {'0': 'daily visitors'}
        if 'audience_size|datafrom' in e.keys():
            e['audience_size|data_from'] = e.pop('audience_size|datafrom')

    for e in result['q']:
        e.pop('audience_size|daily_visitors')

    txn = client.txn()

    try:
        txn.mutate(set_obj=result['q'])
        txn.commit()
    finally:
        txn.discard()

    print(Fore.YELLOW + 'Running: Twitter / Instagram / Telegram / VK: Followers' + Style.RESET_ALL)

    query_string = """
    query {
        c(func: type(Channel)) @filter(eq(unique_name, ["twitter", "telegram", "instagram", "vkontakte"])) {
            u as uid
        }
        q(func: type("Source")) 
            @filter(has(audience_size) AND uid_in(channel, uid(u))) @cascade {
                uid
                audience_size @facets(gt(followers, 0)) @facets
        }
    }
    """

    res = client.txn().query(query_string)

    result = json.loads(res.json)

    for e in result['q']:
        e['audience_size|count'] = e['audience_size|followers']
        e['audience_size|unit'] = {'0': 'followers'}
        if 'audience_size|datafrom' in e.keys():
            e['audience_size|data_from'] = e.pop('audience_size|datafrom')

    for e in result['q']:
        e.pop('audience_size|followers')

    txn = client.txn()

    try:
        txn.mutate(set_obj=result['q'])
        txn.commit()
    finally:
        txn.discard()



    print(Fore.YELLOW + 'Running: Print: subscribers, copies sold' + Style.RESET_ALL)

    query_string = """
    query {
        c(func: type(Channel)) @filter(eq(unique_name, "print")) {
            u as uid
        }
        q(func: type("Source")) 
            @filter(has(audience_size) AND uid_in(channel, uid(u))) @cascade {
                uid
                audience_size @facets(gt(subscribers, 0)) @facets
        }
    }
    """

    res = client.txn().query(query_string)

    result = json.loads(res.json)

    for e in result['q']:
        e['audience_size|count'] = e['audience_size|subscribers']
        e['audience_size|unit'] = {'0': 'subscribers'}
        if 'audience_size|datafrom' in e.keys():
            e['audience_size|data_from'] = e.pop('audience_size|datafrom')


    for e in result['q']:
        e.pop('audience_size|subscribers')

    txn = client.txn()

    try:
        txn.mutate(set_obj=result['q'])
        txn.commit()
    finally:
        txn.discard()



    query_string = """
    query {
        c(func: type(Channel)) @filter(eq(unique_name, "print")) {
            u as uid
        }
        q(func: type("Source")) 
            @filter(has(audience_size) AND uid_in(channel, uid(u))) @cascade {
                uid
                audience_size @facets(gt(copies_sold, 0)) @facets
        }
    }
    """

    res = client.txn().query(query_string)

    result = json.loads(res.json)

    for e in result['q']:
        e['audience_size|count'] = e['audience_size|copies_sold']
        e['audience_size|unit'] = {'0': 'copies sold'}
        if 'audience_size|datafrom' in e.keys():
            e['audience_size|data_from'] = e.pop('audience_size|datafrom')

    for e in result['q']:
        e.pop('audience_size|copies_sold')

    txn = client.txn()

    try:
        txn.mutate(set_obj=result['q'])
        txn.commit()
    finally:
        txn.discard()

    # papers sold

    query_string = """
    query {
        c(func: type(Channel)) @filter(eq(unique_name, "print")) {
            u as uid
        }
        q(func: type("Source")) 
            @filter(has(audience_size) AND uid_in(channel, uid(u))) @cascade {
                uid
                audience_size @facets(gt(papers_sold, 0)) @facets
        }
    }
    """

    res = client.txn().query(query_string)

    result = json.loads(res.json)

    for e in result['q']:
        e['audience_size|count'] = e['audience_size|papers_sold']
        e['audience_size|unit'] = {'0': 'copies sold'}
        if 'audience_size|datafrom' in e.keys():
            e['audience_size|data_from'] = e.pop('audience_size|datafrom')

    for e in result['q']:
        e.pop('audience_size|papers_sold')

    txn = client.txn()

    try:
        txn.mutate(set_obj=result['q'])
        txn.commit()
    finally:
        txn.discard()

    print(Fore.GREEN + 'DONE!' + Style.RESET_ALL)
    deinit()

if __name__ == '__main__':
    main()