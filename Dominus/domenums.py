#!/usr/bin/env python
#
#from basedomtypes import FlexibleEnum
from types import SimpleNamespace

# Move into xmlstrings

# "'It is a most repulsive quality, indeed,’ said he.
#  ‘Oftentimes very convenient, no doubt, but never pleasing.
#   There is safety in reserve, but no attraction.'"
#        -- Jane Austen, Emma, chapter VI

### Constants

RWord = SimpleNamespace(**{
    # Reserved or conventional qname prefixes.
    "XML_PREFIX"     : "xml",
    "NS_PREFIX"      : "xmlns",
    "XSI_PREFIX"     : "xsi",

    # Attribute qnames
    "LANG_ATTR"      : "xml:lang",
    "SPACE_ATTR"     : "xml:space",
    "BASE_ATTR"      : "xml:base",
    "ID_QNAME"       : "xml:id",

    # XML namespace URIs
    "XML_PREFIX_URI" : "http://www.w3.org/XML/1998/namespace",  # as for xml:id
    "XMLNS_URI"      : "http://www.w3.org/2000/xmlns/",
    "XHTML_URI"      : "http://www.w3.org/1999/xhtml",
    "XSI_URI"        : "http://www.w3.org/2001/XMLSchema-instance",
    "XSD_URI"        : "http://www.w3.org/2001/XMLSchema",
    "XSLT_URI"       : "http://www.w3.org/1999/XSL/Transform",
    "SVG_URI"        : "http://www.w3.org/2000/svg",
    "MATHML_URI"     : "http://www.w3.org/1998/Math/MathML",

    # The namespace wildcard
    "NS_ANY"         : "##any",

    # The element name wildcard
    "EL_ANY"         : "*",

    # XML stylesheet PI target name.
    "XML_SS_TARGET"  : "xml-stylesheet",

    # Schema stuff
    "XSL_LOC_QNAME"  : "xsi:schemaLocation",
    "XSI_NLOC_QNAME" : "xsi:noNamespaceSchemaLocation",

    # Reserved nodeNames
    # (PI, ELEMENT, ENTREF, ATTR, DOCTYPE use actual names)
    "NN_TEXT"        : "#text",
    "NN_COMMENT"     : "#comment",
    "NN_CDATA"       : "#cdata",
    "NN_DOCTYPE"     : "#doctype",
    #"NN_DOCUMENT"    : "#document",
    #"NN_FRAGMENT"    : "#document-fragment",

    "NN_PI_JSONX"    : "#pi",
})
