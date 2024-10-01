Generate a ton of picky test cases for an XML parser.

==To do==

* Coverage re-check

* Basic tests still needed (?)
** eachNode

* Much more on namespaces

* lookupNamespaceURI
** For DocumentFragment nodes: It will check the child elements of the fragment.
** Allow on Document nodes
* Finish charstestXmlNameUnicode.py
* Option to test all HTML named entities
* Integrate Whitespace, case, unorm options
* Test super-long &#x0000000XX, names, comments, etc.

* Questions
** Can you change ns defs after loading?

* Integrations
** Hook up to generate a pack of XML files (marked good/bad)
** Hook up to parse directly given a parser.
** Hook up to generate a standard test result, to compare parsers with?

* makeTestDoc.py options for max depth, name-length, content length for
** text
** attr values
** comments
** pi target and data
** cdata content
** numeric ent leading 0s
** ent names
** excess whitespace in markup

"""

okXmlDcl = """<?xml version="1.0" encoding='utf-8'?>"""

okDoctype = """<!DOCTYPE tei PUBLIC "-//some/fpi" "/home/cmsmcq/dts/p3.dtd">"""

docStub = (
"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE TEI.3 PUBLIC "-//TEI P3//DTD Main Document Type//EN" "tei3.dtd">
<TEI.3>
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Title of the Document</title>
        <author>Author Name</author>
      </titleStmt>
      <publicationStmt>
        <p>Publication Information</p>
      </publicationStmt>
      <sourceDesc>
        <p>Information about the source</p>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <p>Your text goes here.</p>
        %s
      </div>
    </body>
  </text>
</TEI.2>
""")

class WFErrors(Enum):
    """Organized by relevant nodeType * 10.
    """
    NOT_WF              = 0   # Not Well-Formed (General concept)

    MISPLACED_DECL      = 1   # Misplaced XML Declaration (2.8)
    BAD_ENCODING        = 2   # Improper Encoding (4.3.3)

    UNMATCHED_TAG       = 11  # Unmatched Tag (3.1)
    MISMATCHED_END      = 12  # Mismatched End Tag (3.1)

    DUP_ATTR            = 21  # Duplicate Attribute (3.1)
    ILLEGAL_ATTR_VAL    = 22  # Illegal Attribute Value (3.1)

    INVALID_CHAR        = 31  # Invalid Character (2.2)

    # CDATA = 4?

    UNDECLARED_ENT      = 51  # Undeclared Entity Reference (4.1)
    RECURSIVE_ENT       = 52  # Recursive Entity Reference (4.1)
    EXT_ENT_IN_ATTR     = 53  # External Entity Reference in Attribute Value (3.1)
    BINARY_ENT          = 54  # Binary Entity Reference (4.2.2)

    # PI = 7
    # Comment = 8?

    BAD_DTD             = 101  # Incorrect Document Type Declaration (2.8)
    ATTR_MARKUP_SUBSET  = 102  # Attribute-Like Markup in Internal Subset (2.8)
    INCOMPLETE_MARKUP   = 103  # Incomplete Markup Declaration (Various sections)

    UNCLOSED_TOKEN      = 201  # Unclosed Token (Various sections)
    UNBOUND_NS          = 202  # Unbound Namespace Prefix (Namespaces in XML 3e)

XmlDcls = """

<?xml version="1.0" encoding = 'utf-8' standalone="yes" ?>
<?xml version="1.1"
    encoding = 'UtF-8' standalone="no" ?>
<?xml version="1.1"?>

    <?zork version="1.0" encoding="utf-8"?>
    <?xml Version="1.0" _encoding="utf-8"?>
    <?xml version="0.9" encoding="utf-8"?>
    <?xml version="1.0" _encoding="utf-8"?>
    <? xml version="1.0" encoding="utf-8"?>
    <?xml version="x" encoding="utf-8"?>
    <?xml version="1.0" encoding="utf-8" badAttr="1"?>
    <?xml encoding="utf-8"?>
"""


Comments = """
<!-- This is <ok>, as are>  and &%foo-bar -->
    <!-- This is not -- really, not -- ok. -->
"""


Dcls = """
<!ELEMENT p  (#PCDATA | i | b ) * >
<!ELEMENT p  ANY>
<!ELEMENT p  EMPTY>
<!ATTLIST p     id      ID          #IMPLIED
                style   CDATA       #FIXED ""
                class   NMTOKENS    #REQUIRED>

    <!SHORTREF foo>
    <!USEMAP   foo p>
    <!DATATAG>
"""


Cdata = """
abcde <![CDATA[ <this> &is; all &#99999999; <!DOCTYPE literal. ]]>

    <!CDATA[ foo ]]>
    <![IGNORE[ foo ]]>
    abc ]]> def

"""


Entrefs = """
<p>This is &amp; &#000000000000000065; &#x2022;  &#X0002022;</p>
<p foo="&lt; &amp; &quot; &apos; &gt;"</p>
<p foo='&lt; &amp; &quot; &apos; &gt;'</p>
<p foo="&lt; &amp; &quot; &apos; &gt;"</p>
<p foo="&lt; &amp; &quot; &apos; &gt;"</p>

    <p>This is &amp; &.lt; &$x; & &#beef; &#x00FG; &<q>.</p>
    <p>Reference to an &undefined; entity.</p>
"""


Doctypes = """
<!DOCTYPE xyzzy PUBLIC "" "https//example.com/dtds/xyzzy.dtd" []>
<!DOCTYPE xyzzy_2.a SYSTEM "https//example.com/dtds/xyzzy.dtd" []>
<!DOCTYPE _xyzzy PUBLIC>
<!DOCTYPE xyzzy SYSTEM>
<!DOCTYPE xyzzy []>


    <!DOCTYPE _xyzzy PUBLIUS>
    <!DOCTYPE _xyzzy PUBLIC []>
    <!DOCTYPE _xyzzy PUBLIC <p>>
"""


Naming/chars
    bigName = ""
    for c in range(1, MAXCHAR):
        if (isXmlNameStartChar(c)):
            bigName += c
    try:
        tag = f"<{bigName}/>"
        doc = docStub % (tag)
        theImpl.parse_string(doc)
    except Exception as e:
        print("Failed")

    buf = ""
    for i in range(1, MAXDEPTH): buf += "<div_%d>" % (i)
    buf += "ahhhhhh"
    for i in reversed(range(1, MAXDEPTH)): buf += "</div_%d>" % (i)

    for i in range(1, 32):
        if (i in [ 9, 10, 13 ]):
        doc = docStub % (f"<p>{chr(i)}</p>")

Tags = """
<p id="_foo" class="foo bar  baz &#65;" z=''>well?</p>
<p    \t  id="_foo" class
=
"foo bar  baz"
           />

    < uh, what?
    <p="x"/>
    <:foo/>
    <(concur)p/>
    <para
    <para id>
    <para id/>
    <para id=>
    <para id=">
    <para id=""
    <p id="_foo" class=“”/>
    <p id="_foo" class=12/>
    <p .id="10"/>
    <p border />
    <p border:10pt; />
"""


Tree = """
<p><a><b><c><d><c><d>wow</d></c></d></c></b></a></p>

    <p>well, <i>they <b>said</i> it was</b> ok.</p>
    <p>well, <i><b> they said it was</i></b> ok.</p>
    <p>well, <i>they said it was</tt> ok.</p>
    <p id="_foo" class="foo bar  baz"/></p>
    <p id="_foo" class="foo bar  baz"/><!-- c --></p>
"""
