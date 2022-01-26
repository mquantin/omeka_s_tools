# AUTOGENERATED! DO NOT EDIT! File to edit: api.ipynb (unless otherwise specified).

__all__ = ['OmekaAPIClient']

# Cell
import requests
import requests_cache
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from pathlib import Path

class OmekaAPIClient(object):

    def __init__(self, api_url, key_identity=None, key_credential=None, use_cache=True):
        self.api_url = api_url
        self.params = {
            'key_identity': key_identity,
            'key_credential': key_credential
        }
        # Set up session and caching
        if use_cache:
            self.s = requests_cache.CachedSession()
            self.s.cache.clear()
        else:
            self.s = requests.Session()
        retries = Retry(total=10, backoff_factor=1, status_forcelist=[ 502, 503, 504, 524 ])
        self.s.mount('http://', HTTPAdapter(max_retries=retries))
        self.s.mount('https://', HTTPAdapter(max_retries=retries))


    def format_resource_id(self, resource_id, resource_type):
        '''
        Generate a formatted id for the resource with the specified Omeka id number and resource type.

        Parameters:
        * `resource_id` - numeric identifier used by Omeka for this resource
        * `resource_type` - one of Omeka's resource types, eg: 'items', 'properties'

        Returns:
        * a dict with values for '@id' and 'o:id'
        '''
        formatted_id = {
            '@id': f'{self.api_url}/{resource_type}/{resource_id}',
            'o:id': resource_id
        }
        return formatted_id

    def get_resources(self, resource_type, **kwargs):
        '''
        Get a list of resources matching the supplied parameters.
        This will return the first page of matching results. To retrieve additional pages,
        you can supply the `page` parameter to move through the full result set.

        Parameters:
        * `resource_type` - one of Omeka's resource types, eg: 'items', 'properties'
        * there are many additional parameters you can supply as kwargs, see the Omeka documention

        Returns a dict with the following values:
        * `total_results` - number of matching resources
        * `results` - a list of dicts, each containing a JSON-LD formatted representation of a resource
        '''
        response = self.s.get(f'{self.api_url}/{resource_type}/', params=kwargs)
        results = response.json()
        return {'total_results': int(response.headers['Omeka-S-Total-Results']), 'results': results}

    def get_resource(self, resource_type, **kwargs):
        '''
        Get the first resource matching the supplied parameters.

        Parameters:
        * `resource_type` - one of Omeka's resource types, eg: 'items', 'properties'
        * there are many additional parameters you can supply as kwargs, see the Omeka documention

        Returns
        * a dict containing a JSON-LD formatted representation of the resource
        '''

        data = self.get_resources(resource_type, **kwargs)
        try:
            resource = data['results'][0]
        except IndexError:
            return
        else:
            return resource

    def get_resource_by_id(self, resource_id, resource_type='items'):
        '''
        Get a resource from its Omeka id.

        Parameters:
        * `resource_id` - numeric identifier used by Omeka for this resource
        * `resource_type` - one of Omeka's resource types, eg: 'items', 'properties'

        Returns
        * a dict containing a JSON-LD formatted representation of the resource
        '''
        response = self.s.get(f'{self.api_url}/{resource_type}/{resource_id}')
        return response.json()

    def get_template_by_label(self, label):
        '''
        Get a resource template from its Omeka label.

        Parameters:
        * `label` - the name of the resource template in Omeka (eg. 'NewspaperArticle')

        Returns:
        * dict containing representation of the template
        '''
        return self.get_resource('resource_templates', label=label)

    def get_resource_by_term(self, term, resource_type='properties'):
        '''
        Get the resource (property or class) associated with the suppied term.

        Parameters:
        * `term` - property label qualified with vocabulary prefix (eg: 'schema:name')

        Returns:
        * dict containing representation of the resource
        '''
        return self.get_resource(resource_type, term=term)

    def get_resource_from_vocab(self, local_name, vocabulary_namespace_uri='http://schema.org/', resource_type='properties'):
        '''
        Get the resource (property or class) associated with the suppied vocabulary and label.

        Parameters:
        * `local_name` - label of the property or class
        * `vocabulary_namespace_uri` - URI defining the vocab

        Returns:
        * dict containing representation of the resource
        '''
        return self.get_resource(resource_type, local_name=local_name, vocabulary_namespace_uri=vocabulary_namespace_uri)

    def get_property_id(self, term):
        '''
        Get the numeric identifier associated with the supplied property term.

        Parameters:
        * `term` - property label qualified with vocabulary prefix (eg: 'schema:name')

        Returns:
        * numeric identifier
        '''
        resource = self.get_resource_by_term(term=term)
        if resource:
            return resource['o:id']

    def filter_items(self, params, **extra_filters):
        for filter_type in ['resource_template_id', 'resource_class_id', 'item_set_id', 'is_public']:
            filter_value = extra_filters.get(filter_type)
            if filter_value:
                params[filter_type] = filter_value
        return params

    def filter_items_by_property(self, filter_property='schema:name', filter_value='', filter_type='eq', page=1, **extra_filters):
        '''
        Filter the list of items by searching for a value in a particular property.
        Additional filters can also limit to items associated with particular templates, classes, or item sets.

        Parameters:
        * `filter_property` - property term (eg: 'schema:name')
        * `filter_value` - the value you want to find
        * `filter_type` - how `filter_value` should be compared to the stored values (eg: 'eq')
        * `page` - number of results page

        Additional parameters:
        * `resource_template_id` - numeric identifier
        * `resource_class_id` - numeric identifier
        * `item_set_id` - numeric identifier
        * `is_public` - boolean, True or False

        Returns a dict with the following values:
        * `total_results` - number of matching resources
        * `results` - a list of dicts, each containing a JSON-LD formatted representation of a resource

        '''
        # We need to get the id of the property we're using
        property_id = self.get_property_id(filter_property)
        params = {
            'property[0][joiner]': 'and', # and / or joins multiple property searches
            'property[0][property]': property_id, # property id
            'property[0][type]': filter_type, # See above for options
            'property[0][text]': filter_value,
            'page': page
        }
        params = self.filter_items(params, **extra_filters)
        # print(params)
        data = self.get_resources('items', **params)
        return data

    def search_items(self, query, search_type='fulltext_search', page=1, **extra_filters):
        '''
        Search for matching items.
        Two search types are available:
        * 'search` - looks for an exact match of the query in a property value
        * 'fulltext_search` - looks for the occurance of the query anywhere

        Parameters:
        * `query` - the text you want to search for
        * `search_type` - one of 'fulltext_search' or 'search'
        * `page` - number of results page

        Additional parameters:
        * `resource_template_id` - numeric identifier
        * `resource_class_id` - numeric identifier
        * `item_set_id` - numeric identifier
        * `is_public` - boolean, True or False

        Returns a dict with the following values:
        * `total_results` - number of matching resources
        * `results` - a list of dicts, each containing a JSON-LD formatted representation of a resource
        '''
        params = {'page': page}
        params[search_type] = query
        params = self.filter_items(params, **extra_filters)
        return self.get_resources('items', **params)

    def get_template_properties(self, template_id):
        '''
        List properties used by the specified template.

        The resource template objects returned by the API don't include property terms.
        This function gets the additional details, and organises the properties in a dictionary,
        organised by term. This makes it easy to check if a particular term is used by a template.

        Parameters:
        * `template_id` - numeric identifier for a template

        Returns:
        * a dict organised by property terms, with values for `property_id` and `type`
        '''
        properties = {}
        template = self.get_resource_by_id(template_id, 'resource_templates')
        for prop in template['o:resource_template_property']:
            prop_url = prop['o:property']['@id']
            # The resource template doesn't include property terms, so we have to go to the property data
            response = self.s.get(prop_url)
            data = response.json()
            # Use default data types if they're not defined in the resource template
            data_type = ['literal', 'uri', 'resource:item'] if prop['o:data_type'] == [] else prop['o:data_type']
            properties[data['o:term']] = {'property_id': data['o:id'], 'type': data_type}
        return properties

    def prepare_property_value(self, value, property_id):
        '''
        Formats a property value according to its datatype as expected by Omeka.
        The formatted value can be used in a payload to create a new item.

        Parameters:
        * `value` - a dict containing a `value` and (optionally) a `type`
        * `property_id` - the numeric identifier of the property

        Note that is no `type` is supplied, 'literal' will be used by default.

        Returns:
        * a dict with values for `property_id`, `type`, and either `@id` or `@value`.
        '''
        if not isinstance(value, dict):
            value = {'value': value}

        try:
            data_type = value['type']
        except KeyError:
            data_type = 'literal'

        property_value = {
            'property_id': property_id,
            'type': data_type
        }

        if data_type == 'resource:item':
            property_value['@id'] = f'{self.api_url}/items/{value["value"]}'
            property_value['value_resource_id'] = value['value']
            property_value['value_resource_name'] = 'items'
        elif data_type == 'uri':
            property_value['@id'] = value['value']
        else:
            property_value['@value'] = value['value']
        return property_value

    def add_item(self, payload, media_files=None, template_id=None, class_id=None, item_set_id=None):
        '''
        Create a new item from the supplied payload, optionally uploading attached media files.

        Parameters:
        * `payload` - a dict generated by `prepare_item_payload()` or `prepare_item_payload_using_template()`
        * `media_files` - a list of paths pointing to media files, or a list of dicts with `path` and `title` values
        * `template_id` - internal Omeka identifier of a resource template you want to attach to this item
        * `class_id` - internal Omeka identifier of a resource class you want to attach to this item
        * `item_set_id` - internal Omeka identifier for an item set you want to add this item to

        Returns:
        * a dict providing the JSON-LD representation of the new item from Omeka
        '''
        if template_id:
            payload['o:resource_template'] = self.format_resource_id(template_id, 'resource_templates')
        if class_id:
            payload['o:resource_class'] = self.format_resource_id(class_id, 'resource_classes')
        if item_set_id:
            payload['o:item_set'] = self.format_resource_id(template_id, 'item_sets')
        if media_files:
            files = self.add_media_to_payload(payload, media_files)
            response = self.s.post(f'{self.api_url}/items', files=files, params=self.params)
        else:
            response = self.s.post(f'{self.api_url}/items', json=payload, params=self.params)
        return response.json()

    def prepare_item_payload(self, terms):
        '''
        Prepare an item payload, ready for upload.

        Parameters:
        * `terms`: a dict of terms, values, and (optionally) data types

        Returns:
        * the payload dict
        '''
        payload = {}
        for term, values in terms.items():
            # Get the property id of the supplied term
            try:
                property_id = self.get_property_id(term)
            except IndexError:
                print(f'Term "{term}" not found')
            else:
                payload[term] = []
                for value in values:
                    # Add a value formatted according to the data type
                    payload[term].append(self.prepare_property_value(value, property_id))
        return payload

    def prepare_item_payload_using_template(self, terms, template_id):
        '''
        Prepare an item payload, checking the supplied terms and values against the specified template.
        Note:
        * terms that are not in the template will generate a warning and be dropped from the payload
        * data types that don't match the template definitions will generate a warning and the term will be dropped from the payload
        * if no data type is supplied, a type that conforms with the template definition will be used

        Parameters:
        * `terms`: a dict of terms, values, and (optionally) data types
        * `template_id`: Omeka's internal numeric identifier for the template

        Returns:
        * the payload dict
        '''
        template_properties = self.get_template_properties(template_id)
        payload = {}
        for term, values in terms.items():
            if term in template_properties:
                property_details = template_properties[term]
                payload[term] = []
                for value in values:
                    if not isinstance(value, dict):
                        value = {'value': value}
                    # The supplied data type doesn't match the template
                    if 'type' in value and value['type'] not in property_details['type']:
                        print(f'Data type "{value["type"]}" for term "{term}" not allowed by template')
                        break
                    elif 'type' not in value:
                        # Use default datatype from template if none is supplied
                        if len(property_details['type']) == 1:
                            value['type'] = property_details['type'][0]
                        # Use literal if allowed by template and data type not supplied
                        elif 'literal' in property_details['type']:
                            value['type'] = 'literal'
                        # Don't know what data type to use
                        else:
                            print(f'Specify data type for term "{term}"')
                            break
                    # Add a value formatted according to the data type
                    payload[term].append(self.prepare_property_value(value, property_details['property_id']))
            # The supplied term is not in the template
            else:
                print(f'Term {term} not in template')
        return payload

    def add_media_to_payload(self, payload, media_files):
        '''
        Add media files to the item payload.

        Parameters:
        * `payload` - the payload dict to be modified
        * `media_files` - media files to be uploaded

        The value of `media_files` can be either:
        * a list of paths to the image/media files (filename is used as title)
        * a list of dicts, each containing `title`, and `path` values

        Returns:
        * the modified payload dict
        '''
        payload['o:media'] = []
        files = {}
        for index, media_file in enumerate(media_files):
            if isinstance(media_file, dict):
                title = media_file['title']
                path = media_file['path']
            else:
                title = media_file[:-4]
                path = media_file
            payload['o:media'].append({'o:ingester': 'upload', 'file_index': str(index), 'o:item': {}, 'dcterms:title': [{'property_id': 1, '@value': title, 'type': 'literal'}]})
            files[f'file[{index}]'] = Path(path).read_bytes()
        files['data'] = (None, json.dumps(payload), 'application/json')
        return files