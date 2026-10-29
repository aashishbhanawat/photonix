from unittest import TestCase
from photonix.photos.utils.tasks import requeue_stuck_tasks, count_remaining_task

class TasksTestCase(TestCase):
    def test_count_remaining_task(self):
        result = count_remaining_task('any_task')
        self.assertEqual(result, {'remaining': 0})

    def test_requeue_stuck_tasks(self):
        # Currently the function does nothing, just verify it can be called
        # with various arguments.
        result = requeue_stuck_tasks('any_task')
        self.assertIsNone(result)

        result = requeue_stuck_tasks('another_task', age_hours=12, max_num=5)
        self.assertIsNone(result)
