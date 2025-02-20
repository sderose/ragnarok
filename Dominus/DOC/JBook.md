==jsondocs==

This library provides a complete and round-trippable mapping
between XML or HTML, and JSON, mainly intended for document-ish
data, not struct-ish data.

It will handle any XML, and convert it to JSON without losing information.
The conversion handles attributes, PIs, comments, CDATA, mixed content, etc.,
And is fairly easy to understand and read.

A simple example:

    <html>
        <head>
            <title>My document</title>
        </head>
        <body>
            <h1>Introduction</1>
            <p id="p1">This is a <i>very</i> short document.</p>
            <hr />
            This is some "literal" &lt;text&gt;.
            <!--Pay no attention to the text behind the curtains.-->
        </body>
    </html>

becomes the JSON below (the first hash is mainly boilerplate to make it
easy to identify versions, what HTML or XML tag-set is in use, etc.):

    [{ "~":"JBook" },
      [{ "~":"html", "xmlns:html":"http://www.w3.org/1999/xhtml" },
        [{ "~":"html:head" },
          [{ "~":"title" }, "My document" ]
        ],
        [{ "~":"body" },
          [{ "~":"p", "id":"stuff" },
            "This is a ", [{ "~":"i" }, "very" ], " short document." ]
        ],
        [{ "~":"hr" } ],
        [{ "~":"#cdata" }, "This is some \"literal\" <text>." ],
        [{ "~":"#comment" }, "Pay no attention to the text behind the curtains." ],
      ]
    ]

Header-ish information can be included at option, as true HTML and XML:

    [{ "~":"JBook", "#JBookVersion":"0.9",
        "!xmlversion":"1.1", "!encoding":"utf-8", "!standalone":"yes",
        "!doctype":"html", "!systemId":"http://w3.org/html" }...


==Description==

Every document component, such as a heading, list, item, paragraph, or
inline item, corresponds to a single JSON array (text content
is just strings). Each of these arrays starts with a single hash,
must always have a "~" item giving the component type ("p", etc.).
Special components use reserved names, mostly the same as the ones in DOM
(#pi, #comment, #cdata, etc). Properties also go in here, such as attributes
of elements, or several special properties at the very top.

By default this convertor changes escaped special characters to literals
where allowed (for example, JSON \u2022 or HTML &bull; for BULLET).
But you can opt to have certain characters (say, all non-ASCII?) escaped in
output.

Incoming JSON may include ints, floats, booleans, and nulls in content;
they are just treated as the equivalent strings.

If you can find a simpler/cleaner mapping that supports everything, tell me.
But use an example like a web page or published article, not like a CSV; I've
seen way too many solution that only cover trivial cases.

This JSON is a bit longer than the same thing in XML or HTML.
That's mostly because of quotes. But the difference isn't that big.

I'm considering letting the property-list dict be empty (or even ommitted?)
if it (a) would only have "~", and with the same value as it's immediate
prior sibling (this is a pretty common case in documents, and is very
like the "<|>" extension).

        [{ "~":"body" },
          [{ "~":"p" }, "This is a short paragraph." ]
          [{}, "And so is this." ]
          [{}, "And this." ]
        ]

This will not convert arbitrary JSON to XML. You can do that with
many other tools.


==Schemas==

Schemas do not need to be included or referenced, but they can be.

This is still being finalized, but will likely look something like below.
The example is DTD-like, but XML Schema may also be supported.

    [{ "~":"DOCTYPE", "root":"html", "systemId":"...",
        "elementFold":true, "entityFold":false },

      [{ "~":"ELEMENT", "name":"br", "type:"EMPTY" } ],
      [{ "~":"ELEMENT", "name":"i", "type:"PCDATA" } ],
      [{ "~":"ELEMENT", "name":"div", "type:"ANY" } ],
      [{ "~":"ELEMENT", "name":"html", "type:"MODEL", "model":"(head, body)" } ],

      [{ "~":"ENTITY", "type":"parameter", "name":"chap1", "systemId":"..." } ],
      [{ "~":"ENTITY", "name":"em", "data":" -- " } ],
      [{ "~":"ATTLIST", "for":"p" },
        [{ "~":"ATT", "name":"id", "type":"ID", "dft":"#IMPLIED" } ],
        [{ "~":"ATT", "name":"class", "type":"NMTOKENS", "use":"#FIXED",
            "default":"normal" } ]
        [{ "~":"ATT", "name":"just",
            type:"(left|right|center)", default:"left" } ]
      ]
      [{ "~":"NOTATION", name:"png", "publicId":"..." } ]
    ]

