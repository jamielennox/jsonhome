===============================
jsonhome
===============================

Helpers for handling jsonhome documents

* Free software: Apache license
* Documentation: https://readthedocs.org/projects/jsonhome
* Source: https://github.com/jamielennox/jsonhome
* Bugs: http://bugs.launchpad.net/python-jsonhome

Introduction
------------

The jsonhome library provides a simple way to build and consume compliant json-home documents.

Building
--------

To build a jsonhome document you create a document and then add resources::

    >>> import jsonhome

    >>> doc = jsonhome.Document()

    >>> doc.create_resource('http://mysite.com/rel/widgets',
    ...                     uri='/widgets{/widget_id}'
    ...                     uri_vars={'widget_id': 'http://mysite.com/param/widget'},
    ...                     allow_get=True,
    ...                     accept_post=['application/json'])

    >>> print(doc.to_json())
    {
        "resources": {
            "http://mysite.com/rel/widgets": {
                "href-template": "/widgets{/widget_id}",
                "href-vars": {
                    "widget_id": "http://mysite.com/param/widget"
                },
                "hints": {
                    "accept-post": [
                        "application/json"
                    ],
                    "allow": [
                        "GET",
                        "POST"
                    ]
                }
            }
        }
    }

Additional parameters to creating resources can be found on the module documentation.

Consuming
---------

To consume a json-home document you load it and then fetch the URIs you need::

    >>> doc = jsonhome.Document.from_json(data)

    >>> print(doc.get_uri('http://mysite.com/rel/widgets', widget_id='1234')
    '/widgets/1234'

Or for specific information you can find helpers on the resource::

    >>> print(doc['http://mysite.com/rel/widgets'].href_vars)
    {"widget_id": "http://mysite.com/param/widget"}
