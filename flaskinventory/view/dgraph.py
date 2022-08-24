from flaskinventory import dgraph
from flaskinventory.flaskdgraph import Schema

from typing import Union
from flaskinventory.flaskdgraph.utils import restore_sequence, validate_uid

"""
    Inventory Detail View Functions
"""

def get_entry(unique_name: str = None, uid: str = None, dgraph_type: str = None) -> Union[dict, None]:
    query_var = 'query get_entry($value: string) '
    if unique_name:
        query_func = f'{{ entry(func: eq(unique_name, $value))'
        var = unique_name
    elif uid:
        uid = validate_uid(uid)
        if not uid:
            return None
        query_func = f'{{ entry(func: uid($value))'
        var = uid
    else:
        return None

    if dgraph_type:
        assert isinstance(dgraph_type, str), "Only strings are accepted"
        dgraph_type = Schema.get_type(dgraph_type)
        query_func += f'@filter(type({dgraph_type}))'
    else:
        query_func += f'@filter(has(dgraph.type))'

    query_fields = '''{ uid dgraph.type expand(_all_) (orderasc: unique_name) { uid unique_name name entry_review_status user_displayname authors @facets title channel { name unique_name } }'''

    if dgraph_type == 'Source':
        query_fields += '''published_by: ~publishes @facets @filter(type("Organization")) (orderasc: unique_name) { name unique_name uid entry_review_status } 
                            archives: ~sources_included @facets @filter(type("Archive")) (orderasc: unique_name) { name unique_name uid entry_review_status } 
                            datasets: ~sources_included @facets @filter(type("Dataset")) (orderasc: unique_name) (orderasc: unique_name){ name unique_name uid entry_review_status authors @facets }
                            corpora: ~sources_included @facets @filter(type("Corpus")) (orderasc: unique_name) { name unique_name uid entry_review_status authors @facets }
                            papers: ~sources_included @facets @filter(type("ResearchPaper")) (orderasc: published_date) { uid name title published_date entry_review_status authors @facets } 
                        } }'''

    elif dgraph_type == 'Organization':
        query_fields += 'owned_by: ~owns @filter(type(Organization)) (orderasc: unique_name) { uid name unique_name entry_review_status } } }'

    elif dgraph_type == 'Channel':
        query_fields += 'num_sources: count(~channel) } }'

    elif dgraph_type == 'Archive':
        query_fields += 'num_sources: count(sources_included) } }'

    elif dgraph_type == 'Dataset':
        query_fields += '''
                        num_sources: count(sources_included) } }
                        '''

    elif dgraph_type == 'Corpus':
        query_fields += '''
                        num_sources: count(sources_included) 
                        papers: ~corpus_used @facets @filter(type("ResearchPaper")) (orderasc: name) { uid title published_date name entry_review_status authors @facets } 
                        } }
                        '''

    elif dgraph_type == 'Country':
        query_fields += '''
                        num_sources: count(~country @filter(type("Source")))  
                        num_orgs: count(~country @filter(type("Organization"))) } }
                        '''
    
    elif dgraph_type == 'Multinational':
        query_fields += '''
                        num_sources: count(~country @filter(type("Source"))) } }
                        '''

    elif dgraph_type == 'Subunit':
        query_fields += '''
                        num_sources: count(~geographic_scope_subunit @filter(type("Source"))) } }
                        '''
    
    elif dgraph_type == 'Operation':
        query_fields += '''
                        tools: ~used_for @filter(type("Tool")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date programming_languages platform } } }
                        '''

    elif dgraph_type == 'FileFormat':
        query_fields += '''
                        tools_input: ~input_file_format @filter(type("Tool")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date programming_languages platform } 
                        tools_output: ~output_file_format @filter(type("Tool")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date programming_languages platform }
                        datasets: ~file_format @filter(type("Dataset")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date }
                        } }
                        '''

    elif dgraph_type == 'MetaVar':
        query_fields += '''
                        datasets: ~meta_vars @filter(type("Dataset")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date }
                        corpus: ~meta_vars @filter(type("Corpus"))  (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date }
                        } }
                        '''
    
    elif dgraph_type == 'ConceptVar':
        query_fields += '''
                        datasets: ~concept_vars @filter(type("Dataset")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date }
                        corpus: ~concept_vars @filter(type("Corpus"))  { uid name unique_name entry_review_status authors @facets published_date }
                        tools: ~concept_vars @filter(type("Tool")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date programming_languages platform }
                        } }
                        '''

    elif dgraph_type == 'TextUnit':
        query_fields += '''
                        corpus: ~text_units @filter(type("Corpus")) (orderasc: unique_name) { uid name unique_name entry_review_status authors @facets published_date }
                        } }
                        '''
    else:
        query_fields += '} }'
    
    query_string = query_var + query_func + query_fields

    data = dgraph.query(query_string, variables={'$value': var})

    if len(data['entry']) == 0:
        return None

    data = data['entry'][0]

    restore_sequence(data)

    return data


def get_rejected(uid):
    query_string = f'''{{ q(func: uid({uid})) @filter(type(Rejected)) 
                        {{ uid name unique_name other_names 
                            creation_date entry_added {{ uid user_displayname }} 
                            entry_notes entry_review_status reviewed_by {{ uid user_displayname }}
                        }}
                        }}'''

    res = dgraph.query(query_string)

    if len(res['q']) > 0:
        return res['q'][0]
    else:
        return False


def get_orphan(query):
    q_string = '''{
                source(func: eq(dgraph.type, "Source")) 
                @filter(not(has(~publishes))) {
                    uid
                    name
                    }
                }'''
    pass


""" 
    Query Related Functions 
"""

# List all entries of specified type, allows to pass in filters


def list_by_type(typename, filt=None, fields=None, normalize=False):
    query_head = f'{{ q(func: type("{typename}"), orderasc: name) '
    if filt:
        query_head += dgraph.build_filt_string(filt)

    query_fields = ''
    if fields == 'all':
        query_fields = " expand(_all_) "
    elif fields:
        query_fields = " ".join(fields)
    else:
        normalize = True
        if typename == 'Source':
            query_fields = ''' uid unique_name name founded other_names
                                channel { name }
                                '''
        if typename == 'Organization':
            query_fields = ''' uid unique_name name founded other_names
                                publishes: count(publishes)
                                owns: count(owns)
                                '''
        if typename in ['Archive', 'Dataset', 'Corpus']:
            query_fields = ''' uid unique_name name access other_names
                                sources_included: count(sources_included)
                                ''' 
        if typename == 'ResearchPaper':
            normalize = False   
            query_fields = ''' uid title authors @facets published_date journal
                                sources_included: count(sources_included)
                                '''
        if typename == 'Subunit':
            normalize = False
            query_fields = ''' uid name unique_name other_names '''
        
        if typename == 'Tool':
            normalize = False
            query_fields = ''' uid name authors @facets published_date journal
                                '''

    query_fields += ''' country { name } '''

    if normalize:
        query_head += ''

    query_string = query_head + \
        ' { ' + query_fields + ' ' + ' } }'

    data = dgraph.query(query_string)

    if len(data['q']) == 0:
        return False

    data = data['q']
    if typename in ['ResearchPaper', 'Tool', 'Corpus', 'Dataset']:
        for paper in data:
            restore_sequence(paper)

    return data
