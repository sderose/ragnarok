=Information on Thor, an XML parser=

Thor is a pure Python XML parser. The name may be taken as short for "Text
Hierarchy Object Reader"; but just call it Thor.
It was originally named "xsparser", and
there may be remaining vestiges of that name.

It looks like xml.parsers.expat, and produces the same SAX events (except
that it doesn't break text at every character reference and newline -- there's
an option to do that if you want).

Thor has a few other options, mainly to limit entity references so as to protect
against expansion attacks.

==Usage==

A simple usage example is in `examples/ThorDriver.py`.

```
    from thor import XSParser
    xsp = XSParser()
    xsp.readDtd("someDTD.dtd")
    xsp.openEntity("someDocument.xml")
    ...
```

To get expat like event-breaks at newlines and entity references, add
this like right after instantiating an XSParser instance:

```
    xsp.options.setOption("expatBreaks", True)
```

==SAX Events==

The events generated are named the same as in expat (and listed in
`saxplayer.py`), plus a few extras mainly for the DTD (if any).
You set callbacks to handle them, just like for expat; see `examples/ThorDriver.md`
for a simple example.

The specific events are defined in `saxplayer.py`, as a `FlexibleEnum` (q.v.)
called `SaxEvent`. FlexibleEnum is like regular Enum, but recognizes string
names and values for the members as well as Enum instances.

Note: Yggdrasil (the Ragnarok DOM implementation, aka "basedom") provides a
generator that yields events corresponding to the SAX events that would have
been generated had any given node been parsed. It is applicable to any
subtree:

    eachSaxEvent(self, attrTx:str="PAIRS", test:Callable=None) -> Tuplle

Attributes can be returned in several ways, chosen via the `attrTx` arguent,
which must be one of:

    "PAIRS"  -- as 2n arguments on START events
    "DICT"   -- as a single dict argument on START events
    "EVENTS" -- as separate ATTRIBUTE events

The `test` argument can be used to filter returned events. Each event is
passed to the given method, which should return True for the event to
be generated, otherwise False.


==Thor Options==

Options are defined with their name, datatype, and default in a dict
called `XSParserOptionDefs` (in thor.py), copied below for convenience.

When a Thor parser is instantiated, is creates an `XSPOptions` object,
initializes it from the items in `XSParserOptionDefs`, and stored it in
`self.options`. Loki (q.v.) works the same way, but adds many more options.

The Thor options fall into a few groups:

* Limiting entity recognition or expansion

* Limiting the input character set (say, disallowing C1 control characters,
private use, etc.).

* Modulating how SAX events are returned, such as casting attribute values
to Python types fitting fitting their declared types.

* Controlling how much validation is done. Full content model validation is
not finished, but XML and DTD syntax can be checked, as are attribute value types.

* A few options will eventually offer limitations on namespace use, such
as limiting to one overall, or to ones declared on the document, or prohibiting
prefixes being re-used for different URLs.

XSParserOptionDefs = {
    # Option name        type  default     description
    "utgard":           (bool, False ),  # Any Loki stuff going?

    ### Size limits and security (these are XML compatible),
    "MAXEXPANSION":     (int,  1<<20 ),  # Limit expansion length of entities
    "MAXENTITYDEPTH":   (int,  16    ),  # Limit nesting of entities
    "charEntities":     (bool, True  ),  # Allow SDATA and CDATA entities
    "extEntities":      (bool, True  ),  # External entity refs?
    "netEntities":      (bool, True  ),  # Off-localhost entity refs?
    "entityDirs":       (List, None  ),  # Permitted dirs to get ents from
    "extSchema":        (bool, True  ),  # Fetch and process external schema

    "noC0":             (bool, True  ),  # No C0 controls (XML 1.0),
    "noC1":             (bool, False ),  # No C1 controls (b/c CP1252),
    "noPrivateUse":     (bool, False ),  # No Private Use chars
    "langChecking":     (bool, False ),  # Content matches xml:lang?    TODO

    ### Attributes
    "saxAttribute":     (bool, False ),  # Separate SAX event per attribute
    "attributeCast":    (bool, False ),  # Cast to declared type        TODO

    ### Validation (beyond WF!),
    "useDTD":           (bool, False ),  # Use external DTD if available
    "valElemNames":  (bool, False ),  # Element must be declared
    "valModels":        (bool, False ),  # Check child sequences        TODO
    "valAttributeNames":(bool, False ),  # Attributes must be declared
    "valAttributeTypes":(bool, False ),  # Attribute values must match datatype

    ### Other
    "expatBreaks":      (bool, False ),  # Break at \n and entities like expat
    "nsUsage":          (bool, None  ),  # one/global/noredef/regular    TODO
}


=History=

* 2011-03-11 `multiXml` written by Steven J. DeRose.
* 2013-02-25: EntityManager broken out from `multiXML.py`.
* 2015-09-19: Close to real, syntax ok, talks to `multiXML.py`.
* 2020-08-27: New layout.
* 2022-03-11: Lint. Update logging.
* 2024-08-09: Split Manager from Reader. Use for dtdParser.
* 2024-10: Finish parsing infrastructure, DTD and extensions.
Add generally-useful non-terminals (attribute, int, float, tags,...)
* 2025: Lots of changes as Ragnarok is built. See the log files. In general:

    * Loki, the extended XML-adjacent parser with its options, is now a
      subclass of Thor.
    * Runeheim was introduced to separate character set, case, and name handling.
    * Schemera was added to provide a real DocumentType object, compatible with
      DTDs, XSDs (almost), and an extended DTD-like format that supports
      various features such as name group declarations, validation of items
      within PIs, slightly more powerful marked sections, use of XSD datatypes
      for attributes, and so on.
    * Node methods involving child nodes are in a separate Branchable class,
      which is a mix-in to Element and Document.
    * Node methods involving attributes are in a separate Attributable class,
      which is a mix-in to Element.
