from csvwlib.utils import datatypeutils
from csvwlib.utils.json.JSONLDUtils import JSONLDUtils
from language_tags import tags

from csvwlib.utils.json.CommonProperties import CommonProperties
from csvwlib.utils.rdf.CSVW import core_group_of_tables_properties, inherited_properties, core_table_properties, \
    array_properties, array_property_item_types, fields_properties

metadata_fields = {
    'commentPrefix': ([str], '#', None),
    'default': ([str], '', None),
    'delimiter': ([str], ',', None),
    'dialect': ([dict], None, None),
    'doubleQuote': ([bool], True, None),
    'encoding': ([str], 'utf-8', None),
    'header': ([bool], True, None),
    'headerRowCount': ([int], 1, None),
    'lineTerminators': ([list], ["\r\n", "\n"], str),
    'name': ([str], None, None),
    'null': ([str, list], 'null', str),
    'ordered': ([bool], False, None),
    'separator': ([str], None, None),
    'skipBlankRows': ([bool], False, None),
    'skipColumns': ([int], 0, None),
    'skipInitialSpace': ([bool], False, None),
    'skipRows': ([int], 0, None),
    'suppressOutput': ([bool], False, None),
    'tableSchema': ([dict], {}, None),
    'titles': ([str, list, dict], None, dict),
    'trim': ([bool], True, None),
    'virtual': ([bool], None, None),
    'quoteChar': ([str], "'", None),
}

encodings = ['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424', 'cp437', 'cp500', 'cp720', 'cp737', 'cp775',
             'cp850', 'cp852', 'cp855', 'cp856', 'cp857', 'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864',
             'cp865', 'cp866', 'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026', 'cp1125',
             'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258',
             'cp65001', 'euc-jp', 'euc-jis-2004', 'euc-jisx0213', 'euc-kr', 'gb2312', 'gbk', 'gb18030', 'hz',
             'iso2022-jp', 'iso2022-jp-1', 'iso2022-jp-2', 'iso2022-jp-2004', 'iso2022-jp-3', 'iso2022-jp-ext',
             'iso2022-kr', 'latin-1', 'iso8859-2', 'iso8859-3', 'iso8859-4', 'iso8859-5', 'iso8859-6', 'iso8859-7',
             'iso8859-8', 'iso8859-9', 'iso8859-10', 'iso8859-11', 'iso8859-13', 'iso8859-14', 'iso8859-15',
             'iso8859-16', 'johab', 'koi8-r', 'koi8-t', 'koi8-u', 'kz1048', 'mac-cyrillic', 'mac-greek',
             'mac-iceland', 'mac-latin2', 'mac-roman', 'mac-turkish', 'ptcp154', 'shift-jis', 'shift-jis-2004',
             'shift-jisx0213', 'utf-32', 'utf-32-be', 'utf-32-le', 'utf-16', 'utf-16-be', 'utf-16-le', 'utf-7',
             'utf-8', 'utf-8-sig']

values_map = {
    'textDirection': (['ltr', 'rtl', 'auto', 'inherit'], 'inherit'),
    'datatype': (['anyURI', 'base64Binary', 'boolean', 'date', 'dateTime', 'datetime', 'dateTimeStamp', 'decimal',
                  'integer', 'integer', 'long', 'int', 'short', 'byte', 'nonNegativeInteger', 'positiveInteger',
                  'unsignedLong', 'unsignedInt', 'unsignedShort', 'unsignedByte', 'nonPositiveInteger',
                  'negativeInteger', 'double', 'number', 'duration', 'dayTimeDuration', 'yearMonthDuration', 'float',
                  'gDay', 'gMonth', 'gMonthDay', 'gYear', 'gYearMonth', 'hexBinary', 'QName', 'string',
                  'normalizedString', 'token', 'language', 'Name', 'NMTOKEN', 'time', 'xml', 'html', 'json'], 'string'),
    'encoding': (encodings, 'utf-8'),
    'tableDirection': (['rtl', 'ltr', 'auto'], 'auto')
}

non_regex_types = ['boolean', 'date', 'dateTime', 'datetime', 'dateTimeStamp', 'decimal', 'integer', 'integer', 'long',
                   'int', 'short', 'byte', 'nonNegativeInteger', 'positiveInteger', 'unsignedLong', 'unsignedInt',
                   'unsignedShort', 'unsignedByte', 'double', 'number', 'time',
                   'float', 'gDay', 'gMonth', 'gMonthDay', 'gYear', 'gYearMonth', 'hexBinary']

constraints = {
    'skipRows': ({'min': 0}, 0),
    'name': ({'forbidden_chars': [' '], 'starts_not_with': ['_']}, None),
}


class MetadataValidator:

    instance = None

    def __init__(self, start_url):
        MetadataValidator.instance = self
        self.metadata = {}
        if isinstance(start_url,dict):
            if 'url' in start_url.keys():
                self.start_url = start_url['url']
        else:
            self.start_url = start_url
        self.warnings = []
        self.table = {}

    def validate_metadata(self, metadata):
        if metadata is None or not isinstance(metadata, dict):
            return
        self.metadata = metadata
        if 'tableSchema' in metadata.keys():
            tables = [metadata]
        else:
            tables = metadata['tables']

        for table in tables:
            self.table = table
            if 'tables' in metadata.keys():
                self.check_member_property('tableGroup', metadata)
            else:
                self.check_member_property('table', metadata)
            self.check_csv_reference(table, metadata)
            self.validate(metadata)
            self.check_undefined_properties(metadata)
            self.check_uri_templates()
            self.check_titles(table)

    def check_csv_reference(self, table, metadata):
        if isinstance(self.start_url,dict):
            return
        if not self.start_url.endswith('.csv'):
            return
        if table['url'] != self.start_url:
            for key in list(metadata.keys()):
                del metadata[key]
            self.print_bad_reference_warning()

    def print_bad_reference_warning(self):
        self.print_warning('Found metadata does not implicitly reference CSV file. It will be ignored')

    def validate(self, metadata):
        for key, value in list(metadata.items()):
            self.check_value_type(key, value, metadata)
            value = metadata.get(key)
            if value is None:
                continue
            self.check_language_tag(key, value, metadata)
            self.check_value(key, value, metadata)
            self.check_value_constraints(key, value, metadata)
            self.check_array_properties(key, value, metadata)
            value = metadata.get(key)
            self.check_member_properties(key, value)
            self.check_id(key, value, metadata)
            self.check_primary_key(key, value)
            self.check_datatype(key, value)
            if type(value) is dict:
                self.warnings.extend(self.validate(value))
            if type(value) is list:
                for element in value:
                    if type(element) is dict:
                        self.warnings.extend(self.validate(element))
        return self.warnings

    _uri_template_properties = ['aboutUrl', 'propertyUrl', 'valueUrl']

    def check_uri_templates(self):
        tables_url = self.metadata.get('tables', [{}])[0].get('url')
        self.check_uris(self.metadata, self.metadata.get('url', tables_url))
        if 'tables' in self.metadata:
            for table in self.metadata['tables']:
                self.check_uris(table, table['url'])

    def check_uris(self, table, csv_url):
        for key, value in table.items():
            if key in self._uri_template_properties and type(value) is not str:
                table[key] = csv_url
                self.print_field_type_warning(key, value, csv_url)
        for column in table.get('tableSchema', {}).get('columns', []):
            for key, value in column.items():
                if key in self._uri_template_properties and type(value) is not str:
                    table[key] = csv_url
                    self.print_field_type_warning(key, value, csv_url)

    def check_value_type(self, key, value, metadata):
        if key in metadata_fields:
            expected_types, default_value, list_item_type = metadata_fields[key]
            if type(value) not in expected_types:
                if default_value is not None:
                    metadata[key] = default_value
                else:
                    del metadata[key]
                self.print_field_type_warning(key, value, default_value)
            if type(value) is list:
                for item in value:
                    if type(item) is list_item_type:
                        self.print_bad_array_item_type_warning(key, type(item))

    def print_field_type_warning(self, field, value, default):
        self.print_warning("Warning: Field '{}' cannot have value of type '{}'. Using '{}' as default"
                           .format(field, type(value), default))

    def check_language_tag(self, key, value, metadata):
        if (key == 'lang' or key == '@language') and not tags.check(value):
            del metadata[key]
            self.print_language_tag_warning(value)

    def check_lang_tag(self, tag):
        if not tags.check(tag):
            self.print_language_tag_warning(tag)

    def print_language_tag_warning(self, tag):
        self.print_warning("'{}' is not a valid language tag".format(tag))

    def check_value(self, key, value, metadata):
        if key in values_map:
            possible_values, default = values_map[key]
            if key == 'datatype' and type(value) is dict:
                value = value.get('base', 'string')
            if value not in possible_values:
                metadata[key] = default
                self.print_value_warning(key, value, possible_values)

    def print_value_warning(self, key, value, possible_values):
        self.print_warning("'{}' cannot have value '{}', possible values: {}".format(key, value, possible_values))

    def check_value_constraints(self, key, value, metadata):
        if key in constraints:
            constraint, default = constraints[key]
            if 'min' in constraint:
                if value < constraint['min']:
                    self.handle_field(key, metadata, default)
                    self.print_value_constraint_warning(key, value, default)
            if 'forbidden_chars' in constraint:
                for char in constraint['forbidden_chars']:
                    if char in value:
                        self.print_value_constraint_warning(key, value, default)
                        self.handle_field(key, metadata, default)
            if 'starts_not_with' in constraint:
                for string in constraint['starts_not_with']:
                    if value.startswith(string):
                        self.print_value_constraint_warning(key, value, default)
                        self.handle_field(key, metadata, default)

    @staticmethod
    def handle_field(key, metadata, default):
        if default is None:
            del metadata[key]
        else:
            metadata[key] = default

    def print_value_constraint_warning(self, key, value, default):
        self.print_warning("'{}' cannot have value '{}', Using {} as default".format(key, value, default))

    def check_member_properties(self, prop, value):
        if prop in array_properties and prop != '@context':
            for item in value:
                self.check_member_property(prop, item)
        else:
            self.check_member_property(prop, value)

    def check_member_property(self, prop, object_value):
        if prop in fields_properties:
            possible_keys = fields_properties[prop].keys()
            for _key, _value in list(object_value.items()):
                if _key not in possible_keys and not CommonProperties.is_common_property(_key) \
                        and _key not in inherited_properties:
                    self.print_invalid_member_property(prop, _key)
                    del object_value[_key]

    def print_invalid_member_property(self, parent, prop):
        self.print_warning("Invalid property '{}' in '{}'".format(prop, parent))

    def check_undefined_properties(self, metadata):
        for key, value in list(metadata.items()):
            if key not in core_group_of_tables_properties and key not in core_table_properties \
                    and not CommonProperties.is_common_property(key)\
                    and key not in inherited_properties:
                del metadata[key]
                self.print_undefined_property_warning(key)
        for table in metadata.get('tables', []):
            for key, value in table.items():
                if key not in core_table_properties and key not in inherited_properties \
                        and not CommonProperties.is_common_property(key):
                    del metadata[key]
                    self.print_undefined_property_warning(key)

    def print_undefined_property_warning(self, key):
        self.print_warning("Unknonwn property '{}'. It will be ignored".format(key))

    def check_array_properties(self, key, value, metadata):
        if key in array_properties and key != '@context':
            if type(value) is not list:
                self.print_bad_array_type_warning(key)
                metadata[key] = []
                return
            expected_type = array_property_item_types[key]
            for i in range(len(value)):
                if type(value[i]) != expected_type:
                    self.print_bad_array_item_type_warning(key, type(value[i]))
                    del value[i]

    def print_bad_array_item_type_warning(self, key, bad_type):
        self.print_warning("Bad type of property item '{}' - '{}'".format(key, bad_type))

    def print_bad_array_type_warning(self, key):
        self.print_warning("'{}' has to have array value.".format(key))

    def check_id(self, key, value, metadata):
        if key == '@id' and type(value) is not str:
            metadata[key] = self.start_url
            self.print_field_type_warning(key, value, self.start_url)

    def check_primary_key(self, key, value):
        if key == 'primaryKey':
            for column in self.table['tableSchema']['columns']:
                if 'name' in column and column['name'] == value:
                    return
            self.print_missing_column_name_warning(value)

    def print_missing_column_name_warning(self, column_name):
        self.print_warning("A column with name '{}' has to exist if 'primaryKey' specified .".format(column_name))

    def print_warning(self, warning):
        self.warnings.append(warning)
        print('Warning: {}'.format(warning))

    def check_datatype(self, key, datatype):
        if key != 'datatype':
            return
        base = datatypeutils.get_type_name(datatype)
        if base == 'boolean':
            self.check_boolean_datatype(datatype)

    def check_boolean_datatype(self, datatype):
        if type(datatype) is dict:
            if type(datatype.get('format', '')) is not str or '|' not in datatype.get('format', '|'):
                self.print_bad_datatype_format_warning('boolean', datatype['format'])
                del datatype['format']

    def print_bad_datatype_format_warning(self, datatype_name, format):
        self.print_warning("Datatype '{}' cannot have format '{}'".format(datatype_name, format))

    def check_titles(self, table):
        language = JSONLDUtils.language(table.get('@context'), table)
        for column in table.get('tableSchema', {}).get('columns', []):
            titles = column.get('titles')
            compatible_title_language = False if language is not None else True
            if type(titles) is str:
                compatible_title_language = True
            elif type(titles) is list:
                for title in titles:
                    self.check_title(title)
                    if language is not None:
                        if type(title) is str:
                            compatible_title_language = True
                        if type(title) is dict:
                            (lang, title), = title.items()
                            if lang == language:
                                compatible_title_language = True
            elif type(titles) is dict:
                self.check_title(titles)
                if language is not None:
                    (lang, title), = titles.items()
                    if lang == language:
                        compatible_title_language = True
            if not compatible_title_language:
                self.print_no_matching_title_lang_found_warning(language)

    def print_no_matching_title_lang_found_warning(self, lang):
        self.print_warning("No matching column title found for language '{}'".format(lang))

    def check_title(self, title):
        if type(title) is not dict and type(title) is not str:
            self.print_bad_array_item_type_warning('titles', type(title))
        if type(title) is dict:
            (lang, title), = title.items()
            self.check_lang_tag(lang)
            if type(title) is not str:
                self.print_warning("Bad titles value {}".format(title))

    def print_ignore_property_warning(self, prop):
        self.print_warning("Invalid value '{}'. It will be ignored".format(prop))

    def check_compatibility(self, csvs, metadata):
        for csv, table_metadata in zip(csvs, metadata['tables']):
            if metadata.get('dialect', {}).get('header', True):
                columns = list(map(lambda col_name: col_name, csv[0]))
            else:
                columns = list(map(lambda index: '_col.' + str(index + 1), range(len(csv[0]))))
            if len(columns) != len(table_metadata['tableSchema']['columns']):
                self.print_column_count_mismatch_warning()
                metadata_columns = table_metadata['tableSchema']['columns']
                columns = list(map(lambda index: '_col.' + str(index + 1), range(len(csv[0]))))
                metadata_columns.extend(list(map(lambda col_name: {'name': col_name}, columns[len(metadata_columns):])))
                return
            for embedded_column_name, column_metadata in zip(columns, table_metadata['tableSchema']['columns']):
                titles = column_metadata.get('titles', [])
                titles = titles if type(titles) is list else [titles]
                for title in titles:
                    if type(title) is dict:
                        (lang, title), = title.items()
                    if title == embedded_column_name:
                        break
                    self.print_incompatibility_warning('titles', embedded_column_name)

    def print_incompatibility_warning(self, prop, embedded_column_name):
        self.print_warning("Metadata property '{}' is incompatible with embedded metadata - {}"
                           .format(prop, embedded_column_name))

    def print_column_count_mismatch_warning(self):
        self.print_warning("Column count in metadata does not match embedded metadata")
