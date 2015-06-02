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


def _accept_prop(name, doc=None):

    def _accept_getter(self):
        return self.hints.setdefault('accept-%s' % name, [])

    return property(_accept_getter, doc=doc)


def _available(kwargs, *args):
    """Return available keyword arguments for requested keys"""

    for method in args:
        value = kwargs.pop(method, None)
        if value is not None:
            yield method, value


class Resource(dict):
    """One resource that exists within a JSON home document."""

    @property
    def href_vars(self):
        return self.setdefault('href-vars', {})

    @property
    def href_template(self):
        return self.get('href-template')

    @href_template.setter
    def href_template(self, value):
        self['href-template'] = value

    @property
    def href(self):
        """A Direct URI Link to a resource."""
        return self.get('href')

    @href.setter
    def href(self, value):
        self['href'] = value

    @property
    def hints(self):
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
        return self.setdefault('hints', {})

    @property
    def allow(self):
        """HTTP Allow Methods for this resource.

        Hints the HTTP methods that the current client will be able to use to
        interact with the resource; equivalent to the Allow HTTP response
        header.
        """
        return self.hints.setdefault('allow', [])

    allow_delete = _allow_prop('DELETE')
    allow_get = _allow_prop('GET')
    allow_head = _allow_prop('HEAD')
    allow_options = _allow_prop('OPTIONS')
    allow_patch = _allow_prop('PATCH')
    allow_post = _allow_prop('POST')
    allow_put = _allow_prop('PUT')

    accept_patch = _accept_prop('patch')
    accept_post = _accept_prop('post')
    accept_prefer = _accept_prop('prefer')
    accept_ranges = _accept_prop('ranges')

    @property
    def docs(self):
        """The location for human-readable documentation for the resource."""
        return self.hints.get('docs')

    @docs.setter
    def docs(self, value):
        self.hints['docs'] = value

    def get_uri(self, **kwargs):
        if self.href:
            return self.href

        if self.href_template:
            return uritemplate.expand(self.href_template, **kwargs)

        raise MissingValues("Couldn't determine href from values in Resource")

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

    @classmethod
    def create(cls, **kwargs):
        """Create a new resource with specified values.

        A factory function that allows you to create a new Resource object with
        a number of attributes in one method.

        :param str href: A direct URI link to a resource.
        :param str href_template: A template from which a URI is determined.
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
        # Document.create_resource function below for better documentation.

        # before we start handle some SHOULD aspects of the specification to
        # try and make the resources as consistent with the spec as possible.
        if kwargs.get('accept_patch'):
            kwargs.setdefault('allow_patch', True)
        if kwargs.get('accept_post'):
            kwargs.setdefault('allow_post', True)

        r = cls()

        for method, value in _available(kwargs,
                                        'href',
                                        'href_template',
                                        'docs',
                                        'allow_delete',
                                        'allow_get',
                                        'allow_head',
                                        'allow_options',
                                        'allow_patch',
                                        'allow_post',
                                        'allow_put'):
            setattr(r, method, value)

        for method, value in _available(kwargs,
                                        'accept_patch',
                                        'accept_post',
                                        'accept_prefer',
                                        'accept_ranges'):
            getattr(r, method).extend(value)

        if kwargs:
            msg = 'create got an unexpected argument: %s' % ', '.join(kwargs)
            raise TypeError(msg)

        return r


class Document(dict):
    """A model of a JSON Home document that can be manipulated."""

    def __setitem__(self, relation, value):
        if relation in self:
            raise ResourceAlreadyExists(relation)

        super(Document, self).__setitem__(relation, value)

    def get_uri(self, relation, **kwargs):
        try:
            res = self[relation]
        except KeyError:
            raise UnknownResource(relation)

        return res.get_uri(**kwargs)

    def create_resource(self, relation, **kwargs):
        """Create a new resource on this document.

        Create a new resource with prefilled attributes and add it to the
        current document.

        :param str relation: The string relationship to this resource that will
            be used to identity resources.

        :param str href: A direct URI link to a resource.
        :param str href_template: A template from which a URI is determined.
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
        r = Resource.create(**kwargs)
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
        return cls(dict((relation, Resource(d))
                        for relation, d in data['resources'].items()))

    def to_json(self):
        """Convert the Document into JSON format.

        Serialize the json-home document into valid JSON so that it can be sent
        to users.

        :rtype: str
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data):
        """Create a JSON home document from a JSON string.

        Take a string that was received from a remote service and load the JSON
        home document that describes its resources.

        :rtype: :py:class:`~jsonhome.Document`
        """
        return cls.from_dict(json.loads(data))
