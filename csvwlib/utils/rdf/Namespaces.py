from rdflib import URIRef
from rdflib.namespace import Namespace

from csvwlib.utils.rdf import CSVW


class Namespaces:
    """ RDFa initial context
    https://www.w3.org/2011/rdfa-context/rdfa-1.1
    """

    @staticmethod
    def all():
        return {
            # Vocabulary Prefixes of W3C Documents
            'as': Namespace('https://www.w3.org/ns/activitystreams#'),
            'csvw': Namespace('http://www.w3.org/ns/csvw#'),
            'dcat': Namespace('http://www.w3.org/ns/dcat#'),
            'dqv': Namespace('http://www.w3.org/ns/dqv#'),
            'duv': Namespace('https://www.w3.org/TR/vocab-duv#'),
            'grddl': Namespace('http://www.w3.org/2003/g/data-view#'),
            'ldp': Namespace('http://www.w3.org/ns/ldp#'),
            'ma': Namespace('http://www.w3.org/ns/ma-ont#'),
            'oa': Namespace('http://www.w3.org/ns/oa#'),
            'org': Namespace('http://www.w3.org/ns/org#'),
            'owl': Namespace('http://www.w3.org/2002/07/owl#'),
            'prov': Namespace('http://www.w3.org/ns/prov#'),
            'qudt': Namespace('http://qudt.org/1.1/schema/qudt#'),
            'qb': Namespace('http://purl.org/linked-data/cube#'),
            'rdf': Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
            'rdfa': Namespace('http://www.w3.org/ns/rdfa#'),
            'rdfs': Namespace('http://www.w3.org/2000/01/rdf-schema#'),
            'rif': Namespace('http://www.w3.org/2007/rif#'),
            'rr': Namespace('http://www.w3.org/ns/r2rml#'),
            'sd': Namespace('http://www.w3.org/ns/sparql-service-description#'),
            'skos': Namespace('http://www.w3.org/2004/02/skos/core#'),
            'skosxl': Namespace('http://www.w3.org/2008/05/skos-xl#'),
            'ssn': Namespace('http://www.w3.org/ns/ssn/'),
            'sosa': Namespace('http://www.w3.org/ns/sosa/'),
            'time': Namespace('http://www.w3.org/2006/time#'),
            'void': Namespace('http://rdfs.org/ns/void#'),
            'wdr': Namespace('http://www.w3.org/2007/05/powder#'),
            'wdrs': Namespace('http://www.w3.org/2007/05/powder-s#'),
            'xhv': Namespace('http://www.w3.org/1999/xhtml/vocab#'),
            'xml': Namespace('http://www.w3.org/XML/1998/namespace'),
            'xsd': Namespace('http://www.w3.org/2001/XMLSchema#'),
            # Widely used Vocabulary prefixes
            'cc': Namespace('http://creativecommons.org/ns#'),
            'ctag': Namespace('http://commontag.org/ns#'),
            'dc': Namespace('http://purl.org/dc/terms/'),
            'dcterms': Namespace('http://purl.org/dc/terms/'),
            'dc11': Namespace('http://purl.org/dc/elements/1.1/'),
            'foaf': Namespace('http://xmlns.com/foaf/0.1/'),
            'gr': Namespace('http://purl.org/goodrelations/v1#'),
            'ical': Namespace('http://www.w3.org/2002/12/cal/icaltzd#'),
            'og': Namespace('http://ogp.me/ns#'),
            'rev': Namespace('http://purl.org/stuff/rev#'),
            'sioc': Namespace('http://rdfs.org/sioc/ns#'),
            'v': Namespace('http://rdf.data-vocabulary.org/#'),
            'vcard': Namespace('http://www.w3.org/2006/vcard/ns#'),
            'schema': Namespace('http://schema.org/'),
        }

    @staticmethod
    def get(prefix):
        return Namespaces.all().get(prefix)

    @staticmethod
    def get_term(string):
        if string in CSVW.term_mappings.keys():
            uri = CSVW.term_mappings[string]
            if uri.startswith('http'):
                return URIRef(uri)
            return Namespaces.get_term(uri)
        if string == '@type':
            return Namespaces.get('rdf').type
        prefix, term = string.split(':', 1) if string is not None else ('', '')
        return Namespaces.get(prefix).term(term) if prefix in Namespaces.all() else None

    @staticmethod
    def replace_url_with_prefix(url):
        """ Replaces absolute URL with prefix:term if domain is in known
        namespaces """
        for prefix, namespace in Namespaces.all().items():
            if url.startswith(namespace):
                return url.replace(namespace, prefix + ':')
        return url


