# Point to this from the pudb config file
#
#import inspect
#
from pudb.var_view import default_stringifier

from basedom import Node, Attr

descr = """
Goals:

* Hide consts (esp. NoteType)
* Expand Enum to name
* Reduce Attr to just name/value
* ? hide is... predicates
* Show cseq for referenced nodes
* Show attrs on element?
* Show address?
"""

def custom_stringifier(obj):
    if (isinstance(obj, Node)):
        filtered_dict = {
            k: v for k, v in obj.__dict__.items()
                if not isinstance(v, property) and not callable(v)
        }
        filtered_dict["_cseq"] = obj.getPath()
        return default_stringifier(filtered_dict)

    if (isinstance(obj, Attr)):
        filtered_dict = {
            'nodeName': obj.__dict__['nodeName'],
            'value': obj.__dict__['value']
        }
        return default_stringifier(filtered_dict)

    return default_stringifier(obj)
