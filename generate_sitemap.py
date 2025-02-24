import json
from datetime import datetime

# Load posts.json
try:
    with open("posts.json", "r", encoding="utf-8") as f:
        posts = json.load(f)
except FileNotFoundError:
    print("Error: posts.json not found.")
    exit()

BASE_URL = "https://blog.zettelkasten.shop"

# XML header
sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

# Add homepage
sitemap_content += f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{datetime.utcnow().date()}</lastmod>
    <priority>1.0</priority>
  </url>\n"""

# Add each blog post
for post in posts:
    post_url = f"{BASE_URL}/{post['link']}"
    lastmod = post.get("date_published", datetime.utcnow().date())  
    sitemap_content += f"""  <url>
    <loc>{post_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <priority>0.8</priority>
  </url>\n"""

sitemap_content += "</urlset>"

# Save to sitemap.xml
with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap_content)

print("sitemap.xml has been generated successfully.")
