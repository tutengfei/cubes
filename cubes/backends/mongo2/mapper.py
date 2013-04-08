# -*- coding: utf-8 -*-
"""Logical to Physical Mapper for MongoDB"""

import collections
from cubes.common import get_logger
from cubes.errors import *
from cubes.mapper import Mapper

__all__ = (
    "MongoCollectionMapper"
)

DEFAULT_KEY_FIELD = "_id"

"""Physical reference to a table column. Note that the table might be an
aliased table name as specified in relevant join."""
class MongoDocumentField(object):
    def __init__(self, field, match, project, encode, decode):
        self.field = field
        self.match = match
        self.project = project
        self.encode = lambda x: x
        if encode:
            self.encode = compile(encode, 'eval')
        self.decode = lambda x: x
        if decode:
            self.decode = compile(decode, 'eval')

    def match_expression(self, value, op=None):
        value = self.encode(value)
        if op is None:
            return { self.field : value }
        else:
            return { self.field : { op : value } }

    def project_expression(self):
        if self.project:
            return copy.deepcopy(self.project)
        else:
            return "$%s" % self.field

def coalesce_physical(ref):
    if isinstance(ref, basestring):
        return MongoDocumentField(ref, None, None, None, None)
    elif isinstance(ref, dict):
        return MongoDocumentField(ref.get('field'), ref.get('match'), ref.get('project'), ref.get("encode"), ref.get("decode"))
    else:
        raise BackendError("Number of items in mongo document field reference should "\
                               "be 1 (field name) or a dict of (field, match, project, encode, decode)")


class MongoCollectionMapper(Mapper):
    """Mapper is core clas for translating logical model to physical
    database schema.
    """
    def __init__(self, cube, mappings=None, **options):

        """A mongo collection mapper for a cube. The mapper creates required
        fields, project and match expressions, and encodes/decodes using
        provided python lambdas.

        Attributes:

        * `cube` - mapped cube
        * `mappings` – dictionary containing mappings

        `mappings` is a dictionary where keys are logical attribute references
        and values are mongo document field references. The keys are mostly in the
        form:

        * ``attribute`` for measures and fact details
        * ``dimension.attribute`` for dimension attributes

        The values might be specified as strings in the form ``table.column``
        (covering most of the cases) or as a dictionary with keys ``schema``,
        ``table`` and ``column`` for more customized references.

        .. In the future it might support automatic join detection.

        """

        super(MongoCollectionMapper, self).__init__(cube, **options)

        self.mappings = mappings or cube.mappings

    def physical(self, attribute, locale=None):
        """Returns physical reference as tuple for `attribute`, which should
        be an instance of :class:`cubes.model.Attribute`. If there is no
        dimension specified in attribute, then fact table is assumed. The
        returned object is a MongoDocumentField object.
        """

        reference = None
        dimension = attribute.dimension

        # Try to get mapping if exists
        if self.cube.mappings:
            logical = self.logical(attribute, locale)

            # TODO: should default to non-localized reference if no mapping 
            # was found?
            mapped_ref = self.cube.mappings.get(logical)

            if mapped_ref:
                reference = coalesce_physical(mapped_ref)

        # No mappings exist or no mapping was found - we are going to create
        # default physical reference
        if not reference:
            column_name = attribute.name

            if locale:
                column_name += "_" + locale

            reference = MongoDocumentField(column)

        return reference
