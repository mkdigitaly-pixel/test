import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import dzen_rss as blog


class DetachedBlogDeploymentTests(unittest.TestCase):
    def git(self,*args,cwd=None):
        result=subprocess.run(['git',*args],cwd=cwd or self.repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if result.returncode:
            raise AssertionError('Git fixture command failed: '+result.stderr)
        return result.stdout.strip()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.repo=root/'repo';self.repo.mkdir()
        self.remote=root/'remote.git';self.occupied=root/'existing-blog'
        self.git('init','--bare',str(self.remote))
        self.git('init','-b','main')
        self.git('config','user.name','Test')
        self.git('config','user.email','test@example.invalid')
        self.git('config','core.autocrlf','false')
        self.git('checkout','--orphan','gh-pages')
        (self.repo/'index.html').write_text('old',encoding='utf-8')
        (self.repo/'verification.txt').write_text('keep',encoding='utf-8')
        self.git('add','.')
        self.git('commit','-m','existing site')
        self.git('remote','add','origin',str(self.remote))
        self.git('push','-u','origin','gh-pages')
        self.git('checkout','-b','main')
        self.git('worktree','add',str(self.occupied),'gh-pages')

    def deploy(self,dry_run):
        with patch.object(blog,'_git_root',return_value=self.repo),patch.object(blog,'_collect_gh_pages_files',return_value={'index.html':b'new'}),patch.object(blog,'_blog_posts',return_value=[]):
            return blog.deploy_gh_pages(campaign_id='test',dry_run=dry_run)

    def test_dry_run_works_when_blog_branch_is_already_checked_out(self):
        previous=self.git('rev-parse','HEAD')
        message=self.deploy(True)
        self.assertTrue(message.startswith('[dry-run] gh-pages:'),message)
        self.assertEqual(self.git('rev-parse','HEAD'),previous)
        self.assertEqual((self.occupied/'index.html').read_text(),'old')
        self.assertEqual(self.git('--git-dir='+str(self.remote),'show','gh-pages:index.html'),'old')

    def test_detached_push_preserves_existing_checkout_and_verification(self):
        previous=self.git('rev-parse','HEAD')
        message=self.deploy(False)
        self.assertTrue(message.startswith('gh-pages '),message)
        self.assertEqual(self.git('--git-dir='+str(self.remote),'show','gh-pages:index.html'),'new')
        self.assertEqual(self.git('--git-dir='+str(self.remote),'show','gh-pages:verification.txt'),'keep')
        self.assertEqual(self.git('rev-parse','HEAD'),previous)
        self.assertEqual((self.occupied/'index.html').read_text(),'old')
