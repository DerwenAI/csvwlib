import re

from csvwlib.utils import datatypeutils
from csvwlib.utils.datatypeutils import type_constraints
from csvwlib.utils.metadata import MetadataValidator, non_regex_types
from csvwlib.utils.rdf.CSVW import CONST_STANDARD_MODE, CONST_MINIMAL_MODE, number_datatypes
from csvwlib.utils.CSVUtils import CSVUtils
from csvwlib.utils.DOPUtils import DOPUtils
from csvwlib.utils.DialectUtils import DialectUtils
from csvwlib.utils.MetadataLocator import MetadataLocator
from csvwlib.utils.NumericUtils import NumericUtils
from csvwlib.utils.TypeConverter import TypeConverter
from csvwlib.utils.json.CommonProperties import CommonProperties
from csvwlib.utils.json.JSONLDUtils import JSONLDUtils
from csvwlib.utils.url.PropertyUrlUtils import PropertyUrlUtils
from csvwlib.utils.url.UriTemplateUtils import UriTemplateUtils


class ModelConverter:

    def __init__(self, csv_url=None, metadata_url=None):
        super().__init__()
        self.csv_url = csv_url
        self.csvs = None
        self.values_valiator = None
        self.metadata_url = metadata_url
        self.start_url = csv_url if csv_url is not None else (metadata_url if not isinstance(metadata_url,dict) else metadata_url.get('url'))
        self.metadata = None
        self.atdm = {'@type': '@AnnotatedTableGroup'}
        self.mode = CONST_STANDARD_MODE

    def convert_to_atdm(self, mode=CONST_STANDARD_MODE):
        """ atdm - annotated tabular data model """
        metadata_validator = MetadataValidator(self.start_url)
        self.mode = mode
        self.metadata = MetadataLocator.find_and_get(self.csv_url, self.metadata_url)
        if self.metadata_url and (isinstance(self.metadata_url,dict) or not self.metadata_url.startswith('http')):
           self.metadata_url = "http://example.com/metadata" 
        self._normalize_metadata_base_url()
        self._normalize_metadata_csv_url()
        metadata_validator.validate_metadata(self.metadata)
        self._fetch_csvs()
        self._normalize_existing_metadata()
        self.values_valiator = ValuesValidator(self.csvs, self.metadata)
        self.values_valiator.validate()

        self._normalize_csv_values()
        metadata_validator.check_compatibility(self.csvs, self.metadata)

        tables = []
        self._add_table_metadata(self.metadata, self.atdm)
        for index, table_metadata in enumerate(self.metadata['tables']):
            rows = []
            start_position = self._first_row_of_data(table_metadata)
            for number, row_data in enumerate(self.csvs[index][start_position:], start=1):
                source_number = number + start_position
                rows.append(self._parse_row(row_data, number, source_number, table_metadata))
            tables.append({'@type': 'AnnotatedTable', 'columns': table_metadata['tableSchema']['columns'], 'rows': rows,
                           'url': table_metadata['url']})
            self._add_table_metadata(table_metadata, tables[-1])
            tables[-1] = {**table_metadata['tableSchema'], **tables[-1]}

        for table in tables:
            for column in table['columns']:
                column['@type'] = 'Column'

        self.atdm['tables'] = tables
        self._normalize_atdm_values()
        return self.atdm, self.metadata

    @staticmethod
    def _add_table_metadata(table_metadata, table):
        for key, value in table_metadata.items():
            if CommonProperties.is_common_property(key) or key == 'notes' or key == '@id':
                table[key] = value

    def _normalize_metadata_base_url(self):
        if self.metadata is None:
            return
        if isinstance(self.metadata,dict):
            for context_entry in self.metadata.get('@context',[]):
                if type(context_entry) is dict and '@base' in context_entry:
                    original_url = self.metadata["url"]
                    if original_url.startswith('http'):
                        directory, file_name = original_url.rsplit('/', 1)
                        self.metadata['url'] = directory + '/' + context_entry['@base'] + file_name
                    else:
                        self.metadata['url'] = context_entry['@base'] + self.metadata['url']
        else:
            print(f"Error: not dict, {self.metadata}")

    def _normalize_metadata_csv_url(self):
        """ Expands 'url' properties if necessary """
        if self.metadata is None:
            return
        domain = PropertyUrlUtils.domain(self.metadata_url) if self.metadata_url is not None else \
            PropertyUrlUtils.domain(self.csv_url)
        if 'url' in self.metadata:
            if not self.metadata['url'].startswith('http'):
                self.metadata['url'] = domain + self.metadata['url']
        else:
            for table in self.metadata.get('tables', []):
                if 'url' in table:
                    if not table['url'].startswith('http'):
                        table['url'] = domain + table['url']

    def _fetch_csvs(self):
        if self.metadata is None or self.metadata == {}:
            self.csvs = [CSVUtils.parse_csv_from_url_to_list(self.csv_url)]
        else:
            if 'tables' in self.metadata:
                self.csvs = list(map(lambda table:
                                     CSVUtils.parse_csv_from_url_to_list(table['url'], self._delimiter(table)),
                                     self.metadata['tables']))
            else:
                self.csvs = [CSVUtils.parse_csv_from_url_to_list(self.metadata.get('url'), self._delimiter(self.metadata))]

    @staticmethod
    def _delimiter(metadata):
        delimiter = ','
        if 'dialect' in metadata:
            delimiter = metadata['dialect'].get('delimiter', delimiter)
        return metadata.get('delimiter', delimiter)

    def _normalize_existing_metadata(self):
        if self.metadata is None or self.metadata == {}:
            self.metadata = {'@context': 'http://www.w3.org/ns/csvw', 'url': self.csv_url}
            self._create_embedded_metadata()
        if self.mode == CONST_MINIMAL_MODE:
            self._convert_metadata_to_minimal_mode()

        self._normalize_tables()
        self._normalize_dialect()
        self._add_table_schemas_if_necessary()
        self._normalize_inherited_properties()
        self._normalize_schemas()
        self._normalize_columns()

    def _create_embedded_metadata(self):
        table = {'tableSchema': {'columns': []}, 'dialect': DialectUtils.get_default(), 'url': self.csv_url}
        for cell in self.csvs[0][0]:
            table['tableSchema']['columns'].append({'name': cell})
        self.metadata = {'@context': 'http://www.w3.org/ns/csvw', 'tables': [table]}

    def _convert_metadata_to_minimal_mode(self):
        for key in list(self.metadata.keys()):
            if ':' in key:
                del self.metadata[key]

    _omitted_properties = ['@context', 'tables', 'notes']

    def _normalize_tables(self):
        if 'tables' not in self.metadata:
            table = {}
            self.metadata['tables'] = [table]
            for key in list(self.metadata.keys()):
                if key not in self._omitted_properties and not CommonProperties.is_common_property(key):
                    table[key] = self.metadata[key]
                    del self.metadata[key]
            self._add_common_properties_to_table(table)

    def _normalize_dialect(self):
        for table in self.metadata['tables']:
            dialect = DialectUtils.get_default()
            dialect = {**dialect, **self.metadata.get('dialect', {})}
            dialect = {**dialect, **table.get('dialect', {})}
            table['dialect'] = dialect
        self.metadata.pop('dialect', None)

    _inherited_properties = ['aboutUrl', 'datatype', 'default', 'lang', 'null', 'ordered', 'propertyUrl', 'required',
                             'separator', 'textDirection', 'valueUrl']

    _uri_template_properties = ['aboutUrl', 'propertyUrl', 'valueUrl']

    def _normalize_inherited_properties(self):
        for prop in self._inherited_properties:
            self._normalize_inherited_property(prop)

    def _normalize_inherited_property(self, property_name):
        for table in self.metadata['tables']:
            property_value = self.metadata.get(property_name, None)
            property_value = table.get(property_name, property_value)
            property_value = table['tableSchema'].get(property_name, property_value)

            if property_value is not None:
                for column in table['tableSchema']['columns']:
                    if property_name not in column:
                        column[property_name] = property_value
                    if property_name in self._uri_template_properties:
                        column[property_name] = UriTemplateUtils.expand(column[property_name], table['url'])

    def _normalize_schemas(self):
        for table in self.metadata['tables']:
            if 'rowTitles' in table['tableSchema']:
                row_titles = table['tableSchema']['rowTitles']
                if type(row_titles) is str:
                    table['tableSchema']['rowTitles'] = [row_titles]

    def _normalize_columns(self):
        self._normalize_column_names()
        self._normalize_datatypes()

    def _normalize_column_names(self):
        """ Adds 'name' property if not present """
        for table in self.metadata['tables']:
            for i, column in enumerate(table['tableSchema']['columns'], start=1):
                if 'name' not in column:
                    language = JSONLDUtils.language(self.metadata['@context'], table)
                    titles = column.get('titles',[]) 
                    if type(titles) is not list:
                        titles = [titles]
                    if language is None:
                        column['name'] = DOPUtils.natural_language_first_value(titles)
                    else:
                        for title in titles:
                            if type(title) is str:
                                column['name'] = title
                                break
                            if type(title) is dict:
                                (lang, value), = title.items()
                                if lang == language:
                                    column['name'] = value
                                    break
                        if 'name' not in column:
                            column['name'] = '_col.' + str(i)

    def _normalize_datatypes(self):
        for table in self.metadata['tables']:
            for column in table['tableSchema']['columns']:
                if 'datatype' in column:
                    datatype = column['datatype']
                    if type(datatype) is dict and 'base' not in datatype:
                        datatype['base'] = 'string'

    def _add_common_properties_to_table(self, table):
        """ Moves common properties from group of tables to table """
        for key, value in list(self.metadata.items()):
            if CommonProperties.is_common_property(key) or key == 'notes' or key == '@id':
                table[key] = value
                del self.metadata[key]

    def _add_table_schemas_if_necessary(self):
        for index, table in enumerate(self.metadata['tables']):
            if 'tableSchema' not in table:
                table['tableSchema'] = {}
                self._add_columns_schema(table, self.csvs[index])
            elif table['tableSchema'] == {} or len(table['tableSchema']['columns']) == 0:
                self._add_embedded_columns_schema(table, self.csvs[index])

    def _add_columns_schema(self, table, csv):
        if self._has_header_row(table['dialect']):
            columns = list(map(lambda col_name: {'name': col_name}, csv[0]))
        else:
            columns = list(map(lambda index: {'name': '_col.' + str(index + 1)}, range(len(csv[0]))))
        table['tableSchema']['columns'] = columns

    @staticmethod
    def _add_embedded_columns_schema(table, csv):
        columns = list(map(lambda index: {'name': '_col.' + str(index + 1)}, range(len(csv[0]))))
        table['tableSchema']['columns'] = columns

    @staticmethod
    def _has_header_row(dialect):
        return dialect['header']

    @staticmethod
    def _columns(table):
        return list(map(lambda json: json['name'], table['tableSchema']['columns']))

    def _normalize_csv_values(self):
        self._set_default_values()
        self._normalize_numbers_notation()
        self._normalize_exponent_signs()

    def _set_default_values(self):
        for table_metadata, csv in zip(self.metadata['tables'], self.csvs):
            for i, column_metadata in enumerate(table_metadata['tableSchema']['columns']):
                if 'default' in column_metadata:
                    for row in csv:
                        if i < len(row) and row[i] == '':
                            row[i] = column_metadata['default']

    def _normalize_numbers_notation(self):
        """ Deletes group char and replaces decimal char with '.' in decimal cells """
        for table_metadata, csv in zip(self.metadata['tables'], self.csvs):
            for i, column_metadata in enumerate(table_metadata['tableSchema']['columns']):
                if type(column_metadata.get('datatype')) is dict and 'format' in column_metadata['datatype']:
                    cell_format = column_metadata['datatype']['format']
                    if type(cell_format) is dict:
                        group_char = cell_format.get('groupChar')
                        decimal_char = cell_format.get('decimalChar')
                        if group_char is not None:
                            for row in csv:
                                row[i] = row[i].replace(group_char, '')
                        if decimal_char is not None:
                            for row in csv:
                                row[i] = row[i].replace(decimal_char, '.')
                        for row in csv:
                            row[i] = row[i].replace(',', '')

    def _normalize_exponent_signs(self):
        for table_metadata, csv in zip(self.metadata['tables'], self.csvs):
            for i, column_metadata in enumerate(table_metadata['tableSchema']['columns']):
                if 'datatype' in column_metadata:
                    datatype = datatypeutils.get_type_name(column_metadata['datatype'])
                    if datatype == 'decimal':
                        for row in csv:
                            row[i] = row[i][:-1] if row[i][-1] == 'E' else row[i]
                            row[i] = NumericUtils.interpret_special_signs(row[i])

    def _parse_row(self, row, number, source_number, table_metadata):
        json_row = {'@id': table_metadata['url'] + '#row=' + str(source_number),
                    'number': number, 'sourceNumber': source_number,
                    'cells': self._row_data_to_json(row, table_metadata)}
        return json_row

    def _row_data_to_json(self, row, table_metadata):
        cells_map = {}
        null_value = table_metadata.get('null', '')
        for column_metadata, column_data in zip(table_metadata['tableSchema']['columns'], row):
            column_name = column_metadata['name']
            if column_data == null_value:
                continue
            if column_data.startswith('\"'):
                column_data = column_data[1:-1]
            if 'separator' in column_metadata and column_metadata['separator'] is not None:
                column_data = column_data.split(column_metadata['separator'])
                column_data = list(map(lambda item: item.strip(), column_data))
            else:
                column_data = [column_data]

            cells_map[column_name] = column_data
        return cells_map

    @staticmethod
    def _first_row_of_data(metadata):
        rows_to_skip_count = metadata['dialect']['skipRows']
        header_row_count = metadata['dialect']['headerRowCount']
        return rows_to_skip_count + header_row_count

    def _normalize_atdm_values(self):
        for table_metadata, atdm_table in zip(self.metadata['tables'], self.atdm['tables']):
            dialect = table_metadata['dialect']
            columns = table_metadata['tableSchema']['columns']
            null_value = table_metadata.get('null', '')
            for i in range(dialect['skipColumns'], len(columns)):
                if 'datatype' in columns[i]:
                    column_name = columns[i]['name']
                    for row in atdm_table['rows']:
                        converted = []
                        if column_name not in row['cells']:
                            continue
                        for value in row['cells'][column_name]:
                            if value != null_value:
                                if datatypeutils.is_compatible_with_datatype(value, columns[i].get('datatype')):
                                    value = TypeConverter.convert_if_necessary(value, columns[i])
                                else:
                                    self.values_valiator.print_type_value_incompatibility_warning(
                                        value, columns[i].get('datatype'))
                            converted.append(value)
                        row['cells'][column_name] = converted


class ValuesValidator:

    def __init__(self, csvs, metadata):
        self.csvs = csvs
        self.metadata = metadata
        self.warnings = []

    def validate(self):
        for csv, table_metadata in zip(self.csvs, self.metadata['tables']):
            self.validate_table(csv, table_metadata)

    def validate_table(self, csv, metadata):
        self.check_required_columns(csv, metadata)
        self.check_regex_compatibility(csv, metadata)

    def check_required_columns(self, csv, metadata):
        null_value = metadata.get('null', '')
        for i, column_metadata in enumerate(metadata['tableSchema']['columns']):
            if column_metadata.get('required', False) is True:
                for row in csv:
                    if row[i] == null_value:
                        self.print_missing_required_value_warning(i, column_metadata['name'])

    def print_missing_required_value_warning(self, row_index, column_name):
        self.print_warning('Column {} is required. Missing value in row {}'.format(column_name, row_index))

    def print_warning(self, warning):
        print('Warning: {}'.format(warning))
        self.warnings.append(warning)

    def check_regex_compatibility(self, csv, metadata):
        for i, column_metadata in enumerate(metadata['tableSchema']['columns']):
            datatype = column_metadata.get('datatype')
            if type(datatype) is dict:
                base = datatype.get('base', 'string')
                datatype_format = datatype.get('format')
                if base not in non_regex_types and datatype_format is not None:
                    try:
                        re.compile(datatype_format)
                    except re.error:
                        self.print_bad_regex_warning(datatype_format)

    def print_bad_regex_warning(self, regex):
        self.print_warning("'{}' is not a valid regular expression".format(regex))

    def print_type_value_incompatibility_warning(self, value, datatype):
        self.print_warning("'{}' is not a valid '{}' type".format(value, datatype))
