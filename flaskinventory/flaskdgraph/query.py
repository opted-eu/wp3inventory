from .schema import Schema

from wtforms import SubmitField, SelectField, StringField
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
    """
        Construct a query string from a dictionary of filters.
        Returns a dql query string with two queries: `total` and `q`
    """

    from flaskinventory.flaskdgraph.dgraph_types import Facet, MutualRelationship, SingleRelationship

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

    # special treatment for free text search
    # maybe incorporate searchable predicates in Schema someday...
    filters = []
    try:
        search_terms = query.pop('_terms')
        if isinstance(search_terms, list):
            search_terms = " ".join(search_terms)
        filters.append("""(anyofterms(name, $searchTerms) OR 
                            anyofterms(other_names, $searchTerms) OR 
                            anyofterms(title, $searchTerms) OR 
                            eq(doi, $searchTerms) OR 
                            eq(arxiv, $searchTerms) OR 
                            anyofterms(authors, $searchTerms))""")

        variables = {'$searchTerms': search_terms}

    except (KeyError, ValueError):
        search_terms = None
        variables = None

    # special treatment for dgraph.type
    
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
    _cleaned_query = {k: v for k, v in query.items(
    ) if k in Schema.get_queryable_predicates()}
    cleaned_query = {Schema.get_queryable_predicates()[k]: v for k, v in _cleaned_query.items() if not isinstance(Schema.get_queryable_predicates()[k], Facet)}

    # preprare facets
    facets = {Schema.get_queryable_predicates()[k]: v for k, v in _cleaned_query.items() if isinstance(Schema.get_queryable_predicates()[k], Facet)}
    for facet in facets:
        if facet.predicate not in _cleaned_query:
            cleaned_query.update({Schema.predicates()[facet.predicate]: None})

    operators = {k.split('*')[0]: v[0]
                 for k, v in query.items() if '*operator' in k}

    # prevent querying everything
    if len(cleaned_query) == 0 and len(filters) == 0:
        return False

    query_parts = ['uid', 'unique_name', 'name', 'dgraph.type', 'authors', 'other_names', 'published_date']
    query_parts_total = ['count(uid)']
    if public:
        filters.append('eq(entry_review_status, "accepted")')

    for predicate, val in cleaned_query.items():
        # get predicate from Schema

        # check if we have a non-default operator
        operator = operators.get(predicate.predicate, None)

        # Let the predicate object generate the filter query part
        predicate_filter = predicate.query_filter(val, custom_operator=operator)

        # check if there are aliases for this predicate
        if predicate.predicate_alias:
            alias_filters = [predicate_filter]
            for alias in predicate.predicate_alias:
                alias_filters.append(predicate.query_filter(val, predicate=alias, custom_operator=operator))
            predicate_filter = " OR ".join(alias_filters)
            predicate_filter = f'({predicate_filter})'

        filters.append(predicate_filter)

        facet_filter = []
        facet_list = []
        # check if we have facet filters
        # "predicate|facet*operator": "name of operator"
        # "audience_size|subscribers*operator": "gt"
        for facet, facet_value in facets.items():
            if facet.predicate == predicate.predicate:
                facet_operator = operators.get(f'{facet}', 'eq')
                filt = facet.query_filter(facet_value, operator=facet_operator)
                if filt:
                    facet_filter.append(filt)
                    facet_list.append(facet.key)

        if len(facet_filter) > 0:
            facet_filter = f'@facets({" AND ".join(facet_filter)})'
            facet_list = f'@facets({", ".join(facet_list)})'
            query_parts_total.append(f'{predicate.query} {facet_filter}')
        else:
            facet_filter = ''
            facet_list = ''

        if isinstance(predicate, (SingleRelationship, MutualRelationship)):
            query_parts.append(
                f'{predicate.query} {facet_filter} {facet_list}  {{ uid name unique_name }}'.strip())
        else:
            query_parts.append(
                f'{predicate.query} {facet_filter} {facet_list}'.strip())

    filters = " AND ".join(filters)

    # make sure predicates are always queried
    if "country" not in _cleaned_query.keys():
        query_parts.append('country { uid name unique_name }')
    if "channel" not in _cleaned_query.keys():
        query_parts.append('channel { uid name unique_name }')

    query_parts = list(set(query_parts))
    if len(facets.keys()) > 0:
        cascade = list(set([facet.predicate for facet in facets]))
        cascade = f"@cascade({', '.join(cascade)})"
    else:
        cascade = ""

    if variables:
        variables_declaration = ", ".join([f'{k}: string' for k in variables])
        variables_declaration = f'query search({variables_declaration})'
    else:
        variables_declaration = ''

    query_string = f"""
        {variables_declaration}
        {{
        total(func: has(dgraph.type)) 
            @filter({filters}) {cascade} {{
                {" ".join(query_parts_total)}
            }}

        q(func: has(dgraph.type), orderasc: name, first: {max_results}, offset: {page * max_results}) 
            @filter({filters}) {cascade} {{
                {" ".join(query_parts)}
            }}
        }}
    """

    return query_string


def generate_query_forms(dgraph_types: list = None, populate_obj: dict = None) -> FlaskForm:

    if populate_obj is None:
        populate_obj = {}

    # if no type is specified, just create a form for all types
    if not dgraph_types:
        dgraph_types = Schema.get_types()

    class F(FlaskForm):

        submit = SubmitField('Query')
        max_results = SelectField('max results', choices=[10, 25, 50], default=25, name='_max_results', coerce=int)
        terms = StringField('Free text search', name='_terms')

        def get_field(self, field):
            return getattr(self, field, None)

    setattr(F, 'dgraph.type', TomSelectMutlitpleField(
        'Entity Type', choices=dgraph_types))

    for dt in dgraph_types:
        fields = Schema.get_queryable_predicates(dt)
        for k, v in fields.items():
            if not hasattr(F, k):
                setattr(F, k, v.query_field)
                if isinstance(v.operators, list):
                    operator_selection = SelectField('operator', name=f'{v}*operator', choices=v.operators)
                    setattr(F, f'{k}*operator', operator_selection)



    form = F(formdata=populate_obj)

    return form
