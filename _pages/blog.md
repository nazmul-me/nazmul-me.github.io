<!-- ---
layout: default
title: Blog
permalink: /blog/
author_profile: true
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
{% endif %} -->


---
permalink: /blog/
title: ""
excerpt: ""
author_profile: true
redirect_from: 
  - /about/
  - /about.html
---

{% if site.google_scholar_stats_use_cdn %}
{% assign gsDataBaseUrl = "https://cdn.jsdelivr.net/gh/" | append: site.repository | append: "@" %}
{% else %}
{% assign gsDataBaseUrl = "https://raw.githubusercontent.com/" | append: site.repository | append: "/" %}
{% endif %}
{% assign url = gsDataBaseUrl | append: "google-scholar-stats/gs_data_shieldsio.json" %}

{% include_relative sections/aboutMe.md %}

There is no blog post.