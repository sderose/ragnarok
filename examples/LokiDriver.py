#!/usr/bin/env python3
#
# Run the Thor parser on a file.
#
from typing import Dict
import loki

# Set up whatever SAX event handlers you want

def StartElement(name:str, attrs:Dict=None) -> None:
    print(f"<{name}>")
def EndElement(name:str, attrs:Dict=None) -> None:
    print(f"</{name}>")
def CharacterData(data:str="") -> None:
    print(data)

#def ProcessingInstruction(target:str="", data:str="") -> None:
#    pass
#def Comment(data:str="") -> None:
#    pass
#def StartCdataSection() -> None:
#    pass
#def EndCdataSection() -> None:
#    pass
#def StartDoctypeDecl(doctypeName:str, systemId="", publicId="",
#    has_internal_subset:bool=False) -> None:
#    pass
#def EndDoctypeDecl() -> None:
#    pass
#def Default(data:str="", *args) -> None:
#    pass
#def ElementDecl(name:str, model:str="") -> None:
#    pass
#def AttlistDecl(elname:str, attname, typ="", default="", required=False) -> None:
#    pass
#def NotationDecl(notationName:str, base="", systemId="", publicId="") -> None:
#    pass
#def EntityDecl(entityName:str, is_parameter_entity=False, value="", base="",
#    systemId="", publicId="", notationName=None) -> None:
#    pass
#def UnparsedEntityDecl(entityName:str, value="", base="",
#    systemId="", publicId="", notationName=None) -> None:
#    pass

# Instantiate the parser, attach the handlers, and go

parser = loki.Loki.ParserCreate()
parser.StartElementHandler = StartElement
parser.EndElementHandler = EndElement
parser.CharacterDataHandler = CharacterData
with open("example.xml", "rb") as ifh:
    parser.ParseFile(ifh)
