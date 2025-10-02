=Information on characterentities.py=

==Description==

Maintain mappings between Unicode code point values and XML/HTML NAMEs
for them. This is similar to Python
`codepoint2name` and `name2codepoint` in `html.entities`. However:

* You can define multiple names for the same codepoint.
* You can add new items, either via `add(name, codepoint)` or by
specifying a file to load (see below)
* You can delete items (this allows you to trim the list down to what
you expect, thus making uses of unexpected references cause WF errors
so you immediately catch them.
* You can define multiple maps and switch between them (I can imagine wanting
this if importing files from TEX or other sources).


==Usage==

```
    from charentities import CharacterEntities
    CE = CharacterEntities(HTML=True)
    CE.addFromPairFile("myEntDefs.txt")
    CE.delete("bull", 0x2022)
    CE.saveToFile("newVersion.csv", includeHTML=False, sep=", ", base=16)
```

The `saveToFile` saves to the first of the two file formats described
below, but you can pick the separator and the base (pass 16 for
hexadecimal like 0xFFFF; other value produce decimal).


==File formats==

Two file formats for listing special character definitions are supported:

`addFromPairFile(path)` -- this loads from a simple 2-column file, like:

```
    # My own special characters
    bull 8226
    nbsp 0xA0
    logo 0xE100
```

The rules are:
    * Leading and trailing whitespace is removed.
    * Lines that are empty or start with "#" are discarded as comments.
    * Each non-comment line consists of an XML non-qualified name, a separator
(typically spaces), and a number in any format accepted by Python `int(x, 0)`.

`addFromDclFile(path)` -- this formats lines that are simple SGML/XML/HTML
ENTITY declarations, like:

```
    <!-- My owm special characters -->
    <!ENTITY bull "*">
    <!ENTITY nbsp   "&#160;" >
    <!ENTITY   logo   "&#XE100;">
```

The rules are:
    * No interior comments (though entire comment lines are ok).
    * Only ENTITY declarations, one per line.
    * Extra whitespace (not including line-breaks) is ok.
    * The quoted part can use decimal, hex, XML predefined, and/or
    HTML 4 or 5 predefined references, or a literal character. But it must
resolve down to one character in the end. No external entities.
    * For backward compatibility with SGML files, the keyword `SDATA` is
also permitted between the name and the quoted string.


==See also==


==Known bugs and Limitations==

If you load from a file and then save back out, comments, blank lines,
and extra whitespace are lost.

It would be nice to allow multi-character values.

It would be nice to allow the right-hand side of declarations read by
`addFromDclFile(path)` to use references defined by a `CharacterEntities`
instance.


==To do==

This should be hooked up the list by Sebastian Rahtz of AMS, AFII, TEX,
and other names. This could be done by code operating over his dataset, or by
making loadable files for each system.


==History==

* 2024-09-09: Written by Steven J. DeRose.


==Rights==

Copyright 2024-09-09 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].
