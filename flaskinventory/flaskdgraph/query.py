from .schema import Schema

from wtforms import SubmitField
from flask_wtf import FlaskForm
from .customformfields import TomSelectMutlitpleField


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

    # get parameter: maximum results per page
    try:
        max_results = query.pop('_max_results')
        max_results = int(max_results[0]) if isinstance(
            max_results, list) else int(max_results)
        if max_results > 50 or max_results < 0:
            max_results = 50
    except (KeyError, ValueError):
        max_results = 25

    # get parameter: current page
    try:
        page = query.pop('_page')
        page = int(page[0]) if isinstance(page, list) else int(page)
        page = page - 1 if page > 0 else 0
    except (KeyError, ValueError):
        page = 0

    # special treatment for dgraph.type
    filters = []
    try:
        dgraph_type = query.pop('dgraph.type')
        if isinstance(dgraph_type, str):
            dgraph_type = [dgraph_type]
        type_filter = " OR ".join(
            [f'type("{Schema.get_type(dt)}")' for dt in dgraph_type if Schema.get_type(dt)])
        filters.append(f'({type_filter})')
    except KeyError:
        dgraph_type = None

    # first we clean the query dict
    # make sure that the predicates exists (cannot query arbitrary predicates) and is queryable
    # also asserts that certain predicates remain private (e.g., email addresses)
    cleaned_query = {k: v for k, v in query.items(
    ) if k in Schema.get_queryable_predicates()}
    operators = {k.split('*')[0]: v[0]
                 for k, v in query.items() if '*operator' in k}
    facets = {k.split('|')[0]: {k.split('|')[1]: v[0]}
              for k, v in query.items() if '|' in k and not '*' in k}

    for k in facets.keys():
        if k not in cleaned_query.keys() and k in Schema.get_queryable_predicates():
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
        # "predicate|facet*operator": "name of operator"
        # "audience_size|subscribers*operator": "gt"
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
            query_parts.append(
                f'{predicate.query} {facet_filter} {facet_list}  {{ uid name unique_name }}')
        else:
            query_parts.append(
                f'{predicate.query} {facet_filter} {facet_list}')

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
        q(func: has(dgraph.type), orderasc: unique_name, first: {max_results}, offset: {page * max_results}) 
            @filter({filters}) {cascade} {{
                {" ".join(query_parts)}
            }}
        }}
    """

    return query_string


def generate_query_forms(dgraph_types: list = None):

    if not dgraph_types:
        dgraph_types = Schema.get_types()

    class F(FlaskForm):

        submit = SubmitField('Query')

        def get_field(self, field):
            return getattr(self, field, None)

    setattr(F, 'dgraph.type', TomSelectMutlitpleField(
        'Entity Type', choices=dgraph_types))

    for dt in dgraph_types:
        fields = Schema.get_queryable_predicates(dt)
        for k, v in fields.items():
            if not hasattr(F, k):
                setattr(F, k, v.query_field)

    form = F()

    # add a hook for JavaScript to hide / show fields according to selected entities
    # feels a bit Hacky...
    # the predicates themselves should know, which entity types they belong to
    # for field in form._fields:
    #     try:
    #         associated = Schema.__predicates_types__[field]
    #         getattr(form, field).render_kw.update(
    #             {'data-entities': ",".join(associated)})
    #     except KeyError:
    #         pass

    # ability to pre-populate the form with data
    # if populate_obj:
    #     form = cls.populate_form(form, populate_obj, fields)

    return form
