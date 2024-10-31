==jsondocs==

This library provides a complete and round-trippable mapping
between XML and JSON.

It will handle any XML you can come up with, and convert it to
isomorphic JSON, using conventions the author calls "JSON-X".
The conversion won't lose PIs, comments, CDATA, mixed content, etc.
And the mapping is easy to understand and read.

A simple example:

    <html>
        <head>
            <title>My page</title>
        </head>
        <body>
            <h1>Introduction</1>
            <p id="p1">This page is <i>very</i> important.</p>
        </body>
    </html>

becomes:

    [{ "#name":"html" },
        [{ "#name":"head" },
            [{ "#name":"title" }, "My page" ]
        ]
        [{ "#name":"body" },
            [{ "#name":"h1" }, "Introduction" ],
            [{ "#name":"p", "id":"p1" }, "This page is ",
                [{ "#name":"i" }, "very" ], " important."
            ]
        ]
    ]

Every XML node corresponds to a single JSON array, except text nodes
which are just strings. Every such array has a hash as its first item,
which always has a "#name" item with the element type or a
reserved word for special nodes (#pi, #comment, #cdata). Things that
have attributes (or special properties such as the name and system
identifier for DOCTYPE), also have those in the hash.

Other xml/json conversions I've seen leave out all but the most trivial
cases, or do a dizzying variety of different things for them. This format,
you've probably already memorized (maybe I should have called it
"correct XML JSON staple"?)

By default this convertor expands references to special characters
(via entity syntax in XML or backslash syntax in JSON). But you can
opt to have certain characters (say, all non-ASCII?) escaped in
output. If you really want escaped characters preserved, you can
use a JSON or XML parser that doesn't expand them (both are uncommon),
or escape them again before input and unsecape again afteward:
    XML &lt; becomes &amp;lt;
    JSON \xA0 becomes \\xA0

If you can find a simpler/cleaner mapping, tell me. But make sure it
works not just for CSV-like data, but for documents -- convert a random
web page to it and see if you can still read it.

Now, you will have noticed that this JSON is a bit longer than the XML;
mostly because of quotes, plus the {} around the name and attributes
(you do save one the end-tag, though it's a bit harder to find the
problem if you drop one). But the difference isn't that big

This will not go the other way. If you have JSON that is not like this
(an array in which every array consists of a leading hash with a #name,
following by any number of arrays and/or strings), it won't go. Actually,
other JSON scaler types will be accepted on input (int, float, booleans,
and nil), but are just converted to strings. I may add an option to
retain them as special nodes like:
    <scalar type="int" value="999">

This would allow retaining them with type intact, and be extensible to
other types, such as XSD numeric types, complex numbers, datimes,
urls, identifiers, or even vector types (string types can of course be
Goedelized into big integers, so can be considered scalars if you like).

Or you can convert any JSON to this form and then run it through,
after which you can go back and forth all you want.
I'll probably add that if people asks.
