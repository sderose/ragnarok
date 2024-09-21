# Point to this from the pudb config file
#
#import inspect
from pudb.var_view import default_stringifier

from basedom import Node

def custom_stringifier(obj):
    if (isinstance(obj, Node)):
        filtered_dict = {
            k: v for k, v in obj.__dict__.items()
                if not isinstance(v, property) and not callable(v)
        }
        return default_stringifier(filtered_dict)

    return default_stringifier(obj)
