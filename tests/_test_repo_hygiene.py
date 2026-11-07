"""仓库卫生：accounts/ 下的账号密钥不能被 git 跟踪。

`.gitignore` 只挡「还没进版本库」的东西——一旦某个账号 JSON 被误提交过一次，
之后它就一直是 tracked，`.gitignore` 再也管不住它（`git add -A` 会继续带着它
走）。所以这里不看 `.gitignore` 写了什么，直接问 git：到底有哪些 accounts 文件
在版本库里。

两个断言分开写，因为它们的失效方式不一样：
  - 规则写漏了 → 新文件会被 `git add -A` 加进来（第二、三个测试兜）
  - 已经误提交了 → 规则写得再对也没用，得 `git rm --cached`（第一个测试兜）

没有 `.git` 目录时（发布 tarball、便携包、源码 zip）整组跳过：那些地方本来就
没有版本库，谈不上泄漏。
"""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# accounts/ 下唯一允许进版本库的文件：给用户解释这个目录放什么，本身不含密钥。
ALLOWED_TRACKED = frozenset(("accounts/README.txt",))


def git(*args):
    """跑 git 子命令并返回 stdout 文本；git 不可用或命令失败时返回 None。"""
    try:
        proc = subprocess.run(
            ("git",) + args,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def tracked_accounts():
    """版本库里 accounts/ 下的全部路径。"""
    listing = git("ls-files", "--", "accounts")
    if listing is None:
        return None
    return [line.strip() for line in listing.splitlines() if line.strip()]


class AccountsDirectoryStaysOutOfGit(unittest.TestCase):
    def setUp(self):
        if tracked_accounts() is None:
            self.skipTest("not a git checkout")

    def test_only_the_readme_is_tracked(self):
        """已经进版本库的 accounts 文件里，除了 README.txt 一个都不该有。"""
        extra = sorted(set(tracked_accounts()) - ALLOWED_TRACKED)
        self.assertEqual(
            extra,
            [],
            "这些 accounts/ 文件已经被 git 跟踪，里面是真实账号密钥；"
            "用 `git rm --cached <path>` 把它们移出版本库：%s" % (extra,),
        )

    def test_subdirectories_are_ignored(self):
        """按渠道分的子目录（codearts/ 这种）整棵都要被忽略。

        断言用的是编出来的路径：真实目录不存在时也要成立，否则新加一个渠道目录
        就会悄悄绕过规则。深层嵌套一并覆盖——目录被忽略，整棵树都进不来。
        """
        for path in (
            "accounts/codearts/state.json",
            "accounts/codearts/codearts-0123456789abcdef.json",
            "accounts/some-future-channel/state.json",
            "accounts/some-future-channel/nested/account.json",
        ):
            proc = subprocess.run(
                ("git", "check-ignore", "-q", "--", path),
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(
                proc.returncode,
                0,
                "accounts 的子目录没被 .gitignore 挡住，`git add -A` 会把账号密钥"
                "推上公开仓库：%s" % path,
            )

    def test_the_readme_is_not_ignored(self):
        """`!accounts/README.txt` 白名单还生效。

        这条容易被后面的 `accounts/*/` 之类规则顺手盖掉，盖掉了就说明有人改规则
        时没想清楚，得当场知道。
        """
        proc = subprocess.run(
            ("git", "check-ignore", "-q", "--", "accounts/README.txt"),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(
            proc.returncode,
            1,
            "accounts/README.txt 被 .gitignore 忽略了，但它是仓库里解释这个目录的"
            "唯一文件，应该保留在版本库里",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
