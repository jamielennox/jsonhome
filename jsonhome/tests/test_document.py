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

import jsonhome
from jsonhome.tests import base


class DocumentTests(base.TestCase):

    def setUp(self):
        super(DocumentTests, self).setUp()
        self.doc = jsonhome.Document()

    def assertDocument(self, data):
        self.assertEqual({'resources': data}, self.doc.to_dict())

    def test_create_allow_delete(self):
        r = self.doc.add_resource('relation', allow_delete=True)

        self.assertTrue(r.allow_delete)
        self.assertDocument({'relation': {'hints': {'allow': ['DELETE']}}})

    def test_create_docs(self):
        r = self.doc.add_resource('relation', docs='doc-location')

        self.assertEqual('doc-location', r.docs)
        self.assertDocument({'relation': {'hints': {'docs': 'doc-location'}}})

    def test_accept_patch(self):
        f = 'application/json-patch'
        r = self.doc.add_resource('relation', accept_patch=[f])

        # setting accept_patch also sets the allow_patch flag
        self.assertEqual([f], r.accept_patch)
        self.assertTrue(r.allow_patch)

        self.assertDocument({'relation': {'hints': {'accept-patch': [f],
                                                    'allow': ['PATCH']}}})

    def test_accept_post(self):
        f = 'application/json'
        r = self.doc.add_resource('relation', accept_post=[f])

        # setting accept_post also sets the allow_post flag
        self.assertEqual([f], r.accept_post)
        self.assertTrue(r.allow_post)

        self.assertDocument({'relation': {'hints': {'accept-post': [f],
                                                    'allow': ['POST']}}})

    def test_accept_ranges(self):
        r = self.doc.add_resource('relation', accept_ranges=['bytes'])

        self.assertEqual(['bytes'], r.accept_ranges)
        d = {'relation': {'hints': {'accept-ranges': ['bytes']}}}
        self.assertDocument(d)

    def test_accept_prefer(self):
        r = self.doc.add_resource('relation', accept_prefer=['preference'])

        self.assertEqual(['preference'], r.accept_prefer)
        d = {'relation': {'hints': {'accept-prefer': ['preference']}}}
        self.assertDocument(d)

    def test_href(self):
        r = self.doc.add_resource('relation', href='href-value')

        self.assertEqual('href-value', r.href)
        self.assertEqual('href-value', r.get_uri())
        self.assertEqual('href-value', self.doc.get_uri('relation'))
        self.assertDocument({'relation': {'href': 'href-value'}})

    def test_raises_type_error_on_unknown_create(self):
        e = self.assertRaises(TypeError,
                              self.doc.add_resource,
                              'relation',
                              variablea='foo',
                              variableb='bar')

        s = str(e)

        self.assertIn('variablea', s)
        self.assertIn('variableb', s)

    def test_cant_install_resource_twice(self):
        r = self.doc.add_resource('relation')

        self.assertRaises(jsonhome.ResourceAlreadyExists,
                          self.doc.add_resource,
                          'relation')

        self.assertRaises(jsonhome.ResourceAlreadyExists,
                          self.doc.__setitem__,
                          'relation',
                          r)

    def test_simple_document_equality(self):
        d1 = jsonhome.Document()
        d1.add_resource('relation', allow_delete=True)

        d2 = jsonhome.Document()
        d2.add_resource('relation', allow_delete=True)

        self.assertEqual(d1, d2)

    def test_equality_len_difference(self):
        d1 = jsonhome.Document()
        d1.add_resource('relation', allow_delete=True)
        d1.add_resource('another', allow_delete=True)

        d2 = jsonhome.Document()
        d2.add_resource('relation', allow_delete=True)

        self.assertNotEqual(d1, d2)

    def test_equality_relation_difference(self):
        d1 = jsonhome.Document()
        d1.add_resource('relation', allow_delete=True)
        d1.add_resource('foo', allow_delete=True)

        d2 = jsonhome.Document()
        d2.add_resource('relation', allow_delete=True)
        d2.add_resource('bar', allow_delete=True)

        self.assertNotEqual(d1, d2)

    def test_equality_resource_difference(self):
        d1 = jsonhome.Document()
        d1.add_resource('relation', allow_delete=True)
        d1.add_resource('another', allow_delete=True)

        d2 = jsonhome.Document()
        d2.add_resource('relation', allow_delete=True)
        d2.add_resource('another', allow_delete=False)

        self.assertNotEqual(d1, d2)

    def test_from_dict(self):
        x1 = {'resources': {'relation': {'hints': {'allow': ['DELETE']}}}}
        d = jsonhome.Document.from_dict(x1)

        self.assertTrue(d['relation'].allow_delete)

        x2 = d.to_dict()
        self.assertEqual(x1, x2)

    def test_from_json(self):
        x1 = '{"resources": {"relation": {"hints": {"allow": ["DELETE"]}}}}'
        d = jsonhome.Document.from_json(x1)

        self.assertTrue(d['relation'].allow_delete)

        x2 = d.to_json()
        self.assertEqual(x1, x2)

    def test_create_with_absolute_uri(self):
        r = self.doc.add_resource('relation', uri='href-value')
        self.assertEqual('href-value', r.href)
        self.assertIsNone(r.href_template)
        self.assertDocument({'relation': {'href': 'href-value'}})

    def test_create_with_template_uri(self):
        r = self.doc.add_resource('relation',
                                  uri='/path{/param}',
                                  uri_vars={'param': 'foo'})

        self.assertIsNone(r.href)
        self.assertEqual('/path{/param}', r.href_template)
        self.assertEqual({'param': 'foo'}, r.href_vars)

        self.assertEqual('/path/val',
                         self.doc.get_uri('relation', param='val'))

        self.assertDocument({'relation': {'href-template': '/path{/param}',
                                          'href-vars': {'param': 'foo'}}})

    def test_create_not_enough_variables(self):
        self.assertRaises(jsonhome.MissingValues,
                          self.doc.add_resource,
                          'relation',
                          uri='/path{/param}')

    def test_ignore_extra_uri_vars(self):
        self.doc.add_resource('relation',
                              uri='/path{/param}',
                              uri_vars={'param': 'foo',
                                        'extra': 'vals',
                                        'are': 'ignored'})

        self.assertDocument({'relation': {'href-template': '/path{/param}',
                                          'href-vars': {'param': 'foo'}}})

    def test_ignore_unused_uri_vars(self):
        self.doc.add_resource('relation',
                              href='href-value',
                              uri_vars={'param': 'foo',
                                        'extra': 'vals',
                                        'are': 'ignored'})

        self.assertDocument({'relation': {'href': 'href-value'}})

    def test_unknown_resource(self):
        self.assertRaises(jsonhome.UnknownResource,
                          self.doc.get_uri,
                          'unknown',
                          key='val')

    def test_cant_set_invalid_resource_type(self):
        def _f(k, v):
            """Function is just rather that using __setitem__ directly."""
            self.doc[k] = v

        self.assertRaises(TypeError, _f, 'relation', 'somestring')
        self.assertRaises(TypeError, _f, 'relation', 42)
        self.assertRaises(TypeError, _f, 'relation', ['list', 'of', 'stuff'])
