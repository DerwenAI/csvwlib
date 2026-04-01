from urllib.parse import quote

from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.namespace import XSD

from csvwlib.utils import datatypeutils
from csvwlib.utils.rdf.CSVW import CONST_STANDARD_MODE
from csvwlib.utils.json.CommonProperties import CommonProperties
from csvwlib.utils.json.JSONLDUtils import JSONLDUtils
from csvwlib.utils.rdf.Namespaces import Namespaces
from csvwlib.utils.rdf.OntologyUtils import OntologyUtils
from csvwlib.utils.rdf.RDFGraphUtils import RDFGraphUtils
from csvwlib.utils.url.PropertyUrlUtils import PropertyUrlUtils
from csvwlib.utils.url.UriTemplateUtils import UriTemplateUtils

CSVW = Namespace('http://www.w3.org/ns/csvw#')


class ToRDFConverter:

    def __init__(self, atdm, metadata):
        super().__init__()
        self.graph = Graph()
        self.metadata = metadata
        self.atdm = atdm
        self.mode = CONST_STANDARD_MODE
        RDFGraphUtils.add_default_bindings(self.graph)
        RDFGraphUtils.add_bindings_from_metadata(self.graph, metadata)

    def convert(self, mode=CONST_STANDARD_MODE, format=None):
        self.mode = mode
        main_node = BNode()
        if mode == CONST_STANDARD_MODE:
            self.graph.add((main_node, RDF.type, CSVW.TableGroup))
            self._add_file_metadata(self.metadata, main_node)
        # TODO: 4.5 non-core annotations

        for table_metadata, table_data in zip(self.metadata['tables'], self.atdm['tables']):
            self._parse_table(main_node, table_metadata, table_data)

        return self.graph if format is None else self.graph.serialize(format=format).decode()

    def _parse_table(self, main_node, table_metadata, table_data):
        table_node = URIRef(table_metadata['@id']) if '@id' in table_metadata else BNode()
        property_url = table_metadata['url'] + '#'
        if 'propertyUrl' in table_metadata['tableSchema']:
            property_url = table_metadata['tableSchema']['propertyUrl']

        if self.mode == CONST_STANDARD_MODE:
            self.graph.add((main_node, CSVW.table, table_node))
            self.graph.add((table_node, RDF.type, CSVW.Table))
            self.graph.add((table_node, CSVW.url, URIRef(table_metadata['url'])))
            self._add_file_metadata(table_metadata, table_node)

        for index, atdm_row in enumerate(table_data['rows']):
            if self.mode == CONST_STANDARD_MODE:
                row_node = BNode()
                self._parse_generic_row(atdm_row, table_node, table_metadata, property_url, row_node, table_data)
            else:
                dummy = BNode()
                row_node = BNode()
                self._parse_row(atdm_row, row_node, dummy, table_metadata, property_url, table_data)
                self.graph.remove((dummy, CSVW.describes, row_node))
            self.parse_virtual_columns(row_node, atdm_row, table_metadata)

    def parse_virtual_columns(self, row_node, atdm_row, table_metadata):
        for virtual_column in table_metadata['tableSchema']['columns']:
            if 'virtual' not in virtual_column or virtual_column['virtual'] is False:
                continue
            subject = URIRef(UriTemplateUtils.insert_value(virtual_column['aboutUrl'], atdm_row, '',
                                                           table_metadata['url']))
            predicate = Namespaces.get_term(virtual_column['propertyUrl'])
            if predicate:
                if 'valueUrl' in virtual_column:
                    obj = UriTemplateUtils.insert_value(virtual_column['valueUrl'], atdm_row, '', table_metadata['url'])
                    obj = CommonProperties.expand_property_if_possible(obj)
                    self.graph.add((subject, predicate, URIRef(obj)))
                elif 'default' in virtual_column: 
                    self.graph.add((subject, predicate, self._object_node(virtual_column['default'], virtual_column, atdm_row, '')))
                if self.mode == CONST_STANDARD_MODE:
                    self.graph.add((row_node, CSVW.describes, subject))
            else:
                print(f"term {virtual_column['propertyUrl']} not in namespaces")

    def _add_file_metadata(self, metadata, node):
        language = JSONLDUtils.language(self.metadata.get('@context',[]))
        for key, value in metadata.items():
            if CommonProperties.is_common_property(key) or key == 'notes':
                triples = CommonProperties.property_to_triples((key, metadata[key]), node, language)
                self.graph.addN(triple + (self.graph,) for triple in triples)

    def _parse_generic_row(self, atdm_row, table_node, metadata, property_url, row_node, atdm_table):
        self.graph.add((table_node, CSVW.row, row_node))
        self.graph.add((row_node, RDF.type, CSVW.Row))
        self.graph.add((row_node, CSVW.rownum, Literal(atdm_row['number'], datatype=XSD.integer)))
        self.graph.add((row_node, CSVW.url, URIRef(atdm_row['@id'])))
        if 'rowTitles' in metadata['tableSchema']:
            col_names = metadata['tableSchema']['rowTitles']
            for col_name in col_names:
                col_value = atdm_row['cells'][col_name][0]
                self.graph.add((row_node, CSVW.title, Literal(col_value)))
        values_node = BNode()
        self._parse_row(atdm_row, values_node, row_node, metadata, property_url, atdm_table)

    def _parse_row(self, atdm_row, values_node, row_node, metadata, property_url, atdm_Table):
        if not all(map(lambda column: 'aboutUrl' in column, metadata['tableSchema']['columns'])):
            self.graph.add((row_node, CSVW.describes, values_node))
        self._parse_row_data(atdm_row, values_node, metadata, property_url, row_node, atdm_Table)

    def _parse_row_data(self, atdm_row, subject, table_metadata, property_url, row_node, atdm_table):
        top_level_property_url = property_url
        atdm_columns = atdm_table['columns']
        for index, entry in enumerate(atdm_row['cells'].items()):
            col_name, values = entry
            for col_metadata in atdm_columns:
                if col_metadata['name'] == col_name:
                    break
            if col_metadata.get('suppressOutput', False):
                continue
            property_url = col_metadata.get('propertyUrl', top_level_property_url)
            if 'aboutUrl' in col_metadata:
                subject = UriTemplateUtils.insert_value_rdf(col_metadata['aboutUrl'], atdm_row, col_name,
                                                            table_metadata['url'])
                if self.mode == CONST_STANDARD_MODE:
                    self.graph.add((row_node, CSVW.describes, subject))

            property_namespace = PropertyUrlUtils.create_namespace(property_url, table_metadata['url'])
            predicate = self._predicate_node(property_namespace, property_url, col_name)
            self._parse_cell_values(values, col_metadata, subject, predicate, atdm_row, table_metadata['url'])

    def _parse_cell_values(self, values, col_metadata, subject, predicate, atdm_row, tm_url):
        """ Parses single cell value, values if 'separator' is present"""
        if 'ordered' in col_metadata and col_metadata['ordered'] is True and len(values) > 1:
            next_item = BNode()
            rdf_list = next_item
            values_count = len(values)
            for i in range(values_count):
                item = next_item
                self.graph.add((item, RDF.first, Literal(values[i])))
                if i != values_count - 1:
                    next_item = BNode()
                    self.graph.add((item, RDF.rest, next_item))
            Collection(self.graph, rdf_list)
            self.graph.add((subject, predicate, rdf_list))
        else:
            for value in values:
                object_node = self._object_node(value, col_metadata, atdm_row, tm_url)
                self.graph.add((subject, predicate, object_node))

    @staticmethod
    def _object_node(value, col_metadata, atdm_row, tm_url):
        if 'valueUrl' in col_metadata:
            return UriTemplateUtils.insert_value_rdf(col_metadata['valueUrl'], atdm_row, col_metadata.get('name'), tm_url)
            return ValueUrlUtils.create_uri_ref(value, col_metadata['valueUrl'], col_metadata)
        else:
            lang = col_metadata.get('lang')
            if not datatypeutils.is_compatible_with_datatype(value, col_metadata.get('datatype')):
                datatype = None
            else:
                datatype = OntologyUtils.type(col_metadata)

            lang = None if datatype is not None else lang
            return Literal(value, lang=lang, datatype=datatype)

    @staticmethod
    def _normalize_to_uri(string):
        if string in [None, '']:
            return ''
        string = quote(string, safe='')
        string = string.replace('-', '%2D')
        return string

    @staticmethod
    def _predicate_node(namespace, property_url, col_name):
        col_name = ToRDFConverter._normalize_to_uri(col_name)
        if '{' in property_url:
            return namespace.term(col_name)
        else:
            if CommonProperties.is_common_property(property_url):
                return URIRef(CommonProperties.expand_property_if_possible(property_url))
            else:
                if property_url.endswith('#'):
                    return URIRef(property_url + col_name)
                else:
                    return URIRef(namespace)
