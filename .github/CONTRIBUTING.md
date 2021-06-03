# Contributing to ListenBrainz

This guide is intended to simplify the process for a new contributor to make a
contribution to ListenBrainz. These recommendations help improve review time and
prevent less back-and-forth for common problems.

## MetaBrainz guidelines

There is a maintained list of guidelines in the
[metabrainz/guidelines](https://github.com/metabrainz/guidelines) repository.
Some of the guides there include topics like…

- [GitHub](https://github.com/metabrainz/guidelines/blob/master/GitHub.md)
- [JIRA](https://github.com/metabrainz/guidelines/blob/master/Jira.md)
- [Python](https://github.com/metabrainz/guidelines/blob/master/Python.md)
- [SQL](https://github.com/metabrainz/guidelines/blob/master/SQL.md)

Review these guides to understand our methodologies better.

## Hang out with our community

Open source projects are great, but they're better with people! If you want to
hang out with the development community or get help with contributing, use
either IRC or Discourse to join the MetaBrainz and other \*Brainz project
communities.

- **IRC**: `#metabrainz` ([webchat](https://kiwiirc.com/nextclient/irc.libera.chat/#metabrainz))
- **Discourse**: [community.metabrainz.org](https://community.metabrainz.org/ "MetaBrainz Community Discourse")

## Coding style

ListenBrainz follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/)
standard for Python. We ignore one recommendation:

- **E501 - Maximum line length (79 characters)**: Our general limit is somewhere
  around 120-130.

Remember, the purpose is to make the code in a project consistent and easy for a
human to read. Use this as your guiding principle for code style.

_Recommended video_:
"[Beyond PEP 8 -- Best practices for beautiful intelligible code](https://www.youtube.com/watch?v=wf-BqAjZb8M)"
by Raymond Hettinger at PyCon 2015, which talks about the famous P versus NP
problem.

### Docstrings

Unless the function is easy to quickly understand, it needs a docstring
describing what it does, how it does it, what the arguments are, and what
the expected output is.

We recommend using
["Google-style" docstrings](https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments)
for writing docstrings.

## Git workflow

We follow a "typical" GitHub workflow for contributing changes.

1. **[Fork](https://help.github.com/articles/fork-a-repo/) a repository** into
   your account.
2. Create a new branch and _give it a meaningful name_.
   - For example, if you are going to fix issue PICARD-257, branch can be called `picard-257` or `preserve-artwork`.
3. Make your changes and **commit them with a
   [good description](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)**.
   _ Write your commit summary lines in **imperative voice** and **sentence case**.
   _ Commit message contents don't need a lot of details, but make sure others
   can look back later and understand your changes and why.
4. Ensure that you follow the [pull request requirements](#pull-request-requirements).
5. **[Create](https://help.github.com/articles/creating-a-pull-request/) a new
   pull request** on GitHub.
   - Make your pull request title descriptive and consistent.
   - If you are fixing an issue in our bug tracker, reference it like this:
     `PICARD-257: Allow preserving existing cover-art tags`. **Not**
     `[PICARD-257] - Allow preserving existing cover-art tags` or `Allow preserving existing cover-art tags (PICARD-257)` or simply `PICARD-257`.
6. **Add a bug tracker link** to the ticket your pull request solves in the
   description.
7. **Make smaller pull requests** for each major change.
   - If you are solving more than one issue, split them into multiple pull
     requests. It is easier to review and merge patches this way.
8. Get feedback on a pull request and need to make changes? Add new commits instead of using a
   [git rebase](https://help.github.com/articles/about-git-rebase/)

## Writing unit tests

Unit tests are an important part of ListenBrainz. It helps make it easier for
developers to test changes and help prevent easily avoidable mistakes later on.

New bugfixes or new features should include unit tests. Unit tests are present
with their modules while integration tests are present in
`listenbrainz/tests/integration`. If you need help with writing a unit test, ask
in IRC or Discourse (links above).

## Pull Request Requirements

Before posting a Pull Request, make an effort to:

- Clean up and simplify your code.
- Add as much error handling as possible.
- Document your code.
- Run all existing tests and make them pass.
- Write any new tests required if you've added new features.

---

![MetaBrainz community <3 - from MetaBrainz Summit 2017](https://musicbrainz.files.wordpress.com/2017/11/meb.jpg?w=625 "MetaBrainz community <3 - from MetaBrainz Summit 2017")
