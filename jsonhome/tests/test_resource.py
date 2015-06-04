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


class ResourceTests(base.TestCase):

    def setUp(self):
        super(ResourceTests, self).setUp()
        self.res = jsonhome.Resource()

    def assertResource(self, data):
        self.assertEqual(data, self.res)

    def test_allow(self):
        self.res.allow.extend(['GET', 'PATCH'])
        self.res.allow.append('POST')

        self.assertEqual(['GET', 'PATCH', 'POST'], self.res.allow)
        self.assertResource({'hints': {'allow': ['GET', 'PATCH', 'POST']}})

    def test_allow_methods(self):
        self.res.allow_get = True
        self.assertTrue(self.res.allow_get)
        self.assertFalse(self.res.allow_post)
        self.assertEqual(['GET'], self.res.allow)

        self.res.allow_post = True
        self.assertTrue(self.res.allow_post)
        self.assertEqual(['GET', 'POST'], self.res.allow)

        self.res.allow_get = False
        self.assertFalse(self.res.allow_get)
        self.assertEqual(['POST'], self.res.allow)

    def test_docs(self):
        self.res.docs = 'doc-location'

        self.assertEqual('doc-location', self.res.docs)
        self.assertResource({'hints': {'docs': 'doc-location'}})

    def test_accept_patch(self):
        f = 'application/json-patch'
        self.res.accept_patch.append(f)

        self.assertEqual([f], self.res.accept_patch)
        self.assertResource({'hints': {'accept-patch': [f]}})

    def test_accept_post(self):
        f = 'application/json'
        self.res.accept_post.append(f)

        self.assertEqual([f], self.res.accept_post)
        self.assertResource({'hints': {'accept-post': [f]}})

    def test_accept_ranges(self):
        self.res.accept_ranges.append('bytes')

        self.assertEqual(['bytes'], self.res.accept_ranges)
        self.assertResource({'hints': {'accept-ranges': ['bytes']}})

    def test_accept_prefer(self):
        self.res.accept_prefer.append('preference')

        self.assertEqual(['preference'], self.res.accept_prefer)
        self.assertResource({'hints': {'accept-prefer': ['preference']}})

    def test_href(self):
        self.res.href = 'href-value'

        self.assertEqual('href-value', self.res.href)
        self.assertEqual('href-value', self.res.get_uri())
        self.assertResource({'href': 'href-value'})

    def test_raises_type_error_on_unknown_create(self):
        e = self.assertRaises(TypeError,
                              jsonhome.Resource.create,
                              variablea='foo',
                              variableb='bar')

        s = str(e)

        self.assertIn('variablea', s)
        self.assertIn('variableb', s)

    def test_setting_full_uri(self):
        uri = '/path/to/resource'
        self.res.set_uri(uri)

        self.assertEqual(uri, self.res.href)
        self.assertResource({'href': uri})

    def test_setting_template_uri(self):
        uri = '/path/to/resource{/vara}?param={varb}'
        vara = 'http://url/describes/vara'
        varb = 'http://url/describes/varb'

        self.res.set_uri(uri, vara=vara, varb=varb)

        href_vars = {'vara': vara, 'varb': varb}
        self.assertEqual(uri, self.res.href_template)
        self.assertEqual(href_vars, self.res.href_vars)
        self.assertResource({'href-template': uri, 'href-vars': href_vars})

        self.assertEqual('/path/to/resource/foo?param=',
                         self.res.get_uri(vara='foo'))
        self.assertEqual('/path/to/resource/foo?param=bar',
                         self.res.get_uri(vara='foo', varb='bar'))
        self.assertEqual('/path/to/resource?param=bar',
                         self.res.get_uri(varb='bar'))

    def test_not_enough_template_variables(self):
        self.assertRaises(jsonhome.MissingValues,
                          self.res.set_uri,
                          '/path/to/resource{/vara}?param={varb}',
                          vara='http://url/describes/vara')

    def test_no_href(self):
        self.assertRaises(jsonhome.MissingValues, self.res.get_uri)

    def test_create_multiple_href(self):
        self.assertRaises(ValueError,
                          jsonhome.Resource.create,
                          href='href-value',
                          href_template='href-template')

        self.assertRaises(ValueError,
                          jsonhome.Resource.create,
                          href='href-value',
                          uri='uri-value')

        self.assertRaises(ValueError,
                          jsonhome.Resource.create,
                          uri='uri-value',
                          href_template='href-template')
