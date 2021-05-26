=======
funnel4
=======

A very lightweight static site generator with Jinja2, along with a blog
generator. The main features:

- Write websites with HTML and Jinja2.
- Maintain a blog using `reStructuredText`_.
- Implemented in a single file with only ~200 lines of code.

Licensed under AGPLv3.

.. _reStructuredText: https://docutils.sourceforge.io/docs/user/rst/quickstart.html

------
How to
------

Create a directory structure as follows: ::

    src/
      blog/              # Store all blog posts under this folder. It can be
        2021/post1.rst   # in any path without restrictions. The final HTML
        anotherpost.rst  # file will have the same path as the path of the
        otters/post.rst  # rst file relative to the src/ folder.
      static/            # All files in this directory will be copied into the
                         # out folder verbatim.
        style.css        # An example, you can put anything here.
      templates/         # In addition to the templates specified below, you
                         # put your custom templates into this folder as well.
        _blog_feed.xml   # Generates an atom or RSS feed.
        _blog_index.html # Generates the index for the blog.
        _blog_post.html  # Generates the actual blog post page.

      index.html         # Jinja2 syntax. Will be rendered to index.html
      my_page.html       # Jinja2 syntax. Will be rendered to my_page.html.
    Makefile             # An optional file for convenience. See examples/Makefile.

Now run ``funnel4``, which will automatically create the ``out`` directory and
put all rendered output into that directory. You can then just point your
browser to the HTML files and take a look. If you need a (test) server, you can
use ``cd out && python3 -m http.server``.

See ``example`` directory a more detailed example (although it is incomplete
for now).
