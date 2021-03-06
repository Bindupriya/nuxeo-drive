'''
@author: Remi Cattiau
'''
import sys
from nxdrive.tests.common_unit_test import UnitTestCase
from nxdrive.client import LocalClient
from nxdrive.logging_config import get_logger
log = get_logger(__name__)


class TestWatchers(UnitTestCase):

    def test_local_scan(self):
        files, folders = self.make_local_tree()
        self.queue_manager_1.suspend()
        self.queue_manager_1._disable = True
        self.engine_1.start()
        self.wait_remote_scan()
        metrics = self.queue_manager_1.get_metrics()

        # Workspace should have been reconcile
        self.assertEquals(metrics["total_queue"], 7)
        self.assertEquals(metrics["local_folder_queue"], 5)
        self.assertEquals(metrics["local_file_queue"], 2)
        res = self.engine_1.get_dao().get_states_from_partial_local('/')
        # With root
        self.assertEquals(len(res), folders + files + 1)

    def test_reconcile_scan(self):
        files, folders = self.make_local_tree()
        self.make_server_tree()
        self.queue_manager_1.suspend()
        self.queue_manager_1._disable = True
        self.engine_1.start()
        self.wait_remote_scan()
        # Remote as one more file
        self.assertEquals(self.engine_1.get_dao().get_sync_count(), folders + files + 1)
        # Verify it has been reconcile and all items in queue are sync
        queue = self.get_full_queue(self.queue_manager_1.get_local_file_queue())
        for item in queue:
            self.assertEqual(item.pair_state, "synchronized")
        queue = self.get_full_queue(self.queue_manager_1.get_local_folder_queue())
        for item in queue:
            self.assertEqual(item.pair_state, "synchronized")

    def test_remote_scan(self):
        files, folders = self.make_server_tree()
        # Add the workspace folder
        folders = folders + 1
        self.queue_manager_1.suspend()
        self.queue_manager_1._disable = True
        self.engine_1.start()
        self.wait_remote_scan()
        metrics = self.queue_manager_1.get_metrics()
        self.assertEquals(metrics["total_queue"], 1)
        self.assertEquals(metrics["remote_folder_queue"], 1)
        self.assertEquals(metrics["remote_file_queue"], 0)
        self.assertEquals(metrics["local_file_queue"], 0)
        self.assertEquals(metrics["local_folder_queue"], 0)
        res = self.engine_1.get_dao().get_states_from_partial_local('/')
        # With root
        self.assertEquals(len(res), folders + files + 1)

    def test_local_watchdog_creation(self):
        # Test the creation after first local scan
        self.queue_manager_1.suspend()
        self.queue_manager_1._disable = True
        self.engine_1.start()
        self.wait_remote_scan()
        metrics = self.queue_manager_1.get_metrics()
        self.assertEquals(metrics["local_folder_queue"], 0)
        self.assertEquals(metrics["local_file_queue"], 0)
        files, folders = self.make_local_tree()
        self.wait_sync(timeout=3, fail_if_timeout=False)
        metrics = self.queue_manager_1.get_metrics()
        self.assertEquals(metrics["local_folder_queue"], 2)
        self.assertEquals(metrics["local_file_queue"], 1)
        res = self.engine_1.get_dao().get_states_from_partial_local('/')
        # With root
        self.assertEquals(len(res), folders + files + 1)

    def _delete_folder_1(self):
        path = '/Folder 1'
        self.local_client_1.delete_final(path)
        if sys.platform == 'win32':
            from time import sleep
            from nxdrive.engine.watcher.local_watcher import WIN_MOVE_RESOLUTION_PERIOD
            sleep(WIN_MOVE_RESOLUTION_PERIOD / 1000 + 1)
        self.wait_sync(timeout=1, fail_if_timeout=False)
        return '/' + self.workspace_title + path + '/'

    def test_local_watchdog_delete_non_synced(self):
        # Test the deletion after first local scan
        self.test_local_scan()
        path = self._delete_folder_1()
        children = self.engine_1.get_dao().get_states_from_partial_local(path)
        self.assertEquals(len(children), 0)

    def test_local_scan_delete_non_synced(self):
        # Test the deletion after first local scan
        self.test_local_scan()
        self.engine_1.stop()
        path = self._delete_folder_1()
        self.engine_1.start()
        self.wait_sync(timeout=5, fail_if_timeout=False)
        children = self.engine_1.get_dao().get_states_from_partial_local(path)
        self.assertEquals(len(children), 0)

    def test_local_watchdog_delete_synced(self):
        # Test the deletion after first local scan
        self.test_reconcile_scan()
        path = self._delete_folder_1()
        child = self.engine_1.get_dao().get_state_from_local(path[:-1])
        self.assertEqual(child.pair_state, 'locally_deleted')
        children = self.engine_1.get_dao().get_states_from_partial_local(path)
        self.assertEqual(len(children), 5)
        for child in children:
            self.assertEqual(child.pair_state, 'parent_locally_deleted')

    def test_local_scan_delete_synced(self):
        # Test the deletion after first local scan
        self.test_reconcile_scan()
        self.engine_1.stop()
        path = self._delete_folder_1()
        self.engine_1.start()
        self.wait_sync(timeout=5, fail_if_timeout=False)
        child = self.engine_1.get_dao().get_state_from_local(path[:-1])
        self.assertEqual(child.pair_state, 'locally_deleted')
        children = self.engine_1.get_dao().get_states_from_partial_local(path)
        self.assertEqual(len(children), 5)
        for child in children:
            self.assertEqual(child.pair_state, 'parent_locally_deleted')

    def test_local_scan_error(self):
        local = self.local_client_1
        remote = self.remote_document_client_1
        # Synchronize test workspace
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        # Create a local file and use an invalid digest function in local watcher file system client to trigger an error
        # during local scan
        local.make_file('/', u'Test file.odt', 'Content')

        def get_local_client():
            return LocalClient(self.local_nxdrive_folder_1, digest_func='invalid')

        original_getter = self.engine_1.get_local_client
        self.engine_1.get_local_client = get_local_client
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        self.assertFalse(remote.exists(u'/Test file.odt'))

        # Set back original local watcher file system client, launch local scan and check upstream synchronization
        self.engine_1.get_local_client = original_getter
        self.engine_1.start()
        self.wait_sync()
        self.assertTrue(remote.exists(u'/Test file.odt'))

    def test_local_scan_encoding(self):
        local = self.local_client_1
        remote = self.remote_document_client_1
        # Synchronize test workspace
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        # Create files with Unicode combining accents, Unicode latin characters and no special characters
        local.make_file(u'/', u'Accentue\u0301.odt', u'Content')
        local.make_folder(u'/', u'P\xf4le applicatif')
        local.make_file(u'/P\xf4le applicatif', u'e\u0302tre ou ne pas \xeatre.odt', u'Content')
        local.make_file(u'/', u'No special character.odt', u'Content')
        # Launch local scan and check upstream synchronization
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        self.assertTrue(remote.exists(u'/Accentue\u0301.odt'))
        self.assertTrue(remote.exists(u'/P\xf4le applicatif'))
        self.assertTrue(remote.exists(u'/P\xf4le applicatif/e\u0302tre ou ne pas \xeatre.odt'))
        self.assertTrue(remote.exists(u'/No special character.odt'))

        # Check rename using normalized names as previous local scan has normalized them on the file system
        local.rename(u'/Accentu\xe9.odt', u'Accentue\u0301 avec un e\u0302 et un \xe9.odt')
        local.rename(u'/P\xf4le applicatif', u'P\xf4le applique\u0301')
        # LocalClient.rename calls LocalClient.get_info then the FileInfo constructor which normalizes names
        # on the file system, thus we need to use the normalized name for the parent folder
        local.rename(u'/P\xf4le appliqu\xe9/\xeatre ou ne pas \xeatre.odt', u'avoir et e\u0302tre.odt')
        self.engine_1.start()
        self.wait_sync(wait_for_async=True)
        self.engine_1.stop()
        self.assertEquals(remote.get_info(u'/Accentue\u0301.odt').name, u'Accentu\xe9 avec un \xea et un \xe9.odt')
        self.assertEquals(remote.get_info(u'/P\xf4le applicatif').name, u'P\xf4le appliqu\xe9')
        self.assertEquals(remote.get_info(u'/P\xf4le applicatif/e\u0302tre ou ne pas \xeatre.odt').name,
                          u'avoir et \xeatre.odt')
        # Check content update
        # NXDRIVE-389: Reload the engine to be sure that the pair are all synchronized
        log.debug("Update content of avoir et etre")
        self.engine_1.start()
        self.wait_sync(fail_if_timeout=False)
        self.engine_1.stop()
        local.update_content(u'/Accentu\xe9 avec un \xea et un \xe9.odt', u'Updated content')
        local.update_content(u'/P\xf4le appliqu\xe9/avoir et \xeatre.odt', u'Updated content')
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        self.assertEquals(remote.get_content(u'/Accentue\u0301.odt'), u'Updated content')
        # NXDRIVE-389: Will be Content and not Updated content
        # it is not consider as synced, so conflict is generated
        self.assertEquals(remote.get_content(u'/P\xf4le applicatif/e\u0302tre ou ne pas \xeatre.odt'),
                          u'Updated content')

        # Check delete
        local.delete_final(u'/Accentu\xe9 avec un \xea et un \xe9.odt')
        local.delete_final(u'/P\xf4le appliqu\xe9/avoir et \xeatre.odt')
        self.engine_1.start()
        self.wait_sync()
        self.engine_1.stop()
        self.assertFalse(remote.exists(u'/Accentue\u0301.odt'))
        self.assertFalse(remote.exists(u'/P\xf4le applicatif/e\u0302tre ou ne pas \xeatre.odt'))

    def test_watchdog_encoding(self):
        local = self.local_client_1
        remote = self.remote_document_client_1
        # Start engine
        self.engine_1.start()
        # Wait for test workspace synchronization
        self.wait_sync()
        # Create files with Unicode combining accents, Unicode latin characters and no special characters
        local.make_file(u'/', u'Accentue\u0301.odt', u'Content')
        local.make_folder(u'/', u'P\xf4le applicatif')
        local.make_folder(u'/', u'Sub folder')
        local.make_file(u'/Sub folder', u'e\u0302tre ou ne pas \xeatre.odt', u'Content')
        local.make_file(u'/', u'No special character.odt', u'Content')
        # Wait for upstream synchronization
        self.wait_sync()
        self.assertTrue(remote.exists(u'/Accentue\u0301.odt'))
        self.assertTrue(remote.exists(u'/P\xf4le applicatif'))
        self.assertTrue(remote.exists(u'/Sub folder'))
        self.assertTrue(remote.exists(u'/Sub folder/e\u0302tre ou ne pas \xeatre.odt'))
        self.assertTrue(remote.exists(u'/No special character.odt'))

        # Check rename using normalized names as previous watchdog handling has normalized them on the file system
        local.rename(u'/Accentu\xe9.odt', u'Accentue\u0301 avec un e\u0302 et un \xe9.odt')
        local.rename(u'/P\xf4le applicatif', u'P\xf4le applique\u0301')
        local.rename(u'/Sub folder/\xeatre ou ne pas \xeatre.odt', u'avoir et e\u0302tre.odt')
        self.wait_sync()
        self.assertEquals(remote.get_info(u'/Accentue\u0301.odt').name, u'Accentu\xe9 avec un \xea et un \xe9.odt')
        self.assertEquals(remote.get_info(u'/P\xf4le applicatif').name, u'P\xf4le appliqu\xe9')
        self.assertEquals(remote.get_info(u'/Sub folder/e\u0302tre ou ne pas \xeatre.odt').name,
                          u'avoir et \xeatre.odt')
        # Check content update
        local.update_content(u'/Accentu\xe9 avec un \xea et un \xe9.odt', u'Updated content')
        local.update_content(u'/Sub folder/avoir et \xeatre.odt', u'Updated content')
        self.wait_sync()
        self.assertEquals(remote.get_content(u'/Accentue\u0301.odt'), u'Updated content')
        self.assertEquals(remote.get_content(u'/Sub folder/e\u0302tre ou ne pas \xeatre.odt'),
                          u'Updated content')

        # Check delete
        local.delete_final(u'/Accentu\xe9 avec un \xea et un \xe9.odt')
        local.delete_final(u'/Sub folder/avoir et \xeatre.odt')
        self.wait_sync()
        self.assertFalse(remote.exists(u'/Accentue\u0301.odt'))
        self.assertFalse(remote.exists(u'/Sub folder/e\u0302tre ou ne pas \xeatre.odt'))
