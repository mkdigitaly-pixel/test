import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish as pub


class LongTelegramPostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cover = self.root / "cover.jpg"
        self.cover.write_bytes(b"reviewed image")
        self.text = "Полный самостоятельный пост. " * 80
        self.queue_patch = patch.object(pub, "POSTS_QUEUE_FILE", self.root / "posts.yaml")
        self.queue_patch.start()
        pub.save_posts_queue([{"id": "one", "status": "approved"}])

    def tearDown(self):
        self.queue_patch.stop()
        self.temp.cleanup()

    def run_post(self, text=None, dry_run=False):
        return pub.publish_long_standalone_tg("one", text or self.text, "channel", "test", self.cover, dry_run=dry_run)

    def test_both_receipts_saved_and_completed_send_is_not_repeated(self):
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "photo", 100)) as photo, patch.object(pub, "telegram_api", return_value={"result": {"message_id": 101}}) as api:
            self.assertEqual(self.run_post().message_id, 101)
            self.assertEqual(self.run_post().message_id, 101)
            photo.assert_called_once()
            api.assert_called_once()
            self.assertEqual(api.call_args.args[1]["reply_parameters"], {"message_id": 100})
        item = pub.load_posts_queue()[0]
        self.assertEqual(item["tg_cover_message_id"], 100)
        self.assertEqual(item["tg_text_message_id"], 101)

    def test_explicit_text_rejection_resumes_without_duplicate_cover(self):
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "photo", 100)), patch.object(pub, "telegram_api", side_effect=pub.TelegramRejectedError("text rejected")):
            with self.assertRaises(pub.TelegramRejectedError):
                self.run_post()
        with patch.object(pub, "publish_telegram") as photo, patch.object(pub, "telegram_api", return_value={"result": {"message_id": 101}}):
            self.assertEqual(self.run_post().message_id, 101)
            photo.assert_not_called()

    def test_unknown_text_result_blocks_retry_until_channel_is_checked(self):
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "photo", 100)), patch.object(pub, "telegram_api", side_effect=pub.requests.Timeout("timeout")):
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
        self.assertEqual(pub.load_posts_queue()[0]["tg_text_send_state"], "unknown")
        with patch.object(pub, "publish_telegram") as photo, patch.object(pub, "telegram_api") as api:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            photo.assert_not_called()
            api.assert_not_called()

    def test_unknown_cover_result_blocks_retry(self):
        with patch.object(pub, "publish_telegram", side_effect=pub.requests.Timeout("timeout")), patch.object(pub, "telegram_api") as api:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            api.assert_not_called()
        with patch.object(pub, "publish_telegram") as photo:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            photo.assert_not_called()

    def test_changed_text_after_cover_requires_review(self):
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "photo", 100)), patch.object(pub, "telegram_api", side_effect=pub.TelegramRejectedError("rejected")):
            with self.assertRaises(pub.TelegramRejectedError):
                self.run_post()
        with patch.object(pub, "telegram_api") as api:
            with self.assertRaisesRegex(RuntimeError, "изменён"):
                self.run_post(self.text + " changed")
            api.assert_not_called()

    def test_dry_run_has_no_network_or_queue_changes(self):
        before = pub.POSTS_QUEUE_FILE.read_bytes()
        with patch.object(pub.requests, "post") as request:
            self.assertTrue(self.run_post(dry_run=True).ok)
            request.assert_not_called()
        self.assertEqual(pub.POSTS_QUEUE_FILE.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
