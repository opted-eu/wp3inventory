import pydgraph

client_stub = pydgraph.DgraphClientStub('localhost:9080')
client = pydgraph.DgraphClient(client_stub)

client.txn(read_only=True).query('schema { }')