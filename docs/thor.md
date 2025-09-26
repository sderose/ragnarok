=Information on Thor, an XML parser=

Thor is a pure Python XML parser. Thor may be taken as short for "Text
Hierarchy Object Reader"; but just call it Thor.
It was originally named "xsparser", and
there may be remaining vestiges of that name.

It looks like xml.parsers.expat, and produces the same SAX events (except
that it doesn't break text at every character reference and newline -- there's
an option to do that if you want).

Thor has a few options, mainly to limit entity references so as to protect
against expansion attacks.

=Usage=

A simple usage example is in examples/ThorDriver.py.

    from thor import XSParser
    xsp = XSParser()
    xsp.readDtd("someDTD.dtd")
    xsp.openEntity("someDocument.xml")
    ...


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
