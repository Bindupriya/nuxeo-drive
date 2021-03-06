
from nxdrive.tests.common_unit_test import UnitTestCase


class TestEncoding(UnitTestCase):

    def setUp(self):
        super(TestEncoding, self).setUp()
        self.engine_1.start()
        self.wait_sync()
        # Bind the server and root workspace
        self.remote_client = self.remote_document_client_1
        self.local_client = self.local_client_1

    def test_filename_with_accents_from_server(self):
        self.remote_client.make_file(self.workspace,
            u'Nom sans accents.doc',
            u"Contenu sans accents.")
        self.remote_client.make_file(self.workspace,
            u'Nom avec accents \xe9 \xe8.doc',
            u"Contenu sans accents.")

        self.wait_sync(wait_for_async=True)

        self.assertEquals(self.local_client.get_content(
            u'/Nom sans accents.doc'),
            u"Contenu sans accents.")
        self.assertEquals(self.local_client.get_content(
            u'/Nom avec accents \xe9 \xe8.doc'),
            u"Contenu sans accents.")

    def test_filename_with_katakana_from_server(self):
        self.remote_client.make_file(self.workspace,
            u'Nom sans \u30bc\u30ec accents.doc',
            u"Contenu")
        self.local_client.make_file('/',
            u'Avec accents \u30d7 \u793e.doc',
            u"Contenu")

        self.wait_sync(wait_for_async=True)

        self.assertEquals(self.local_client.get_content(
            u'/Nom sans \u30bc\u30ec accents.doc'),
            u"Contenu")
        self.assertEquals(self.local_client.get_content(
            u'/Avec accents \u30d7 \u793e.doc'),
            u"Contenu")

    def test_content_with_accents_from_server(self):
        self.remote_client.make_file(self.workspace,
            u'Nom sans accents.txt',
            u"Contenu avec caract\xe8res accentu\xe9s.".encode('utf-8'))
        self.wait_sync(wait_for_async=True)
        self.assertEquals(self.local_client.get_content(
            u'/Nom sans accents.txt'),
            u"Contenu avec caract\xe8res accentu\xe9s.".encode('utf-8'))

    def test_filename_with_accents_from_client(self):
        self.local_client.make_file('/',
            u'Avec accents \xe9 \xe8.doc',
            u"Contenu sans accents.")
        self.local_client.make_file('/',
            u'Sans accents.doc',
            u"Contenu sans accents.")
        self.wait_sync(wait_for_async=True)
        self.assertEquals(self.remote_client.get_content(
            u'/Avec accents \xe9 \xe8.doc'),
            u"Contenu sans accents.")
        self.assertEquals(self.remote_client.get_content(
            u'/Sans accents.doc'),
            u"Contenu sans accents.")

    def test_content_with_accents_from_client(self):
        self.local_client.make_file('/',
            u'Nom sans accents',
            u"Contenu avec caract\xe8res accentu\xe9s.".encode('utf-8'))
        self.wait_sync(wait_for_async=True)
        self.assertEquals(self.remote_client.get_content(
            u'/Nom sans accents'),
            u"Contenu avec caract\xe8res accentu\xe9s.".encode('utf-8'))

    def test_name_normalization(self):
        self.local_client.make_file('/',
            u'espace\xa0 et TM\u2122.doc')
        self.wait_sync(wait_for_async=True)
        self.assertEquals(self.remote_client.get_info(
            u'/espace\xa0 et TM\u2122.doc').name,
            u'espace\xa0 et TM\u2122.doc')
