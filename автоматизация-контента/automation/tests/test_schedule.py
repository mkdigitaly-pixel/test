import argparse
import copy
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publish as pub
import dzen_rss as rss


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'queue').mkdir()
        self.patches = [patch.object(pub,'ROOT',self.root),
            patch.object(pub,'QUEUE_FILE',self.root/'queue/campaigns.yaml'),
            patch.object(pub,'POSTS_QUEUE_FILE',self.root/'queue/posts.yaml'),
            patch.object(pub,'SCHEDULE_FILE',self.root/'queue/schedule.yaml'),
            patch.object(pub,'load_env')]
        for p in self.patches: p.start()
        pub.save_queue([]); pub.save_posts_queue([])
        pub.save_schedule({'timezone':'Asia/Yekaterinburg','slots':[]})

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_timezone_and_legacy_history(self):
        slot={'date':'2026-10-13','time':'12:00'}
        self.assertEqual(pub.slot_when(slot).utcoffset(),timedelta(hours=5))
        slot['timezone']='Europe/Moscow'
        self.assertEqual(pub.slot_when(slot).utcoffset(),timedelta(hours=3))

    def test_future_slot_never_runs_and_dry_run_does_not_save(self):
        pub.save_schedule({'timezone':'Asia/Yekaterinburg','slots':[
            {'date':'2026-10-09','time':'14:00','action':'publish_tg_post','post_id':'one','status':'scheduled'}]})
        before=pub.SCHEDULE_FILE.read_bytes()
        now=datetime(2026,10,9,13,59,tzinfo=pub.ZoneInfo('Asia/Yekaterinburg'))
        args=argparse.Namespace(dry_run=True,date=None,force=False)
        with patch.object(pub,'now_msk',return_value=now), patch.object(pub,'execute_schedule_slot') as execute:
            pub.cmd_schedule_run(args)
            execute.assert_not_called()
        self.assertEqual(before,pub.SCHEDULE_FILE.read_bytes())

    def test_dry_flag_overrides_auto_publish(self):
        pub.save_schedule({'timezone':'Asia/Yekaterinburg','slots':[
            {'date':'2026-10-09','time':'14:00','action':'publish_tg_post','post_id':'one','status':'scheduled'}]})
        args=argparse.Namespace(dry_run=False,date=None,force=False)
        now=datetime(2026,10,9,14,0,tzinfo=pub.ZoneInfo('Asia/Yekaterinburg'))
        with patch.dict(os.environ,{'AUTO_PUBLISH':'true','DRY_RUN':'true'}), patch.object(pub,'now_msk',return_value=now), patch.object(pub,'execute_schedule_slot',return_value=(True,'ok')) as execute:
            pub.cmd_schedule_run(args)
            self.assertTrue(execute.call_args.kwargs['dry_run'])
        self.assertEqual(pub.load_schedule()['slots'][0]['status'],'scheduled')

    def test_stale_slots_expire_without_publishing(self):
        pub.save_schedule({'timezone':'Asia/Yekaterinburg','catchup_hours':24,'slots':[
            {'date':'2026-10-07','time':'14:00','action':'publish_tg_post','post_id':'one','status':'scheduled'}]})
        now=datetime(2026,10,9,14,0,tzinfo=pub.ZoneInfo('Asia/Yekaterinburg'))
        with patch.dict(os.environ,{'AUTO_PUBLISH':'true','DRY_RUN':'false'}), patch.object(pub,'now_msk',return_value=now), patch.object(pub,'execute_schedule_slot') as execute:
            pub.cmd_schedule_run(argparse.Namespace(dry_run=False,date=None,force=False))
            execute.assert_not_called()
        self.assertEqual(pub.load_schedule()['slots'][0]['status'],'expired')

    def test_published_article_is_not_sent_again(self):
        pub.save_queue([{'id':'one','status':'published','dzen_url':'https://dzen.ru/a/example'}])
        with patch.object(pub,'cmd_publish') as publish:
            self.assertTrue(pub.execute_schedule_slot({'action':'publish_dzen','campaign_id':'one'},dry_run=False)[0])
            publish.assert_not_called()

    def test_vk_failure_keeps_telegram_receipt_and_retry_skips_telegram(self):
        item={'id':'one','status':'approved','dzen_url':'https://dzen.ru/a/example',
              'dzen_teaser_tg':'tg.md','dzen_teaser_vk':'vk.md'}
        (self.root/'tg.md').write_text('Read [ссылка]')
        (self.root/'vk.md').write_text('Read [ссылка]')
        pub.save_queue([item])
        with patch.object(pub,'vk_publish_allowed',return_value=True), patch.object(pub,'vk_photos_allowed',return_value=True), patch.object(pub,'publish_telegram',return_value=pub.PublishResult('telegram',True,'ok',101)) as tg, patch.object(pub,'publish_vk',side_effect=RuntimeError('VK rejected')):
            with self.assertRaises(RuntimeError):
                pub.publish_dzen_teasers(item,dry_run=False,token='test',main_ch='test',vk_token='test',vk_group='123')
            tg.assert_called_once()
        saved=pub.load_queue()[0]
        self.assertEqual(saved['tg_teaser_message_id'],101)
        with patch.object(pub,'vk_publish_allowed',return_value=True), patch.object(pub,'vk_photos_allowed',return_value=True), patch.object(pub,'publish_telegram') as tg, patch.object(pub,'publish_vk',return_value=pub.PublishResult('vk',True,'ok',202)):
            pub.publish_dzen_teasers(saved,dry_run=False,token='test',main_ch='test',vk_token='test',vk_group='123')
            tg.assert_not_called()
        self.assertEqual(pub.load_queue()[0]['vk_teaser_message_id'],202)

    def test_missing_cover_never_generates_fallback(self):
        pub.save_queue([{'id':'one','cover':'missing.jpg'}])
        with self.assertRaises(RuntimeError): pub.ensure_campaign_covers('one',dry_run=False)

    def test_blog_merge_preserves_existing_pages_and_verification(self):
        (self.root/'articles').mkdir()
        (self.root/'articles/old.html').write_bytes(b'reviewed layout')
        (self.root/'google-check.html').write_bytes(b'verification')
        rss._write_gh_pages_files(self.root,{'articles/old.html':b'old generator','articles/new.html':b'new theme','index.html':b'new index'},'new')
        self.assertEqual((self.root/'articles/old.html').read_bytes(),b'reviewed layout')
        self.assertEqual((self.root/'google-check.html').read_bytes(),b'verification')
        self.assertEqual((self.root/'articles/new.html').read_bytes(),b'new theme')

    def test_future_approved_articles_stay_out_of_blog(self):
        items=[{'id':'published','status':'published'},{'id':'current','status':'approved'},{'id':'future','status':'approved'}]
        def meta(item):
            return {**item,'title':item['id'],'published_at':'2026-10-09T00:00:00+00:00'}
        with patch.object(rss,'_queue_items',return_value=items),patch.object(rss,'_blog_post_meta',side_effect=meta):
            self.assertEqual({p['id'] for p in rss._blog_posts('current')},{'published','current'})

    def test_secret_is_removed_from_error(self):
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'FAKE_SENSITIVE_TEST_TOKEN'}):
            self.assertNotIn('FAKE_SENSITIVE_TEST_TOKEN',pub.redacted_error(RuntimeError('network FAKE_SENSITIVE_TEST_TOKEN')))

    def test_article_date_is_visible_and_repeated_deploy_is_stable(self):
        page='<html><head><script type="application/ld+json">{"@type":"Article"}</script></head><body><h1>Title</h1><p>Reviewed body</p></body></html>'
        out=rss._with_publication_date(page,'2026-10-09T07:12:44+00:00')
        self.assertIn('9 октября 2026',out)
        self.assertIn('datePublished',out)
        self.assertIn('<p>Reviewed body</p>',out)
        again=rss._with_publication_date(out,'2026-10-09T07:12:44+00:00')
        self.assertEqual(out,again)


if __name__=='__main__': unittest.main()
