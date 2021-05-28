#!/usr/bin/env python3
from html.parser import HTMLParser
import argparse
from datetime import datetime, timezone
import logging
import os
import os.path
import shutil

from docutils.core import publish_parts
from jinja2 import Environment, FileSystemLoader
import yaml

def main():
  parser = argparse.ArgumentParser(description="Generate a static website.")
  parser.add_argument("-c", "--config", nargs="?", default="funnel4.yml", help="config file path, default to funnel4.yml")
  args = parser.parse_args()

  if os.path.exists(args.config):
    with open(args.config) as f:
      config = yaml.safe_load(f.read())
  else:
    config = {}

  basedir = os.path.dirname(os.path.abspath(args.config))
  if not os.path.exists(os.path.join(basedir, config.get("src_path", "src"))):
    parser.print_help()
    return

  logging.basicConfig(format="[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)
  website = Website(basedir, config)
  website.generate()

class Website(object):
  def __init__(self, basedir: str, config: dict):
    self.basedir = basedir
    self.config = {
      "src_path": os.path.join(self.basedir, "src"),
      "out_path": os.path.join(self.basedir, "out"),
      "blog": {
        "post_template": "templates/_blog_post.html",
        "posts_per_page": 4,
        "feeds": [
          {
            "template": "templates/_blog_index.html",
            "path": "blog/index",
          },
          {
            "template": "templates/_blog_feed.xml",
            "path": "blog/feed",
          },
        ]
      }
    }

    self.config.update(config)

    self._jinja2_env = Environment(loader=FileSystemLoader(searchpath=os.path.join(self.basedir, "src")))
    self._jinja2_env.globals["now"] = datetime.utcnow().replace(tzinfo=timezone.utc, microsecond=0)

    self._logger = logging.getLogger("funnel4")
    self._logger.setLevel(logging.DEBUG)

    self._rst_j2context_cache = {}

  def generate(self):
    self.generate_static_pages()
    self.generate_blog_feeds()

  def generate_static_pages(self):
    for root, _dirs, files in os.walk(self.config["src_path"]):
      for file in files:
        full_filename = os.path.join(root, file)
        relative_filename = self._relative_filename(full_filename)

        if relative_filename.startswith("templates/"):
          # Either the templates directory, or a subdirectory of the templates
          # directory will be skipped.
          continue

        if relative_filename.startswith("static/"):
          self.copy_static_file(full_filename)
          continue

        # A jinja2 partial file. Do not render
        if file.startswith("_") and file.endswith(".html"):
          continue

        if relative_filename.startswith("blog/"):
          self.render_file(full_filename, self.config["blog"]["post_template"])
        else:
          self.render_file(full_filename, relative_filename)

  def generate_blog_feeds(self):
    blog_posts = self.discover_blog_posts()
    n = self.config["blog"]["posts_per_page"]

    # Render the paginated main feed first.
    all_posts = blog_posts.pop("__all__")
    all_posts = [post for post in all_posts if not post.get("draft")]

    all_posts_paginated = [all_posts[i:i+n] for i in range(0, len(all_posts), n)]

    if len(all_posts_paginated) == 0:
      all_posts_paginated = [[]]

    # Render each page in a loop.
    for i, posts_for_single_page in enumerate(all_posts_paginated):
      page_num = i + 1
      context = {
        "page_num": page_num,
        "num_pages": len(all_posts_paginated),
        "posts": posts_for_single_page,
        "category": "__all__"
      }

      # We can have multiple global feeds, so here it is.
      for feed in self.config["blog"]["feeds"]:
        ext = os.path.splitext(feed["template"])[1]
        out_filename = os.path.join(self.config["out_path"], feed["path"], "{}{}".format(page_num, ext))
        template = self._jinja2_env.get_template(feed["template"])
        # TODO: probably better to use .stream().dump(multi_io), where multi_io writes to two files simultaneously
        data = template.render(context)

        self._logger.info("writing blog feed ({}/{}) {}".format(page_num, len(all_posts_paginated), out_filename))
        os.makedirs(os.path.dirname(out_filename), exist_ok=True)
        with open(out_filename, "w") as f:
          f.write(data)

        # Also write the index.html page
        if page_num == 1:
          out_filename = os.path.join(self.config["out_path"], feed["path"], "index{}".format(ext))
          self._logger.info("writing blog feed ({}/{}) {}".format(page_num, len(all_posts_paginated), out_filename))
          with open(out_filename, "w") as f:
            f.write(data)

    # TODO: now render the category index.
    # This is not paginated and everything is dumped in a single page for now.

  def copy_static_file(self, full_filename: str):
    out_filename = self._out_filename(full_filename, convert_extension=False)
    self._logger.info("copy static file {} to {}".format(full_filename, out_filename))
    os.makedirs(os.path.dirname(out_filename), exist_ok=True)
    shutil.copyfile(full_filename, out_filename)

  def render_file(self, full_filename: str, template_name: str):
    extension = os.path.splitext(full_filename)[1]
    out_filename = self._out_filename(full_filename)

    if extension == ".rst":
      context = self._rst_j2context(full_filename)
    else:
      context = {}

    self._logger.info("rendering {} with {} context variables and copying to {}".format(
      full_filename,
      len(context),
      out_filename
    ))

    os.makedirs(os.path.dirname(out_filename), exist_ok=True)

    template = self._jinja2_env.get_template(template_name)
    template.stream(context).dump(out_filename, encoding="utf-8")

  def discover_blog_posts(self):
    blog_posts = {
      "__all__": [], # This has a list of all blog posts, regardless which folder
    }

    for root, _dirs, files in os.walk(os.path.join(self.config["src_path"], "blog")):
      for file in files:
        full_filename = os.path.join(root, file)
        context = self._rst_j2context(full_filename)
        for required_metadata_key in ["created_at", "title"]:
          if required_metadata_key not in context:
            raise KeyError("{} doesn't define {} in the metadata when it is required".format(full_filename, required_metadata_key))

        blog_posts["__all__"].append(context)
        blog_posts.setdefault(os.path.dirname(full_filename), []).append(context)


    for _, posts in blog_posts.items():
      posts.sort(key=lambda post: post["created_at"], reverse=True)

    return blog_posts

  def _rst_j2context(self, full_filename: str) -> dict:
    if full_filename in self._rst_j2context_cache:
      return self._rst_j2context_cache[full_filename]

    with open(full_filename) as f:
      rst = f.read()

    parts = publish_parts(rst, source_path=full_filename, writer_name="html")
    parser = MetaParser()
    parser.feed(parts["meta"])

    context = {}
    context.update(parser.metadata)
    context.update({
      "html_body": parts["html_body"],
      "metadata": parser.metadata,
      "href": self._href(full_filename),
    })

    return context

  def _href(self, full_filename: str) -> str:
    if os.path.basename(full_filename) == "index.html":
      return os.path.dirname(full_filename.replace(self.config["src_path"], "/")) + "/"

    ext = os.path.splitext(full_filename)[1]
    return full_filename.replace(self.config["src_path"], "").replace(ext, ".html")

  def _out_filename(self, full_filename: str, convert_extension: bool=True) -> str:
    out_filename = full_filename.replace(self.config["src_path"], self.config["out_path"])
    if convert_extension:
      ext = os.path.splitext(full_filename)[1]
      out_filename = out_filename.replace(ext, ".html")

    return out_filename

  def _relative_filename(self, full_filename: str) -> str:
    # This function is called a lot, but that's ok.
    return full_filename.replace(self.config["src_path"], "").lstrip("/")


class MetaParser(HTMLParser):
  """
  This class is needed to parse the metadata for all rst renders. The metadata
  is only returned by docutils as HTML. We want the metadata to be a part of
  the context.
  """
  def __init__(self):
    super().__init__()

    self.metadata = {}

  def handle_starttag(self, tag, attrs):
    if tag != "meta":
      return

    attrs = dict(attrs)
    name = attrs.get("name", None)
    content = attrs.get("content", None)
    if name is None or content is None:
      return

    if name in self.metadata:
      raise ValueError("name {} is specified multiple times in the metadata".format(name))

    if name in ["created_at", "updated_at"]:
      pass # TODO: parse datetime

    self.metadata[name] = content


if __name__ == "__main__":
  main()
