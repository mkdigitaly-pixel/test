"""Blog metadata checks with no external publication calls."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dzen_rss as blog


class BlogSeoTests(unittest.TestCase):
    def test_schedule_and_other_platform_dates_are_not_blog_dates(self):
        item = {"id": "unpublished", "scheduled_dzen": "2099-01-01", "published_at": "2020-01-01", "dzen_published_at": "2020-01-02"}
        with patch.object(blog, "_rss_article_publication_dates", return_value={}):
            self.assertEqual(blog._item_pub_raw(item), "")
        self.assertEqual(blog._verified_publication_date("2099-01-01"), "")

    def test_article_schema_and_service_links_match_the_known_date(self):
        page = blog._article_html_page("new-seo-topic", "<h1>Тема</h1><p>Текст.</p>", {
            "title": "Тема", "description": "Описание", "published_at": "2026-10-09T07:12:44+00:00", "published_label": "9 октября 2026",
        })
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
        article, breadcrumb = graph["@graph"]
        self.assertEqual(article["datePublished"], "2026-10-09T07:12:44+00:00")
        self.assertEqual(breadcrumb["@type"], "BreadcrumbList")
        self.assertIn("/audit-yandex-direct", page)
        self.assertIn("/nastrojka-yandex-direct", page)
        self.assertEqual(page.count('property="og:type"'), 1)
        self.assertIn('property="og:type" content="article"', page)
        self.assertIn("Onest", page)
        self.assertIn("blog-theme.css?v=" + blog.BLOG_STYLE_VERSION, page)

    def test_rss_republication_keeps_the_blog_first_date(self):
        old_feed = '<rss><channel><item><guid isPermaLink="false">mkekspert-dzen-existing</guid><link>https://blog.mkekspert.ru/articles/existing.html</link><pubDate>Mon, 12 Oct 2026 00:00:00 +0000</pubDate></item></channel></rss>'
        feed = MagicMock()
        feed.is_file.return_value = feed.exists.return_value = True
        feed.read_bytes.return_value = old_feed.encode()
        feed.read_text.return_value = old_feed
        with patch.object(blog, "FEED_FILE", feed), patch.object(blog, "_queue_items", return_value=[{"id": "existing", "blog_published_at": "2026-09-02T11:29:13+00:00"}]):
            blog.upsert_article_item(campaign_id="existing", article_path=Path("existing.md"), title="Обновление", description="Описание", body_html="<p>Текст</p>", cover_rel=None)
        saved = feed.write_text.call_args.args[0]
        self.assertIn("Wed, 02 Sep 2026 11:29:13 +0000", saved)
        self.assertEqual(saved.count("<item>"), 1)

    def test_sitemap_uses_known_dates_and_contains_contacts(self):
        root = ET.fromstring(blog._blog_sitemap_xml([{"url": "https://blog.mkekspert.ru/articles/test.html", "published_at": "2026-10-09T07:12:44+00:00"}]))
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall("sm:url", namespace)
        self.assertEqual(len(urls), 3)
        self.assertIsNone(urls[1].find("sm:lastmod", namespace))
        self.assertEqual(urls[2].findtext("sm:lastmod", namespaces=namespace), "2026-10-09")

    def test_rss_rebuild_does_not_publish_an_approved_future_article(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "future.md").write_text("---\ntitle: Future\n---\nText", encoding="utf-8")
            with patch.object(blog, "ROOT", root), patch.object(blog, "_rss_article_publication_dates", return_value={}):
                item = {"id": "future", "status": "approved", "dzen_article": "future.md", "scheduled_dzen": "2099-01-01"}
                self.assertFalse(blog._item_eligible_for_rss(item, channel_titles=[]))

    def test_a_reviewed_article_with_the_correct_date_is_preserved_exactly(self):
        first_date = "2026-10-09T07:12:44+00:00"
        existing = '<html><head><script type="application/ld+json">{"@type":"Article","datePublished":"' + first_date + '"}</script></head><body><h1>Тема</h1><p class="publication-date">Дата</p><p>Проверенный текст.</p></body></html>'
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "articles/existing.html"
            target.parent.mkdir()
            target.write_text(existing, encoding="utf-8")
            with patch.object(blog, "_blog_posts", return_value=[{"id": "existing", "published_at": first_date}]):
                blog._write_gh_pages_files(Path(folder), {"articles/existing.html": b"older local export"})
            self.assertEqual(target.read_bytes(), existing.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
