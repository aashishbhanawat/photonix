
import os
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse
from photonix.accounts.models import User
from photonix.photos.models import Library, LibraryPath
from django.core.files.uploadedfile import SimpleUploadedFile

class SecurityUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.library = Library.objects.create(name='Test Library')
        self.library.users.create(user=self.user, owner=True)
        # Use a temporary directory for the library path to avoid messing with real data
        self.lib_dir = Path('/tmp/photonix_test_lib')
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        self.lib_path = LibraryPath.objects.create(
            library=self.library,
            type='St',
            backend_type='Lo',
            path=str(self.lib_dir)
        )

    def tearDown(self):
        # Cleanup
        import shutil
        if self.lib_dir.exists():
            shutil.rmtree(self.lib_dir, ignore_errors=True)
        traversal_file = Path('/tmp/traversal.txt')
        if traversal_file.exists():
            traversal_file.unlink()

    def test_upload_path_traversal(self):
        # The vulnerable code uses the form field KEY as the filename:
        # for fn, file in request.FILES.items():
        #     dest = Path(libpath.path) / fn

        malicious_fn = '../traversal.txt'
        file_content = b'this is a traversal test'
        # We put the malicious path as the KEY in the post data
        uploaded_file = SimpleUploadedFile('ignored_name.jpg', file_content)

        url = reverse('upload') + f'?library_id={self.library.id}'
        response = self.client.post(url, {malicious_fn: uploaded_file})

        self.assertEqual(response.status_code, 200)

        traversal_file_path = Path('/tmp/traversal.txt')

        # If vulnerable, this file will exist
        is_vulnerable = traversal_file_path.exists()

        if is_vulnerable:
            # Clean up if it was created
            traversal_file_path.unlink()
            self.fail("Vulnerability confirmed: File created outside library path via traversal!")
        else:
            # If fixed, the file should either not exist or be created safely within the library path
            # as 'traversal.txt' (because Path('../traversal.txt').name is 'traversal.txt')
            safe_file_path = self.lib_dir / 'traversal.txt'
            # We don't necessarily need to assert it exists, as long as it didn't go to /tmp/traversal.txt
            pass
