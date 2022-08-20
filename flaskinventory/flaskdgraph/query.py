from .schema import Schema


# Default Behaviour:
# different predicates are combined with AND operators
# e.g., publication_kind == "newspaper" AND geographic_scope == "national"
# same Scalar predicates are combined with OR operators
# e.g., payment_model == "free" OR payment_model == "partly free"
# same List predicates are combined with AND operators
# e.g., languages == "en" AND languages == "de"
# default comparator is eq or uid_in
# checking for equality


def build_query_string(query: dict, public=True) -> str:

    from flaskinventory.flaskdgraph.dgraph_types import MutualRelationship, SingleRelationship
    filters = []
    try:
        dgraph_type = query.pop('dgraph.type')
        if isinstance(dgraph_type, str):
            dgraph_type = [dgraph_type]
        type_filter = " OR ".join([f'type("{dt}")' for dt in dgraph_type])
        filters.append(f'({type_filter})')
    except KeyError:
        dgraph_type = None

    # first we clean the query dict
    # make sure that the predicates exists (cannot query arbitrary predicates)
    # also would be a hook to declare certain predicates as private (e.g., email addresses)
    cleaned_query = {k: v for k, v in query.items() if k in Schema.predicates().keys()}
    operators = {k.split('+')[0]: v[0] for k, v in query.items() if '+operator' in k}
    facets = {k.split('|')[0]: {k.split('|')[1]: v[0]} for k, v in query.items() if '|' in k and not '+' in k}

    for k in facets.keys():
        if k not in cleaned_query.keys() and k in Schema.predicates().keys():
            cleaned_query.update({k: None})

    query_parts = ['uid', 'unique_name', 'name', 'dgraph.type']
    if public:
        filters.append('eq(entry_review_status, "accepted")')

    for key, val in cleaned_query.items():
        # get predicate from Schema
        predicate = Schema.predicates()[key]

        # check if we have a non-default operator
        operator = operators.get(key, None)

        # Let the predicate object generate the filter query part
        filters.append(predicate.query_filter(val, custom_operator=operator))

        facet_filter = []
        facet_list = []
        # check if we have facet filters
        # predicate|facet+operator
        # audience_size|subscribers+gt
        if key in facets.keys():
            for facet, subvalue in facets[key].items():
                facet_operator = operators.get(f'{key}|{facet}', 'eq')
                facet_filter.append(f'{facet_operator}({facet}, {subvalue})')
                facet_list.append(facet)

        if len(facet_filter) > 0:
            facet_filter = f'@facets({" AND ".join(facet_filter)})'
            facet_list = f'@facets({", ".join(facet_list)})'
        else: 
            facet_filter = ''
            facet_list = ''

        if isinstance(predicate, (SingleRelationship, MutualRelationship)):
            query_parts.append(f'{predicate.query} {facet_filter} {facet_list}  {{ uid name unique_name }}')
        else:
            query_parts.append(f'{predicate.query} {facet_filter} {facet_list}')

        
    filters = " AND ".join(filters)
    
    # make sure predicates are always queried
    if "country" not in cleaned_query.keys():
        query_parts.append('country { uid name unique_name }')
    if "channel" not in cleaned_query.keys():
        query_parts.append('channel { uid name unique_name }')

    query_parts = list(set(query_parts))
    if len(facets.keys()) > 0:
        cascade = "@cascade"
    else:
        cascade = ""

    query_string = f"""{{
        q(func: has(dgraph.type)) @filter({filters}) {cascade} {{
            {" ".join(query_parts)}
            }}
        }}
    """

    return query_string
