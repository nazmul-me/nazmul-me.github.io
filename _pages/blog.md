---
layout: default
title: Blog
permalink: /blog/
author_profile: true
redirect_from:
  - /blogs/
  - /blogs.html
---

# Blog

{% if site.posts and site.posts.size > 0 %}
<ul class="archive__list">
  {% for post in site.posts %}
  <li>
    <a class="archive__item-title" href="{{ post.url | relative_url }}">{{ post.title }}</a>
    <span class="page__meta">{{ post.date | date: "%b %d, %Y" }}</span>
  </li>
  {% endfor %}
</ul>
{% else %}
<p>No posts yet. Check back soon!</p>
{% endif %}