import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish as pub


class SingleTelegramPostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cover = self.root / "cover.jpg"
        self.cover.write_bytes(b"reviewed image")
        self.text = "<b>Полный пост</b>\n\n" + "Объяснение и пример. " * 100 + "\n\nИтоговый вопрос?"
        self.queue_patch = patch.object(pub, "POSTS_QUEUE_FILE", self.root / "posts.yaml")
        self.queue_patch.start()
        pub.save_posts_queue([{"id": "one", "status": "approved"}])

    def tearDown(self):
        self.queue_patch.stop()
        self.temp.cleanup()

    def run_post(self, text=None, dry_run=False):
        return pub.publish_long_standalone_tg("one", self.text if text is None else text, "channel", "test", self.cover, dry_run=dry_run)

    def response(self, message_id=101):
        response = Mock()
        response.json.return_value = {"ok": True, "result": {"message_id": message_id}}
        return response

    def test_one_receipt_and_no_duplicate_after_confirmed_delivery(self):
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "one post", 100)) as send:
            self.assertEqual(self.run_post().message_id, 100)
            self.assertEqual(self.run_post().message_id, 100)
            send.assert_called_once()
            self.assertEqual(send.call_args.args[0], self.text)
        item = pub.load_posts_queue()[0]
        self.assertEqual(item["tg_post_message_id"], 100)
        self.assertEqual(item["tg_post_send_state"], "confirmed")
        self.assertEqual(item["tg_delivery_format"], "single_message")
        self.assertNotIn("tg_cover_message_id", item)
        self.assertNotIn("tg_text_message_id", item)

    def test_long_post_uploads_photo_and_all_text_in_one_request(self):
        with patch.object(pub.requests, "post", return_value=self.response()) as request, patch.object(pub, "telegram_api") as api:
            self.assertEqual(self.run_post().message_id, 101)
            request.assert_called_once()
            api.assert_not_called()
        call = request.call_args
        self.assertTrue(call.args[0].endswith("/sendRichMessage"))
        payload = call.kwargs["data"]
        rich = json.loads(payload["rich_message"])
        self.assertEqual(rich["media"], [{"id": "cover", "media": {"type": "photo", "media": "attach://cover"}}])
        self.assertEqual(set(call.kwargs["files"]), {"cover"})
        self.assertIn('<img src="tg://photo?id=cover"/>', rich["html"])
        for paragraph in self.text.split("\n\n"):
            self.assertIn("<p>" + paragraph + "</p>", rich["html"])
        self.assertNotIn("reply_parameters", payload)

    def test_short_post_keeps_photo_and_caption_in_one_request(self):
        with patch.object(pub.requests, "post", return_value=self.response(102)) as request:
            self.assertEqual(self.run_post("Короткий пост").message_id, 102)
        request.assert_called_once()
        self.assertTrue(request.call_args.args[0].endswith("/sendPhoto"))
        self.assertEqual(request.call_args.kwargs["data"]["caption"], "Короткий пост")

    def test_rich_format_preserves_text_longer_than_plain_message_limit(self):
        text = "Полный текст. " * 400
        self.assertGreater(len(text), pub.TG_MESSAGE_LIMIT)
        with patch.object(pub.requests, "post", return_value=self.response(103)) as request:
            self.assertEqual(self.run_post(text).message_id, 103)
        rich = json.loads(request.call_args.kwargs["data"]["rich_message"])
        self.assertIn(text.strip(), rich["html"])

    def test_explicit_rejection_can_retry_without_split_fallback(self):
        with patch.object(pub, "publish_telegram", side_effect=pub.TelegramRejectedError("rejected")) as send:
            with self.assertRaises(pub.TelegramRejectedError):
                self.run_post()
            send.assert_called_once()
        self.assertEqual(pub.load_posts_queue()[0]["tg_post_send_state"], "rejected")
        with patch.object(pub, "publish_telegram", return_value=pub.PublishResult("telegram", True, "one post", 104)) as send:
            self.assertEqual(self.run_post().message_id, 104)
            send.assert_called_once()

    def test_unknown_result_blocks_retry_until_channel_is_checked(self):
        with patch.object(pub, "publish_telegram", side_effect=pub.requests.Timeout("timeout")):
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
        self.assertEqual(pub.load_posts_queue()[0]["tg_post_send_state"], "unknown")
        with patch.object(pub, "publish_telegram") as send:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            send.assert_not_called()

    def test_inflight_after_process_interruption_blocks_retry(self):
        pub.save_posts_queue([{"id": "one", "status": "approved", "tg_post_send_state": "inflight"}])
        with patch.object(pub, "publish_telegram") as send:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            send.assert_not_called()

    def test_changed_text_after_started_delivery_requires_review(self):
        with patch.object(pub, "publish_telegram", side_effect=pub.TelegramRejectedError("rejected")):
            with self.assertRaises(pub.TelegramRejectedError):
                self.run_post()
        with patch.object(pub, "publish_telegram") as send:
            with self.assertRaisesRegex(RuntimeError, "изменён"):
                self.run_post(self.text + " changed")
            send.assert_not_called()

    def test_partial_legacy_delivery_is_not_restarted_in_new_format(self):
        pub.save_posts_queue([{"id": "one", "status": "approved", "tg_cover_message_id": 90, "tg_cover_send_state": "confirmed"}])
        with patch.object(pub, "publish_telegram") as send:
            with self.assertRaisesRegex(RuntimeError, "сначала проверьте канал"):
                self.run_post()
            send.assert_not_called()

    def test_completed_legacy_delivery_is_not_sent_again(self):
        digest = hashlib.sha256(self.text.encode("utf-8") + self.cover.read_bytes()).hexdigest()
        pub.save_posts_queue([{"id": "one", "status": "approved", "tg_content_sha256": digest, "tg_cover_message_id": 90, "tg_cover_send_state": "confirmed", "tg_text_message_id": 91, "tg_text_send_state": "confirmed"}])
        with patch.object(pub, "publish_telegram") as send:
            self.assertEqual(self.run_post().message_id, 91)
            send.assert_not_called()

    def test_missing_cover_fails_before_network_or_queue_changes(self):
        before = pub.POSTS_QUEUE_FILE.read_bytes()
        self.cover.unlink()
        with patch.object(pub.requests, "post") as request:
            with self.assertRaisesRegex(ValueError, "обложки"):
                self.run_post()
            request.assert_not_called()
        self.assertEqual(pub.POSTS_QUEUE_FILE.read_bytes(), before)

    def test_dry_run_has_no_network_or_queue_changes(self):
        before = pub.POSTS_QUEUE_FILE.read_bytes()
        with patch.object(pub.requests, "post") as request:
            self.assertIn("одним сообщением", self.run_post(dry_run=True).message)
            request.assert_not_called()
        self.assertEqual(pub.POSTS_QUEUE_FILE.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
