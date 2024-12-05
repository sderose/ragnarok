==Syntax experiments==

These are just notes on things I've seen proposed, or thought of,
that *might* potentially be useful, or worth looking at. Or not....

==Shorttag-ish==

* Empty end tags
    <p>...</>

* Restart
    <td>foo<|>bar<|>baz</td>
    Or <>?

* Unquoted attribute values
    <p class=foo12>

* Boolean attribute shorthand
    <p +spam -eggs>


==Schema avoidance :)==

* Default-set (on first instance)
    <table border!="border">
    or ≝ ? U+0225d

* Attr type-set (on first instance)  -- prob vs. ns!
    <p class:NMTOKENS="">

Especially valuable for ID, IDREF, anyURI, ENTITY, NOTATION, language


==ID extensions==

* Co-index or ID suffixes?
cf rank; tagml |layers; mecs numbers: are numbers local or global?

* QID --- IDs with namespaces

* COID -- must be >1, on same eltype, unique within eltype

* SCOPEID -- unique within (nearest?) ancestor of type

* STACKID -- value is accumulated by attr type


==Overlap and structure extensions==

* Simultaneous start/end
    <b|i>...</i|b>

* Multistart/end:
    <div/title>Introduction</title>...

* Suspend/resume
    <q>Hello<-q>, he said. <+q>How are you today?</q>
    See https://huygensing.github.io/TAG/TAGML/

* Co-index (or ID) suffixes (local or global?):
    <q@1>....<q@2>...</q@1>...</q@2>

* Olist closing (see MECS)
    <b>...<i>...</b>...</i>


==DTD/Schema extensions==

* Dcl to enable all Annex D / HTML entities in one step.

* Unicode character-name entities like in some regex lgs

* Multiple SDATA in one dcl
    <!CHAR bull 0x2022>
    <!SDATA nbsp 160 msp 0x2003...>

* LITERAL declaration, just like ENTITY except only qlit value. Meh.
     <!LITERAL foo "hello">

* CTYPE declarations to correspond to XSD complex types.?They
can be referenced within content models via %xxx;. Think of them as
custom reserved words; they cannot be named "PCDATA" etc). They are retained
when the model is parsed. ???
    <!CTYPE fontish "i b u tt">

    ** Possibly add xsd-like operations on them?
        <!CTYPE inlines (#fontish) - (tt) + (em string sup sub)>

    ** * BASE declaration(s)
        <!BASE "c:\\stuff" "/Users/jsmith/XML/entities"...>

    If you can have > 1, they need names and a way to reference. Entity subtype?

* SYSTEM identifier resolution

    ** The time-honored *nix PATH mechanism, say SYSTEMIDPATH?

    ** Let SYSTEM identifiers take multiple quoted literals,
    and try them in order.

    ** Let system identifiers interpolate environment variables.

    ** Allow fragment identifiers on SYSTEM identifiers


==Elements==

* Reintroduce name groups for what's being declared.

* Add {m,n} suffix where [*+?] go im models.

* Track what % ents showed up in models/dcls

* Add content type for ANY_ELEMENT (but no #PCDATA)

* Add something like inclusion exceptions -- global or element-specific mixins...


==Attributes==

* Allow curly and angle quotes

* Add all the XSD built-in datatypes to DTDs.

* Let attribute types take a rep indicator (all but CDATA?).

* Declare global attributes.
    <!ATTLIST * id #IMPLIED...>

* Track which attrs were declared together?


==Namespaces==

* Declare Namespace Defaults for Specific Element names

* Prohibit prefix redefinition

* Global ns only


==Unicode awareness==

* Curly quotes for attrs and such

* SHORTREF-like treatment for quotes

* emdash in comments to avoid tedious fixing when people much it up.

* rule out C1 area

* Constrain charset by block or script?

* Constrain charset by xml:lang


==XSHORTREF==

* Backslashing
    \\ \xA0 \u00A0 \{bull}
* Simplified shortref?
    <!MAP (tr|ul|ol) "\|" "</td><td>"
                     "||" "<tr><td>"
                     "\n" "</tr>">
    <!MAP * "\*(.*?)\*" "<em>\1</em>">

What are useful cases for this?
    MarkDown: "''(\+?)''" -> "<em>\1</em>"
    TEX: \\(\w+){(.*)} -> "<\1>\2</\1>"
    Quotes:  "\s['&quot;“](.*?)['&quot;”]" -> "<q>\1</q>"
    Chars:  "'" -> '&rsquo;'

    \L \U for case
    \C to suppress further parsing
    \R to suppress tag recongition


==Unformed==

* Way to avoid <a href="long...uri">long...uri</a>

* Way to signal truly unordered children (rules out PCDATA?)

* Way to request datatyped attrs (or even elements, a la HTML DOM)

* Let CDATA MS take a mime type or NOTATION name or some such

