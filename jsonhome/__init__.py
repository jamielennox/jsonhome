# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import json

import uritemplate


__all__ = ['Document',
           'Resource',

           'MEDIA_TYPE',

           'JsonHomeException',
           'MissingValues',
           'UnknownResource',
           'ResourceAlreadyExists'
           ]


MEDIA_TYPE = 'application/json-home'


class JsonHomeException(Exception):
    """Base Exception class that all JSONHome exceptions inherit from."""


class MissingValues(JsonHomeException):
    """There is not enough information in the JSONHome document to finish."""


class UnknownResource(JsonHomeException):
    """There is no resource available with the specified relation."""


class ResourceAlreadyExists(JsonHomeException):
    """A resource with the specified relation already exists."""


def _allow_prop(method):

    def _allow_getter(self):
        return self.is_allowed(method)

    def _allow_setter(self, value):
        in_list = self.is_allowed(method)

        if value and not in_list:
            self.allow.append(method)
        if in_list and not value:
            self.hints['allow'] = [x for x in self.allow
                                   if x.upper() != method]

    return property(_allow_getter,
                    _allow_setter,
                    doc='Allow the %s method on this resource' % method)


def _item_prop(name, default=None, setdefault=None, hint=False):
    """Create a property that fetches a value from the dictionary.

    We implement getter, setter and deleter here. Whilst we may not want users
    to do all of those things it is not our job to prevent users from doing
    something stupid. Our goal is to provide helper functions and if people go
    and delete hints or force set multiple href methods that's not our fault.

    Note that set
    :param default: A value that is returned if nothing present in the object.
        This value will be ignored if setdefault is set.
    :param callable setdefault: A value set and returned if nothing present in
        the object. This value will take priority to default. Note that this is
        a callable so the set value will be the result of executing this
        function. This allows us to create new objects for default values.
    :param bool hint: True if this attribute exists in the hints dictionary.

    :rtype: property
    """

    def o(self):
        return self.hints if hint else self

    def _getter(self):
        if setdefault:
            return o(self).setdefault(name, setdefault())
        else:
            return o(self).get(name, default)

    def _setter(self, value):
        o(self)[name] = value

    def _deleter(self):
        o(self).pop(name, None)

    return property(_getter, _setter, _deleter)


class Resource(dict):
    """One resource that exists within a JSON home document."""

    href_vars = _item_prop('href-vars', setdefault=dict)
    """A indication for variables in the template to construct a URI."""

    href_template = _item_prop('href-template')
    """A templated URI link to a resource."""

    href = _item_prop('href')
    """A Direct URI Link to a resource."""

    hints = _item_prop('hints', setdefault=dict)
    """Additional hint information defined by the resource.

    Resource hints allow clients to find relevant information about
    interacting with a resource beforehand, as a means of optimising
    communications, as well as advertising available behaviours (e.g., to
    aid in laying out a user interface for consuming the API).

    Hints are just that - they are not a "contract", and are to only be
    taken as advisory.  The runtime behaviour of the resource always
    overrides hinted information.

    For example, a resource might hint that the PUT method is allowed on
    all "widget" resources.  This means that generally, the user has the
    ability to PUT to a particular resource, but a specific resource
    might reject a PUT based upon access control or other considerations.
    More fine-grained information might be gathered by interacting with
    the resource (e.g., via a GET), or by another resource "containing"
    it (such as a "widgets" collection) or describing it (e.g., one
    linked to it with a "describedby" link relation).
    """

    allow = _item_prop('allow', setdefault=list, hint=True)
    """HTTP Allow Methods for this resource.

    Hints the HTTP methods that the current client will be able to use to
    interact with the resource; equivalent to the Allow HTTP response
    header.
    """

    accept_patch = _item_prop('accept-patch', setdefault=list, hint=True)
    """Hints the PATCH request formats accepted by the resource.

    This is equivalent to the Accept-Patch HTTP response header.
    """

    accept_post = _item_prop('accept-post', setdefault=list, hint=True)
    """Hints the POST request formats accepted by the resource."""

    accept_prefer = _item_prop('accept-prefer', setdefault=list, hint=True)
    """Hints the preferences supported by the resource.

    Note that, as per that specifications, a preference can be ignored by the
    server.
    """

    accept_ranges = _item_prop('accept-ranges', setdefault=list, hint=True)
    """Hints the range-specifiers available to the client.

    This is equivalent to the Accept-Ranges HTTP response header.
    """

    docs = _item_prop('docs', hint=True)
    """The location for human-readable documentation for the resource."""

    def is_allowed(self, method):
        """Test if a HTTP method can be used with this resource.

        :param str method: a HTTP method string to find.

        :returns: bool or None if no hints are defined by the resource.
        """
        try:
            allowed = self.hints['allow']
        except KeyError:
            return None
        else:
            return method.upper() in (a.upper() for a in allowed)

    allow_delete = _allow_prop('DELETE')
    allow_get = _allow_prop('GET')
    allow_head = _allow_prop('HEAD')
    allow_options = _allow_prop('OPTIONS')
    allow_patch = _allow_prop('PATCH')
    allow_post = _allow_prop('POST')
    allow_put = _allow_prop('PUT')

    def get_uri(self, **kwargs):
        """Get an absolute URI for this resource.

        Fetch the absolute URI. If there is an absolute URI set on this
        resource that will be returned.

        If there is a templated URI then the variables in the template will be
        evaluated against the values passed in through keyword arguments.
        """
        if self.href:
            return self.href

        if self.href_template:
            return uritemplate.expand(self.href_template, **kwargs)

        raise MissingValues("Couldn't determine href from values in Resource")

    def set_uri(self, uri, **kwargs):
        """Set the URI on this resource based on its format.

        Selective set the href or href-template and href-vars depending on if
        the URI contains a templated form or not. If there are variables set in
        the URI then a relation name be passed as a kwarg as well.

        Passing an absolute URI::

            res.set_uri('/path/to/resource')

        Passing a templated URI::

            res.set_uri('/path/to/resource{/param}',
                        param='http://description/rel/param')

        :param str uri: The URI you want to set. This may contain variables.

        :raises jsonhome.MissingValues: If a templated URI is passed and there
            is not a relation passed as a keyword argument that matches the
            variable.
        """
        variables = uritemplate.URITemplate(uri).variables

        if variables:
            try:
                href_vars = dict((n, kwargs.pop(n))
                                 for v in variables
                                 for n in v.variable_names)
            except KeyError as e:
                msg = "Missing parameter %s from template" % str(e)
                raise MissingValues(msg)

            del self.href
            self.href_template = uri
            self.href_vars = href_vars

        else:
            self.href = uri
            del self.href_template
            del self.href_vars

    @classmethod
    def create(cls, **kwargs):
        """Create a new resource with specified values.

        A factory function that allows you to create a new Resource object with
        a number of attributes in one method.

        :param str href: A direct URI link to a resource.
        :param str href_template: A template from which a URI is determined.
        :param dict href_vars: The raw href variables that should be set.

        :param str uri: A templatable URI, of the form expected by
            :py:meth:`~jsonhome.Resource.set_uri`.
        :param dict uri_vars: The URI variables that are interpolated in the
            form expected by :py:meth:`~jsonhome.Resource.set_uri`.

        :param str docs: location for human-readable documentation.

        :param bool allow_delete: allow the DELETE method on resource.
        :param bool allow_get: allow the GET method on resource.
        :param bool allow_head: allow the HEAD method on resource.
        :param bool allow_options: allow the OPTIONS method on resource.
        :param bool allow_patch: allow the PATCH method on resource.
        :param bool allow_post: allow the POST method on resource.
        :param bool allow_put: allow the PUT method on resource.

        :param accept_patch: Hints the PATCH [RFC5789] request formats accepted
            by the resource for this client; equivalent to the Accept-Patch
            HTTP response header.
        :type accept_patch: list(str)

        :param accept_post: Hints the POST request formats accepted by the
            resource for this client.
        :type accept_post: list(str)

        :param accept_prefer: Hints the preferences supported by the resource.
            Note that, as per that specifications, a preference can be ignored
            by the server.
        :type accept_prefer: list(str)

        :param accept_ranges: Hints the range-specifiers available to the
            client for this resource; equivalent to the Accept-Ranges HTTP
            response header
        :type accept_ranges: list(str)

        :rtype: :py:class:`~jsonhome.Resource`.
        """
        # NOTE(jamielennox): keep the above parameter list in sync with the
        # Document.add_resource function below for better documentation.

        # before we start handle some SHOULD aspects of the specification to
        # try and make the resources as consistent with the spec as possible.
        if kwargs.get('accept_patch'):
            kwargs.setdefault('allow_patch', True)
        if kwargs.get('accept_post'):
            kwargs.setdefault('allow_post', True)

        # ensure that the URI is only handled in one way.
        uri = kwargs.pop('uri', None)
        uri_vars = kwargs.pop('uri_vars', {})

        # NOTE(jamielennox): we purposefully only check uri here, not uri_vars
        # so that you can keep a repository of uri_vars that are passed every
        # time and ignored if no uri parameter is passed.
        if sum([bool(uri),
                bool(kwargs.get('href')),
                bool(kwargs.get('href_template') or
                     kwargs.get('href_vars'))]) > 1:
            m = 'You should choose only one way to set the URI on a resource.'
            raise ValueError(m)

        r = cls()

        if uri:
            r.set_uri(uri, **uri_vars)

        for method in ('href',
                       'href_template',
                       'href_vars',

                       'docs',

                       'allow_delete',
                       'allow_get',
                       'allow_head',
                       'allow_options',
                       'allow_patch',
                       'allow_post',
                       'allow_put',

                       'accept_patch',
                       'accept_post',
                       'accept_prefer',
                       'accept_ranges'):
            value = kwargs.pop(method, None)
            if value is not None:
                setattr(r, method, value)

        if kwargs:
            msg = 'create got an unexpected argument: %s' % ', '.join(kwargs)
            raise TypeError(msg)

        return r


class Document(dict):
    """A model of a JSON Home document that can be manipulated."""

    resource_class = Resource
    """The class of resource that should be created."""

    def __setitem__(self, relation, value):
        if not isinstance(value, self.resource_class):
            raise TypeError('Can only set valid resources on Document')

        if relation in self:
            raise ResourceAlreadyExists(relation)

        super(Document, self).__setitem__(relation, value)

    def get_uri(self, relation, **kwargs):
        """Get an absolute URI for this resource.

        Fetch the absolute URI. If there is an absolute URI set on this
        resource that will be returned.

        If there is a templated URI then the variables in the template will be
        evaluated against the values passed in through keyword arguments.

        :param str relation: The relation to the resource you wish to get the
            URI for.
        """
        try:
            res = self[relation]
        except KeyError:
            raise UnknownResource(relation)

        return res.get_uri(**kwargs)

    def add_resource(self, relation, **kwargs):
        """Create a new resource on this document.

        Create a new resource with prefilled attributes and add it to the
        current document.

        :param str relation: The string relationship to this resource that will
            be used to identity resources.

        :param str href: A direct URI link to a resource.
        :param str href_template: A template from which a URI is determined.
        :param dict href_vars: The raw href variables that should be set.

        :param str uri: A templatable URI, of the form expected by
            :py:meth:`~jsonhome.Resource.set_uri`.
        :param dict uri_vars: The URI variables that are interpolated in the
            form expected by :py:meth:`~jsonhome.Resource.set_uri`.

        :param str docs: location for human-readable documentation.

        :param bool allow_delete: allow the DELETE method on resource.
        :param bool allow_get: allow the GET method on resource.
        :param bool allow_head: allow the HEAD method on resource.
        :param bool allow_options: allow the OPTIONS method on resource.
        :param bool allow_patch: allow the PATCH method on resource.
        :param bool allow_post: allow the POST method on resource.
        :param bool allow_put: allow the PUT method on resource.

        :param accept_patch: Hints the PATCH [RFC5789] request formats accepted
            by the resource for this client; equivalent to the Accept-Patch
            HTTP response header.
        :type accept_patch: list(str)

        :param accept_post: Hints the POST request formats accepted by the
            resource for this client.
        :type accept_post: list(str)

        :param accept_prefer: Hints the preferences supported by the resource.
            Note that, as per that specifications, a preference can be ignored
            by the server.
        :type accept_prefer: list(str)

        :param accept_ranges: Hints the range-specifiers available to the
            client for this resource; equivalent to the Accept-Ranges HTTP
            response header
        :type accept_ranges: list(str)

        :raises jsonhome.ResourceAlreadyExists: If there is already a relation
            with the requested name available on the document.

        :returns: The new resource. This is the same resource that was added to
            the document so a user may perform additional manipulation.
        :rtype: :py:class:`~jsonhome.Resource`.
        """
        r = self.resource_class.create(**kwargs)
        self[relation] = r
        return r

    def to_dict(self):
        """Convert the document into a serializable format.

        Convert the current document into a valid json-home format so that it
        can be serialized into JSON.

        :rtype: dict
        """
        return {'resources': copy.deepcopy(self)}

    @classmethod
    def from_dict(cls, data):
        """Create a json-home document from de-serialized data.

        Convert a dict that may have been received from an external site into
        a json-home document that can be manipulated and queried.

        :param dict data: The data to be converted.

        :rtype: :py:class:`~jsonhome.Document`
        """
        return cls(dict((relation, cls.resource_class(d))
                        for relation, d in data['resources'].items()))

    def to_json(self, **kwargs):
        """Convert the Document into JSON format.

        Serialize the json-home document into valid JSON so that it can be sent
        to users.

        :rtype: str
        """
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, data):
        """Create a JSON home document from a JSON string.

        Take a string that was received from a remote service and load the JSON
        home document that describes its resources.

        :rtype: :py:class:`~jsonhome.Document`
        """
        return cls.from_dict(json.loads(data))
