from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, SubmitField
from wtforms.fields.core import IntegerField, SelectMultipleField
from wtforms.fields.simple import TextAreaField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import DataRequired
from flask_login import current_user
from wtforms.widgets.core import Input
from flaskinventory import dgraph
from flaskinventory.auxiliary import icu_codes_list_tuples
import datetime

class TomSelectMutlitpleField(SelectMultipleField):

    def pre_validate(self, form):
        pass


class TomSelectField(SelectField):

    def pre_validate(self, form):
        pass

# taken from: https://stackoverflow.com/questions/27766417/
class NullableDateField(DateField):
    """Native WTForms DateField throws error for empty dates.
    Let's fix this so that we could have DateField nullable."""
    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist).strip()
            if date_str == '':
                self.data = None
                return
            try:
                self.data = datetime.datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))

# generic fields

na_option = ('none', "Don't Know / NA")

entry_review_status_choices = [('draft', 'Draft'), ('pending', 'Pending'), ('accepted', 'Accepted')]
entry_review_status = SelectField('Entry Review Status', choices=entry_review_status_choices)


uid = StringField('uid', render_kw={'readonly': True})

unique_name = StringField('Unique Name',
                          validators=[DataRequired()])

name = StringField('Name', validators=[DataRequired()])

entry_notes = TextAreaField('Entry Notes and comments')

other_names = StringField('Other Names')

wikidataID = StringField('Wikidata ID')

founded = NullableDateField('Founded', render_kw={'type': 'date'})

description = TextAreaField('Description')

# Source Fields

related = TomSelectMutlitpleField('Related Sources', choices=[])

channel = TomSelectField('Channel', validators=[DataRequired()], render_kw={'readonly': True})

channel_comments_choices = [('no comments', 'No Comments'), 
                            ('user comments with registration', 'Registered Users can comment'),
                            ('user comments without registration', 'Anyone can comment'), na_option]
channel_comments = SelectField('Allows user comments', choices=channel_comments_choices)

channel_url = StringField('Channel URL')

channel_epaper = StringField('Link to E-Paper')

transcript_kind_choices = [('tv' 'TV'), ('radio', 'Radio'), ('podcast', 'Podcast'), na_option]

transcript_kind = SelectField('Transcript Kind', choices=transcript_kind_choices)

payment_model_choices = [('free', 'Free'),
                         ('soft paywall', 'Soft Paywall'),
                         ('subscription', 'Subscription'),
                         ('none', "Don't know / NA")]

payment_model = SelectField('Payment model', choices=payment_model_choices)

publication_kind_choices = [('newspaper', 'Newspaper'), ('news agency', 'News Agency'), ('magazine', 'Magazine'), ('tv show', 'TV Show'), (
    'radio show', 'Radio Show'), ('podcast', 'Podcast'), ('news blog', 'News Blog'), ('alternative media', 'Alternative Media'), ('none', "Don't Know / NA")]

publication_kind = SelectMultipleField(
    'Publication Kind', choices=publication_kind_choices)

special_interest = BooleanField('Special Interest Publication')

topical_focus_choices = [("politics", "Politics"),
                         ("society", "Society & Panorama"),
                         ("economy", "Economy, Finance & Stocks"),
                         ("religion", "Religion"),
                         ("science", "Science & Technology"),
                         ("media", "Media"),
                         ("environment", "Environment"),
                         ("education", "Education")]

topical_focus = SelectMultipleField(
    'Topical Focus', choices=topical_focus_choices)

publication_cycle_choices = [('continuous', 'Continuous'),
                             ('daily', 'Daily (7 times a week)'),
                             ('multiple times per week',
                              'Multiple times per week'),
                             ('weekly', 'Weekly'),
                             ('twice a month', 'Twice a month'),
                             ('monthly', 'Monthly'),
                             ('none', "Don't know / NA")]

publication_cycle = SelectField(
    'Publication Cycle', choices=publication_cycle_choices)

publication_cycle_weekday_choices = [(1, 'Monday'),
                                     (2, 'Tuesday'),
                                     (3, 'Wednesday'),
                                     (4, 'Thursday'),
                                     (5, 'Friday'),
                                     (6, 'Saturday'),
                                     (7, 'Sunday'),
                                     ('none', "Don't know / NA")]

publication_cycle_weekday = SelectMultipleField(
    'Publication weekdays', choices=publication_cycle_weekday_choices)

geographic_scope_choices = [('multinational', 'Multinational'),
                            ('national', 'National'),
                            ('subnational', 'Subnational'), ('none', "Don't know / NA")]

geographic_scope = SelectField('Geographic Scope', validators=[
                               DataRequired()], choices=geographic_scope_choices)


geographic_scope_countries = TomSelectMutlitpleField('Country')
geographic_scope_subunit = TomSelectMutlitpleField('Subunit', choices=[])

languages = SelectMultipleField('Languages', choices=icu_codes_list_tuples)

audience_size_value = IntegerField('Audience Size')
audience_size_unit = StringField(
    'Audience Size Unit', description="e.g. subscribers, followers, papers sold", default='Subscribers')

audience_size = DateField('Audience Size (Date of Measurement)', render_kw={'type': 'date'})

published_by = SelectMultipleField('Published by')

contains_ads_choices = [('yes', 'Yes'),
                        ('no', 'No'),
                        ('non subscribers', 'Only for non-subscribers'),
                        ('none', "Don't know / NA")]

contains_ads = SelectField('Contains Ads', choices=contains_ads_choices)

verified_account = BooleanField('Verified Account')

archives = SelectMultipleField('Archives that include this source')
datasets = SelectMultipleField('Datasets that include this source')
papers = SelectMultipleField('Research Papers that include this source')

# Organization Fields

is_person = BooleanField('Is a person')

ownership_kind_choices = [('public ownership', 'Mainly public ownership'),
                          ('private ownership', 'Mainly private Ownership'),
                          ('unknown', 'Unknown Ownership'),
                          ('none', 'Missing!')]

ownership_kind = SelectField(
    'Type of Organization', choices=ownership_kind_choices, validators=[DataRequired()])

country = SelectField('Country', choices=[])

address_string = StringField('Address')

address_geo = StringField('Address Geodata', render_kw={'readonly': True})

employees = StringField('Number of employees')

publishes = TomSelectMutlitpleField('Publishes', choices=[])

owns = TomSelectMutlitpleField('Owns', choices=[])

# Dataset Fields

access = SelectField('Access to data', choices=[('restricted', 'Restricted'), ('free', 'Free')])
url = StringField('Link to Dataset')
sources_included = TomSelectMutlitpleField('Sources included in Dataset', choices=[])
fulltext = BooleanField('Dataset contains fulltext')

editfields_base = {
    "uid": uid,
    "entry_review_status": entry_review_status,
    "unique_name": unique_name,
    "name": name,
    "other_names": other_names,
    "entry_notes": entry_notes,
    "wikidataID": wikidataID
}

editorganizationfields = {
    **editfields_base,
    "is_person": is_person,
    "founded": founded,
    "ownership_kind": ownership_kind,
    "country": country,
    "address_string": address_string,
    "address_geo": address_geo,
    "employees": employees,
    "owns": owns,
    "publishes": publishes
}

editsourcefields = {
    **editfields_base,
    "channel": channel,
    "related": related,
    "contains_ads": contains_ads,
    "publication_kind": publication_kind,
    "special_interest": special_interest,
    "topical_focus": topical_focus,
    "publication_cycle": publication_cycle,
    "publication_cycle_weekday": publication_cycle_weekday,
    "geographic_scope": geographic_scope,
    "geographic_scope_countries": geographic_scope_countries,
    "geographic_scope_subunit": geographic_scope_subunit,
    "languages": languages}


editprintfields = {**editsourcefields, 
                    "channel_epaper": channel_epaper,
                    "payment_model": payment_model,
                    "founded": founded}

edittwitterfields = {**editsourcefields,
                        "channel_url": channel_url}

editinstagramfields = {**editsourcefields,
                        "channel_url": channel_url,
                        "founded": founded}

editwebsitefields = {**editsourcefields,
                        "channel_url": channel_url,
                        "channel_comments": channel_comments,
                        "founded": founded,
                        "payment_model": payment_model}

editfacebookfields = {**editsourcefields, 
                        "channel_url": channel_url,
                        "founded": founded}


edittranscriptfields = {**editsourcefields, 
                        "channel_url": channel_url,
                        "transcript_kind": transcript_kind,
                        "founded": founded}

# Subunits

editsubunitfields = {**editfields_base,
                        "country": country}

# dataset

editdatasetfields = {**editfields_base,
                        "description": description,
                        "access": access,
                        "fulltext": fulltext,
                        "url": url,
                        "sources_included": sources_included}
                        
# archive

editarchivefields = {**editfields_base,
                        "description": description,
                        "access": access,
                        "url": url,
                        "sources_included": sources_included}

class DynamicForm(FlaskForm):
    submit = SubmitField('Commit Changes')

    # helper method for Jinja2
    def get_field(self, field):
        return getattr(self, field)

def make_form(entity, audience_size=1):
    if entity == 'organization':
        fields = editorganizationfields
    elif entity == 'print':
        fields = editprintfields
    elif entity == 'instagram':
        fields = editinstagramfields
    elif entity == 'twitter':
        fields = edittwitterfields
    elif entity == 'facebook':
        fields = editfacebookfields
    elif entity == 'website':
        fields = editwebsitefields
    elif entity == 'transcript':
        fields = edittranscriptfields
    elif entity == 'subunit':
        fields = editsubunitfields
    elif entity == 'dataset':
        fields = editdatasetfields
    elif entity == 'archive':
        fields = editarchivefields
    else:
        raise TypeError
    
    class F(DynamicForm):
        pass

    for key, val in list(fields.items()):
        # if key == 'audience_size':
        #     fields.pop(key)
        #     for i in range(audience_size):
        #         setattr(F, f'audience_size_{i}', val)
        #         setattr(F, f'audience_size_value_{i}', audience_size_value)
        #         setattr(F, f'audience_size_unit_{i}', audience_size_unit)
        #         fields[f'audience_size_{i}'] = val
        #         fields[f'audience_size_value_{i}'] = audience_size_value
        #         fields[f'audience_size_unit_{i}'] = audience_size_unit
        setattr(F, key, val)

    return F(), fields

