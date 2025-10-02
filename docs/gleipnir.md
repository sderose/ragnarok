##Information on Gleipnir##

Gleipnir is responsible for serializing YGGdrasil/DOM structures to XML.

"Gleipnir" is Old Norse for "open one", and is the name for the unbreakable
bindings that hold back the wolf Fenrir.

* '''escapeAttribute'''(string, quoteChar='"', addQuotes:bool=True)

Escape the string as needed for it to
fit in an attribute value, including the 'quoteChar' to
be used around the value. Most people seem to use double quote, but single
quote is allowed in XML. You can specify which you plan to use, and that
one will be escaped in 'string'. 'string' should not already be quoted.
If 'addQuotes' is set, a 'quoteChar' is added to each end.
Does not yet support curly quotes.

* '''escapeText'''(string)

Escape the string as needed for it to
fit in XML text content ("&", "<", and "]]>").
Some software escapes all ">", but that is not required. This method only
escape ">" when it follows "]]" (cf FormatOptions.escapeGT).

* '''escapeCDATA'''(string)

Escape the string as needed for it to
fit in a CDATA marked section (only ']]>' is not allowed).
XML does not specify a way to escape ']]>'. The result produced here is "]] >".

Note: Loki has an option, little tested so far, to bring back "RCDATA" as
a marked section keyword. RCDATA means that entity and special character
references are replaced, but no tags. Effectively, "&" but not "<". That
will necessitate adding escapeRCDATA().

* '''escapeComment'''(string)

Escape the string as needed for it to
fit in a comment, where '--' is not allowed.
XML does not specify a way to escape within comments.
The result produced here is "- -".

* '''escapePI'''(string)

Escape the string as needed for it to
fit in a processing instruction (just '?>').
XML does not specify a way to escape this. The result produced here is "?&gt;".

* '''escapeASCII'''(s, width=4, base=16, htmlNames=True))

Escape the string as needed for it to fit in XML text content,
''and'' recode any non-ASCII characters as XML
entities and/or numeric character references.
`width` is the minimum number of digits to be used for numeric character references.
`base` must be 10 or 16, to choose decimal or hexadecimal references.
If `htmlNames` is True, HTML 4 named entities are used when applicable,
with numeric character references used otherwise.
