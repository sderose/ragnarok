#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
#pylint: disable=W0613, W0212
#pylint: disable=E1101
#
#import re
#from collections import OrderedDict
#from enum import Enum
#from typing import Any, Callable, Dict, List, Union
#import logging

import XMLRegexes

import BaseDOM
import DocumentType
import DOMBuilder
import XMLStrings
# Node, Leaf, etc. not used

xr = XMLRegexes.XMLRegexes()
NmToken = str


###############################################################################
#
def getDOMImplementation(name:str=None, features=None):
    #return DOMImplementation(name, features)
    return DOMImplementation


def registerDOMImplementation(self, name:str, factory):
    pass

def getImplementation():
    return None  #DOMImplementation?

def usePythonExceptions():
    BaseDOM.DOMSTRING_SIZE_ERR              = IndexError
    BaseDOM.HIERARCHY_REQUEST_ERR           = ValueError
    BaseDOM.INDEX_SIZE_ERR                  = IndexError
    BaseDOM.INUSE_ATTRIBUTE_ERR             = ValueError
    BaseDOM.INVALID_CHARACTER_ERR           = ValueError
    BaseDOM.NO_DATA_ALLOWED_ERR             = ValueError
    BaseDOM.NO_MODIFICATION_ALLOWED_ERR     = ValueError
    BaseDOM.NOT_FOUND_ERR                   = KeyError
    BaseDOM.NOT_SUPPORTED_ERR               = ValueError
    BaseDOM.WRONG_DOCUMENT_ERR              = ValueError

    BaseDOM.NAME_ERR                        = ValueError


###############################################################################
#
class DOMImplementation:
    name = "BaseDOM"
    version = "0.1"
    features = {
        "caseSensitive"    : True,
        "pythonExceptions" : True,
        "verbose"          : 0,
    }

    def __init__(self, name:str=None, features=None):
        if (name): DOMImplementation.name = name
        if (features):
            #for k, v in features.items:
            #    DOMImplementation.features[k] = v
            pass

    @staticmethod
    def hasFeature(feature, version):
        if (feature in DOMImplementation.features):
            return DOMImplementation.features[feature]
        return False

    @staticmethod
    def createDocument(namespaceUri:str, qualifiedName:NmToken, doctype
        ) -> BaseDOM.Document:
        doc = BaseDOM.Document(namespaceUri, qualifiedName, doctype)
        doc.documentElement = doc.createElement(qualifiedName)
        return doc

    @staticmethod
    def createDocumentType(qualifiedName:NmToken, publicId:str, systemId:str
        ) -> DocumentType.DocumentType:
        loc = XMLStrings.getLocalPart(qualifiedName)
        if (not xr.isLocalName(loc)):
            raise ValueError(
                "createDocumentType: qname '%s' isn't." % (qualifiedName))
        return DocumentType.DocumentType(qualifiedName, publicId, systemId)

    def parse(self, filename_or_file:str, parser=None, bufsize:int=None
        ) -> BaseDOM.Document:
        dbuilder = DOMBuilder.DOMBuilder()
        theDom = dbuilder.parse(filename_or_file)
        return theDom

    def parse_string(self, s:str, parser=None):
        dbuilder = DOMBuilder.DOMBuilder()
        theDom = dbuilder.parse_string(s)
        return theDom

    # minidom-specific methods:
    #unlink
    #writexml(writer, indent="", addindent="", newl="")
    #toxml(encoding=None)
    #toprettyxml(indent="\t", newl="\n", encoding=None)
