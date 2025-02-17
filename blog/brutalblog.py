import os
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime

POSTS_DIR = "posts"
POSTS_JSON = "posts.json"

# Ensure posts directory exists
if not os.path.exists(POSTS_DIR):
    os.makedirs(POSTS_DIR)

def load_posts_json():
    if not os.path.exists(POSTS_JSON):
        return []
    try:
        # Using utf-8-sig to handle any BOM issues
        with open(POSTS_JSON, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load posts.json: {e}")
        return []

def save_posts_json(data):
    try:
        with open(POSTS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save posts.json: {e}")

def get_next_post_number():
    posts = load_posts_json()
    numbers = []
    for post in posts:
        link = post.get("link", "")
        filename = os.path.basename(link)
        try:
            num = int(filename[:4])
            numbers.append(num)
        except ValueError:
            continue
    next_num = max(numbers) + 1 if numbers else 0
    return f"{next_num:04d}"

def refresh_post_list():
    post_listbox.delete(0, tk.END)
    posts = load_posts_json()
    posts_sorted = sorted(posts, key=lambda x: x["link"])
    for post in posts_sorted:
        link = post.get("link", "")
        filename = os.path.basename(link)
        post_listbox.insert(tk.END, filename)

current_file = None  # Tracks the file currently being edited

def save_post():
    global current_file
    title = title_entry.get().strip()
    description = desc_entry.get().strip()
    markdown = markdown_text.get("1.0", tk.END).strip()

    if not title:
        messagebox.showerror("Error", "Post Title cannot be empty!")
        return

    current_date = datetime.now().strftime("%Y-%m-%d")

    if current_file is None:
        # Save as new post
        number = get_next_post_number()
        clean_title = "".join(title.split()).lower()
        filename = f"{number}_{clean_title}.md"
        filepath = os.path.join(POSTS_DIR, filename)
        content = f"Title: {title}\nDescription: {description}\n\n{markdown}"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            posts = load_posts_json()
            new_entry = {
                "title": title,
                "date_published": current_date,
                "last_edited": current_date,
                "description": description,
                "link": f"{POSTS_DIR}/{filename}"
            }
            posts.append(new_entry)
            save_posts_json(posts)
            messagebox.showinfo("Success", f"Post saved as {filename}")
            refresh_post_list()
            clear_fields()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save post: {e}")
    else:
        # Update existing post
        filename = current_file
        filepath = os.path.join(POSTS_DIR, filename)
        content = f"Title: {title}\nDescription: {description}\n\n{markdown}"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            posts = load_posts_json()
            updated = False
            for post in posts:
                if post.get("link") == f"{POSTS_DIR}/{filename}":
                    post["title"] = title
                    post["description"] = description
                    post["last_edited"] = current_date
                    updated = True
                    break
            if updated:
                save_posts_json(posts)
            messagebox.showinfo("Success", f"Post updated: {filename}")
            refresh_post_list()
            clear_fields()
            current_file = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update post: {e}")

def clear_fields():
    global current_file
    title_entry.delete(0, tk.END)
    desc_entry.delete(0, tk.END)
    markdown_text.delete("1.0", tk.END)
    post_listbox.selection_clear(0, tk.END)
    current_file = None

def load_post():
    global current_file
    try:
        selection = post_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No post selected!")
            return
        filename = post_listbox.get(selection[0])
        current_file = filename
        filepath = os.path.join(POSTS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # Split the content into header and markdown body
        try:
            header, md_content = content.split("\n\n", 1)
        except ValueError:
            md_content = content

        # Load metadata from posts.json (the source of truth for title and description)
        posts = load_posts_json()
        record = None
        for post in posts:
            if post.get("link") == f"{POSTS_DIR}/{filename}":
                record = post
                break
        if record:
            loaded_title = record.get("title", "")
            loaded_desc = record.get("description", "")
        else:
            loaded_title = ""
            loaded_desc = ""
        title_entry.delete(0, tk.END)
        title_entry.insert(0, loaded_title)
        desc_entry.delete(0, tk.END)
        desc_entry.insert(0, loaded_desc)
        markdown_text.delete("1.0", tk.END)
        markdown_text.insert(tk.END, md_content)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load post: {e}")

def toggle_list():
    global list_visible
    if list_visible:
        right_frame.pack_forget()
        list_visible = False
        toggle_btn.config(text="Show List")
    else:
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        list_visible = True
        toggle_btn.config(text="Hide List")

# Create main window
root = tk.Tk()
root.title("Brutal Blog Editor 💥")
root.geometry("900x600")

# Left frame for editor fields and buttons
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

tk.Label(left_frame, text="Post Title").grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
title_entry = tk.Entry(left_frame, width=50)
title_entry.grid(row=1, column=0, padx=5, pady=(0, 10), sticky=tk.W)

tk.Label(left_frame, text="Post Description").grid(row=2, column=0, sticky=tk.W, pady=(0, 2))
desc_entry = tk.Entry(left_frame, width=50)
desc_entry.grid(row=3, column=0, padx=5, pady=(0, 10), sticky=tk.W)

tk.Label(left_frame, text="Markdown").grid(row=4, column=0, sticky=tk.W, pady=(0, 2))
markdown_text = scrolledtext.ScrolledText(left_frame, width=70, height=20)
markdown_text.grid(row=5, column=0, padx=5, pady=(0, 10), sticky=tk.W)

button_frame = tk.Frame(left_frame)
button_frame.grid(row=6, column=0, pady=10, sticky=tk.W)

save_btn = tk.Button(button_frame, text="Save", width=10, command=save_post)
save_btn.pack(side=tk.LEFT, padx=(0, 10))

clear_btn = tk.Button(button_frame, text="Clear", width=10, command=clear_fields)
clear_btn.pack(side=tk.LEFT, padx=(0, 10))

edit_btn = tk.Button(button_frame, text="Edit", width=10, command=load_post)
edit_btn.pack(side=tk.LEFT, padx=(0, 10))

toggle_btn = tk.Button(left_frame, text="Hide List", width=10, command=toggle_list)
toggle_btn.grid(row=7, column=0, sticky=tk.W, pady=(0, 10))

# Right frame for the list of posts
right_frame = tk.Frame(root, bd=2, relief=tk.SUNKEN)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
list_visible = True

tk.Label(right_frame, text="Posts List").pack(pady=(5, 0))
post_listbox = tk.Listbox(right_frame, width=40)
post_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
list_scrollbar = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=post_listbox.yview)
list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
post_listbox.config(yscrollcommand=list_scrollbar.set)

refresh_post_list()

root.mainloop()
