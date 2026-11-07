import unittest
from unittest import mock
import publish
class TeaserPolicyTests(unittest.TestCase):
 def test_disabled_direct_call_never_resolves_url_or_sends(self):
  with mock.patch.object(publish, "sync_dzen_url", side_effect=AssertionError("unexpected network")), mock.patch.object(publish, "publish_telegram", side_effect=AssertionError("unexpected send")), mock.patch.object(publish, "publish_vk", side_effect=AssertionError("unexpected send")):
   publish.publish_dzen_teasers({"id":"paired","teasers_enabled":False},dry_run=False,token="test",main_ch="@test",vk_token="test",vk_group="1")
 def test_disabled_schedule_slot_skips_before_url_and_cover_work(self):
  with mock.patch.object(publish,"load_queue",return_value=[{"id":"paired","teasers_enabled":False}]), mock.patch.object(publish,"sync_dzen_url",side_effect=AssertionError("unexpected network")), mock.patch.object(publish,"ensure_campaign_covers",side_effect=AssertionError("unexpected cover")):
   ok,message=publish.execute_schedule_slot({"action":"publish_teasers","campaign_id":"paired"},dry_run=False)
   self.assertTrue(ok)
   self.assertIn("отключены",message)
 def test_default_policy_still_requires_confirmed_dzen_url(self):
  with mock.patch.object(publish,"sync_dzen_url",return_value="") as sync:
   with self.assertRaisesRegex(RuntimeError,"pending"):
    publish.publish_dzen_teasers({"id":"unpaired"},dry_run=False,token="",main_ch="",vk_token="",vk_group="")
   sync.assert_called_once_with("unpaired")
