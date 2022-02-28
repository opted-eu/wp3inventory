from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, SubmitField, RadioField
from wtforms.fields.core import SelectMultipleField
from wtforms.fields.simple import TextAreaField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import DataRequired, Optional
from flask_login import current_user
from wtforms.widgets.core import Input
from flaskinventory import dgraph
from flaskinventory.auxiliary import icu_codes_list_tuples
from flaskinventory.misc.forms import publication_kind_choices, topical_focus_choices, ownership_kind_choices
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
                self.data = datetime.datetime.strptime(
                    date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))

# generic fields


na_option = ('NA', "Don't Know / NA")

entry_review_status_choices = [
    ('draft', 'Draft'), ('pending', 'Pending'), ('accepted', 'Accepted')]
entry_review_status = SelectField(
    'Entry Review Status', choices=entry_review_status_choices)


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

channel = TomSelectField('Channel', validators=[
                         DataRequired()], render_kw={'readonly': True})

channel_comments_choices = [('no comments', 'No Comments'),
                            ('user comments with registration',
                             'Registered Users can comment'),
                            ('user comments without registration', 'Anyone can comment'), na_option]

channel_comments = SelectField(
    'Allows user comments', choices=channel_comments_choices)

website_allows_comments_choices = [na_option,
                                   ('yes', 'Yes'),
                                   ('no', 'No')]

website_allows_comments = SelectField(
    'Allows user comments', choices=website_allows_comments_choices)

website_comments_registration_required = SelectField(
    'Registration required to comment', choices=website_allows_comments_choices)


channel_url = StringField('Channel URL')

channel_epaper = RadioField(
    'E-Paper available', choices=[('yes', 'Yes'), ('no', 'No'), na_option])

transcript_kind_choices = [
    ('tv' 'TV'), ('radio', 'Radio'), ('podcast', 'Podcast'), na_option]

transcript_kind = SelectField(
    'Transcript Kind', choices=transcript_kind_choices)

payment_model_choices = [('free', 'Free, all content is free of charge'),
                         ('partly free', 'Some content is free of charge'),
                         ('not free', 'No content is free of charge'),
                         na_option]

payment_model = SelectField('Payment model', choices=payment_model_choices)

publication_kind = SelectMultipleField(
    'Publication Kind', choices=publication_kind_choices)

special_interest = BooleanField('Special Interest Publication')

topical_focus = SelectMultipleField(
    'Topical Focus', choices=topical_focus_choices)

publication_cycle_choices = [('continuous', 'Continuous'),
                             ('daily', 'Daily (7 times a week)'),
                             ('multiple times per week',
                              'Multiple times per week'),
                             ('weekly', 'Weekly'),
                             ('twice a month', 'Twice a month'),
                             ('monthly', 'Monthly'),
                             ('less than monthly', 'Less frequent than monthly'),
                             na_option]

publication_cycle = SelectField(
    'Publication Cycle', choices=publication_cycle_choices)

publication_cycle_weekday_choices = [(1, 'Monday'),
                                     (2, 'Tuesday'),
                                     (3, 'Wednesday'),
                                     (4, 'Thursday'),
                                     (5, 'Friday'),
                                     (6, 'Saturday'),
                                     (7, 'Sunday'),
                                     na_option]

publication_cycle_weekday = TomSelectMutlitpleField(
    'Publication weekdays', choices=publication_cycle_weekday_choices)

geographic_scope_choices = [('multinational', 'Multinational'),
                            ('national', 'National'),
                            ('subnational', 'Subnational'), na_option]

geographic_scope = SelectField('Geographic Scope', validators=[
                               DataRequired()], choices=geographic_scope_choices)

countries = TomSelectMutlitpleField('Countries', choices=[])

geographic_scope_subunit = TomSelectMutlitpleField('Subunit', choices=[])

languages = SelectMultipleField('Languages', choices=icu_codes_list_tuples)

published_by = SelectMultipleField('Published by')

contains_ads_choices = [('yes', 'Yes'),
                        ('no', 'No'),
                        ('non subscribers', 'Only for non-subscribers'),
                        na_option]

contains_ads = SelectField('Contains Ads', choices=contains_ads_choices)

verified_account = BooleanField('Verified Account')

archives = SelectMultipleField('Archives that include this source')
datasets = SelectMultipleField('Datasets that include this source')
papers = SelectMultipleField('Research Papers that include this source')

party_affiliated_choices = [na_option,
                            ('yes', 'Yes'),
                            ('no', 'No')]

party_affiliated = SelectField(
    'Affiliated with a political party', choices=party_affiliated_choices)

# Organization Fields

is_person = BooleanField('Is a person')

ownership_kind = SelectField(
    'Type of Organization', choices=ownership_kind_choices[1:], validators=[DataRequired()])

country = SelectField('Country', choices=[])

address_string = StringField('Address')

address_geo = StringField('Address Geodata', render_kw={'readonly': True})

employees = IntegerField('Number of employees', validators=[Optional()])

publishes = TomSelectMutlitpleField('Publishes', choices=[])

owns = TomSelectMutlitpleField('Owns', choices=[])

# Dataset Fields

access = SelectField('Access to data', choices=[
                     ('restricted', 'Restricted'), ('free', 'Free')])
url = StringField('Link to Dataset')
sources_included = TomSelectMutlitpleField(
    'Sources included in Dataset', choices=[])
fulltext = BooleanField('Dataset contains fulltext')

editfields_base = {
    "uid": uid,
    # "entry_review_status": entry_review_status,
    # "unique_name": unique_name,
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
    "party_affiliated": party_affiliated,
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
    "party_affiliated": party_affiliated,
    "publication_cycle": publication_cycle,
    "publication_cycle_weekday": publication_cycle_weekday,
    "geographic_scope": geographic_scope,
    "country": countries,
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
                     "website_allows_comments": website_allows_comments,
                     "website_comments_registration_required": website_comments_registration_required,
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

# Multinational
editmultinationalfields = {"uid": uid,
                           "entry_review_status": entry_review_status,
                           "unique_name": unique_name,
                           "name": name,
                           "other_names": other_names,
                           "entry_notes": entry_notes,
                           "description": description}

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


accept = SubmitField('Edit and Accept')


class DynamicForm(FlaskForm):
    submit = SubmitField('Commit Changes')

    # helper method for Jinja2
    def get_field(self, field):
        return getattr(self, field)


def make_form(entity, review_status='accepted'):
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
    elif entity == 'vkontakte':
        fields = editinstagramfields
    elif entity == 'telegram':
        fields = editinstagramfields
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
    elif entity == 'multinational':
        fields = editmultinationalfields
    else:
        raise TypeError

    if current_user.user_role > 1:
        unique_name = StringField('Unique Name',
                                  validators=[DataRequired()])
        fields = {"unique_name": unique_name, **fields}
        if review_status == 'accepted':
            fields["entry_review_status"] = entry_review_status
    else:
        unique_name = StringField('Unique Name',
                                  validators=[DataRequired()], render_kw={'readonly': True})
        fields = {"unique_name": unique_name, **fields}

    class F(DynamicForm):
        pass

    for key, val in fields.items():
        setattr(F, key, val)

    if current_user.user_role > 1 and review_status == 'pending':
        setattr(F, "accept", accept)

    return F(), fields


class RefreshWikidataForm(FlaskForm):

    uid = uid
    submit = SubmitField('Refresh WikiData')
