import os
import time

from nxdrive.tests.common import IntegrationTestCase
from nxdrive.client import LocalClient
from nxdrive.model import LastKnownState


class TestIntegrationRemoteDeletion(IntegrationTestCase):

    def test_synchronize_remote_deletion(self):
        """Test that deleting remote root document while uploading is handled

        SUPNXP-10436
        See TestIntegrationSecurityUpdates.test_synchronize_denying_read_access
        as the same uses cases are tested
        """
        # Bind the server and root workspace
        ctl = self.controller_1
        # Override the behavior to force use of trash
        ctl.trash_modified_file = lambda: True
        ctl.bind_server(self.local_nxdrive_folder_1, self.nuxeo_url,
                        self.user_1, self.password_1)
        ctl.bind_root(self.local_nxdrive_folder_1, self.workspace)

        # Get local and remote clients
        local = LocalClient(os.path.join(self.local_nxdrive_folder_1,
                                         self.workspace_title))
        remote = self.remote_document_client_1

        syn = ctl.synchronizer
        self._synchronize(syn)
        # Create documents in the remote root workspace
        # then synchronize
        local.make_folder('/', 'Test folder')
        i = 0
        while i < 400:
            local.make_file('/Test folder', ('joe%d.bin' % i), 'Some content')
            i += 1

        self._synchronize(syn)
        # All files should not be synchronized
        self.assertTrue(remote.exists('/Test folder'))
        self.assertTrue(remote.exists('/Test folder/joe0.bin'))
        self.assertFalse(remote.exists('/Test folder/joe399.bin'))

        # Delete remote folder then synchronize
        remote.delete('/Test folder')
        # Error counter should be in place
        self._synchronize(syn)
        self.assertFalse(local.exists('/Test folder'))