==Notes on documenttype.py==

This library provides a basic interface to schema information, whether created
via the API, an XML (or perhaps SGML) DTD, an XML Schems, or (eventually) a Relax-NG schema (I'm less
familiar with those, so that may be a while). The idea here is to get any
schema into a common API that parsers and validators can talk to.

There are a lot of classes, but most are quite small and correspond closely
to SGML/HTML/XML/XSD notions. Enums in here generally include the union
of possibilities (for example, #CURRENT has a defined name even though
it is only used in SGML).
Unnamed options such as having NO repetition or no seq operator (as for
singleton model groups) have corresponding enum values for expliciteness.


* SimpleType/attribute stuff (perhaps split to separate file?)

    ** DerivationLimits(FlexibleEnum): Ways to derive types
    (extension, etc)

    ** SimpleType(dict): Basicallly like XSD, a name, base type
    (plus corresponding Python type if any), and selected facets

    ** XsdType(dict): The set of built-in XSD datatypes, with their facets

    ** DateTimeFrag: Support for fragmentary dates/times per XSD

    ** XsdFacet(Enum): The set of known XSD facets

    ** AttributeDef: A single attribute with name/type/default

    ** AttlistDef(dict): A bundle of attributes. These must be attached to
the Doctype, and to their element(s)


* ComplexType(SimpleType): Basically like XSD or SGML Element

    ** ContentType(FlexibleEnum): ANY, EMPTY, etc., or X_MODEL

    ** DclType(FlexibleEnum):  Attribute declared types (cf XsdType)

    ** DftType(FlexibleEnum):  Attribute defaults (#IMPLIED etc., or X_LITERAL)

    ** SeqType(FlexibleEnum):  OR vs. SEQ vs. the late AND

    ** RepType(FlexibleEnum):  *?+ or {} like XSD min/maxOccurs

    ** ModelItem: A token + RepType in a content model

    ** ModelGroup: A group in a content model

    ** Model(ModelGroup): An *entire* content model or declared content value

    ** ElementDef(ComplexType): An element declaration (name(s?) plus Model)
    Cf ComplexType


* Entity stuff

    ** EntitySpace(FlexibleEnum): What kinds of entities we got?
    parameter, general, ndata, maybe sdata

    ** EntityParsing(FlexibleEnum): Parsing constraint on entity

    ** EntityDef: An entity declaration


* Notation stuff (treated as a quasi-entity)

    ** Notation: A notation declaration: name, publicId, systemId

* Document stuff

    ** DocumentType(Node):

