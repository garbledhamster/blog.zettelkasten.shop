import os
import re     # <-- Added for regex replacement
import sys
import json
import logging
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from datetime import datetime
import openai
import shutil

# Configure error logging
logging.basicConfig(filename="error.log", level=logging.ERROR,
                    format="%(asctime)s %(levelname)s: %(message)s")

def exception_hook(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.error("Uncaught exception:\n%s", err_msg)
    messagebox.showerror("Error", "An unexpected error occurred. See error.log for details.")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

# ----------------- Setup Directories & Files -----------------
POSTS_DIR = "posts"
POSTS_JSON = "posts.json"

if not os.path.exists(POSTS_DIR):
    os.makedirs(POSTS_DIR)
if not os.path.exists(POSTS_JSON):
    with open(POSTS_JSON, "w", encoding="utf-8") as file:
        json.dump([], file, indent=4)

posts_data = []
current_file = None
tooltip_window = None
tooltip_index = None
sort_option = "Date Posted"  # Default sort option
sort_order_asc = False       # Default descending order

# ----------------- Posts JSON Functions -----------------
def load_posts_json():
    try:
        with open(POSTS_JSON, "r", encoding="utf-8-sig") as file:
            return json.load(file)
    except Exception as error:
        messagebox.showerror("Error", f"Failed to load posts.json: {error}")
        logging.error("Failed to load posts.json: %s", error)
        return []

def save_posts_json(data):
    try:
        with open(POSTS_JSON, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
    except Exception as error:
        messagebox.showerror("Error", f"Failed to save posts.json: {error}")
        logging.error("Failed to save posts.json: %s", error)

def get_next_post_number():
    posts = load_posts_json()
    numbers = []
    for post in posts:
        filename = os.path.basename(post.get("link", ""))
        try:
            num = int(filename[:4])
            numbers.append(num)
        except ValueError:
            continue
    next_num = max(numbers) + 1 if numbers else 0
    return f"{next_num:04d}"

def refresh_post_list():
    global posts_data
    posts_data = load_posts_json()
    if sort_option == "Name":
        posts_data.sort(key=lambda x: x.get("title", "").lower(), reverse=not sort_order_asc)
    elif sort_option == "Number":
        posts_data.sort(key=lambda x: int(os.path.basename(x.get("link", "0000"))[:4]), reverse=not sort_order_asc)
    elif sort_option == "Date Posted":
        posts_data.sort(key=lambda x: x.get("date_published", ""), reverse=not sort_order_asc)
    elif sort_option == "Date Edited":
        posts_data.sort(key=lambda x: x.get("last_edited", ""), reverse=not sort_order_asc)
    post_listbox.delete(0, tk.END)
    for post in posts_data:
        title = post.get("title", "Untitled")
        date_published = post.get("date_published", "")
        post_listbox.insert(tk.END, f"{title} - {date_published}")

def save_post():
    global current_file
    title = title_entry.get().strip()
    description = desc_entry.get().strip()
    markdown = markdown_text.get("1.0", tk.END).strip()
    if not title:
        messagebox.showerror("Error", "Post Title cannot be empty!")
        return
    current_date = datetime.now().strftime("%Y-%m-%d")

    # 1. Strip special characters from the title to keep only letters and numbers
    #    For example: if user types "My Blog! Post #1", it becomes "MyBlogPost1".
    clean_title = re.sub(r"[^a-zA-Z0-9]+", "", title)

    if current_file is None:
        number = get_next_post_number()
        # 2. Combine the number with the cleaned title
        filename = f"{number}_{clean_title}.md"
        # 3. Force the path to use forward slashes
        filepath = f"{POSTS_DIR}/{filename}"
        content = f"Title: {title}\nDescription: {description}\n\n{markdown}"
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(content)
            posts = load_posts_json()
            new_entry = {
                "title": title,
                "date_published": current_date,
                "last_edited": current_date,
                "description": description,
                "link": f"{POSTS_DIR}/{filename}"  # force forward slash
            }
            posts.append(new_entry)
            save_posts_json(posts)
            messagebox.showinfo("Success", f"Post saved as {filename}")
            refresh_post_list()
            clear_fields()
        except Exception as error:
            messagebox.showerror("Error", f"Failed to save post: {error}")
            logging.error("Failed to save post: %s", error)
    else:
        # If we're updating an existing post
        # Use the original current_file for the number portion
        # but ensure the updated title is also sanitized
        number = current_file.split("_", 1)[0]  # e.g. "0001" from "0001_MyBlog.md"
        filename = f"{number}_{clean_title}.md"

        # Because we're effectively renaming it with the new title, we should
        # remove the old file so we don't leave duplicates around
        old_filepath = f"{POSTS_DIR}/{current_file}"
        new_filepath = f"{POSTS_DIR}/{filename}"

        content = f"Title: {title}\nDescription: {description}\n\n{markdown}"
        try:
            # Remove old file if it exists and if the filenames differ
            if os.path.exists(old_filepath) and (old_filepath != new_filepath):
                os.remove(old_filepath)

            with open(new_filepath, "w", encoding="utf-8") as file:
                file.write(content)
            posts = load_posts_json()

            # Find the matching record and update it
            for post in posts:
                if post.get("link") == f"{POSTS_DIR}/{current_file}":
                    post["title"] = title
                    post["description"] = description
                    post["last_edited"] = current_date
                    post["link"] = f"{POSTS_DIR}/{filename}"  # new link
                    break

            save_posts_json(posts)
            messagebox.showinfo("Success", f"Post updated: {filename}")
            refresh_post_list()
            clear_fields()
            current_file = None
        except Exception as error:
            messagebox.showerror("Error", f"Failed to update post: {error}")
            logging.error("Failed to update post: %s", error)

def clear_fields():
    global current_file
    title_entry.delete(0, tk.END)
    desc_entry.delete(0, tk.END)
    markdown_text.delete("1.0", tk.END)
    post_listbox.selection_clear(0, tk.END)
    current_file = None
    status_label.config(text="Creating a New Post")

def new_post():
    clear_fields()
    status_label.config(text="Creating a New Post")

def load_post(index=None):
    global current_file
    try:
        if index is None:
            selection = post_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "No post selected!")
                return
            index = selection[0]
        record = posts_data[index]
        current_file = os.path.basename(record["link"])
        filepath = record["link"]
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
        try:
            _, markdown_content = content.split("\n\n", 1)
        except ValueError:
            markdown_content = content
        title_entry.delete(0, tk.END)
        title_entry.insert(0, record.get("title", ""))
        desc_entry.delete(0, tk.END)
        desc_entry.insert(0, record.get("description", ""))
        markdown_text.delete("1.0", tk.END)
        markdown_text.insert(tk.END, markdown_content)
        status_label.config(text=f"Editing: {os.path.basename(record['link'])}")
    except Exception as error:
        messagebox.showerror("Error", f"Failed to load post: {error}")
        logging.error("Failed to load post: %s", error)

def delete_post(index=None):
    global current_file
    try:
        if index is None:
            selection = post_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "No post selected!")
                return
            index = selection[0]
        record = posts_data[index]
        filename = os.path.basename(record["link"])
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{record['title']}'?")
        if not confirm:
            return
        os.remove(record["link"])
        posts = load_posts_json()
        posts = [post for post in posts if post.get("link") != record["link"]]
        save_posts_json(posts)
        messagebox.showinfo("Success", f"Post deleted: {filename}")
        clear_fields()
        refresh_post_list()
        current_file = None
    except Exception as error:
        messagebox.showerror("Error", f"Failed to delete post: {error}")
        logging.error("Failed to delete post: %s", error)

def copy_post(index=None):
    try:
        if index is None:
            selection = post_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "No post selected!")
                return
            index = selection[0]
        record = posts_data[index]
        with open(record["link"], "r", encoding="utf-8") as file:
            content = file.read()
        root.clipboard_clear()
        root.clipboard_append(content)
        messagebox.showinfo("Copied", "Post content copied to clipboard")
    except Exception as error:
        messagebox.showerror("Error", f"Failed to copy post: {error}")
        logging.error("Failed to copy post: %s", error)

def show_context_menu(event):
    index = post_listbox.nearest(event.y)
    if index < 0 or index >= len(posts_data):
        return
    post_listbox.selection_clear(0, tk.END)
    post_listbox.selection_set(index)
    menu = tk.Menu(post_listbox, tearoff=0)
    menu.add_command(label="Edit", command=lambda: load_post(index))
    menu.add_command(label="Delete", command=lambda: delete_post(index))
    menu.add_command(label="Copy", command=lambda: copy_post(index))
    menu.tk_popup(event.x_root, event.y_root)

def on_listbox_motion(event):
    global tooltip_window, tooltip_index
    index = post_listbox.nearest(event.y)
    if index != tooltip_index:
        if tooltip_window:
            tooltip_window.destroy()
            tooltip_window = None
        tooltip_index = index
        if 0 <= index < len(posts_data):
            full_path = os.path.abspath(posts_data[index]["link"])
            x = event.x_root + 20
            y = event.y_root + 10
            tooltip_window = tk.Toplevel(post_listbox)
            tooltip_window.wm_overrideredirect(True)
            tooltip_window.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tooltip_window, text=full_path, justify=tk.LEFT,
                             background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal"))
            label.pack(ipadx=1)
    elif tooltip_window:
        x = event.x_root + 20
        y = event.y_root + 10
        tooltip_window.wm_geometry(f"+{x}+{y}")

def on_listbox_leave(event):
    global tooltip_window, tooltip_index
    if tooltip_window:
        tooltip_window.destroy()
        tooltip_window = None
    tooltip_index = None

def apply_sort(event=None):
    global sort_option
    sort_option = sort_combobox.get()
    refresh_post_list()

def toggle_sort_order():
    global sort_order_asc
    sort_order_asc = not sort_order_asc
    toggle_order_btn.config(text="Ascending" if sort_order_asc else "Descending")
    refresh_post_list()

# ----------------- Minimal Grammar Check Function -----------------
def minimal_grammar_check():
    config = get_config()
    if not config.get("api_key"):
        messagebox.showerror("Error", "No API key set. Please set an API key using Manage API Configuration.")
        return
    text = markdown_text.get("1.0", tk.END).strip()
    if not text:
        messagebox.showerror("Error", "No markdown content to check.")
        return
    try:
        openai.api_key = config["api_key"]
        prompt = (
            "Without breaking any markdown code, and actually going as far as fixing it, "
            "please minimally correct the grammar and punctuation of the following text without "
            "altering its original style:\n\n" + text
        )
        response = openai.ChatCompletion.create(
            model=config.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": config.get("instruction", "You are a helpful grammar assistant.")},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.0,
        )
        corrected_text = response.choices[0].message["content"].strip()
        markdown_text.delete("1.0", tk.END)
        markdown_text.insert(tk.END, corrected_text)
        messagebox.showinfo("Success", "Grammar check complete.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to process grammar check: {e}")
        logging.error("Failed to process grammar check: %s", e)

# ----------------- Configuration Encryption & Storage -----------------
def get_uid():
    try:
        return os.getuid()
    except AttributeError:
        return 1000

def xor_encrypt_decrypt(data: bytes, key_val: int) -> bytes:
    return bytes([b ^ key_val for b in data])

def get_config_path():
    if os.name == 'nt':
        base_dir = os.getenv("APPDATA")
    else:
        base_dir = os.path.expanduser("~/.config")
    config_dir = os.path.join(base_dir, "BrutalBlogEditor")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    config_file = os.path.join(config_dir, "config.dat")
    return config_file, config_dir

def save_config(config):
    config_file, _ = get_config_path()
    try:
        config_json = json.dumps(config)
        key_val = get_uid() & 0xFF
        encrypted = xor_encrypt_decrypt(config_json.encode("utf-8"), key_val)
        with open(config_file, "wb") as f:
            f.write(encrypted)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save configuration: {e}")
        logging.error("Failed to save configuration: %s", e)

def get_config():
    config_file, _ = get_config_path()
    if not os.path.exists(config_file):
        return {"api_key": "", "model": "gpt-4o-mini", "instruction": "You are a helpful grammar assistant."}
    try:
        with open(config_file, "rb") as f:
            encrypted = f.read()
        key_val = get_uid() & 0xFF
        decrypted = xor_encrypt_decrypt(encrypted, key_val)
        try:
            config = json.loads(decrypted.decode("utf-8"))
        except json.JSONDecodeError:
            config = {"api_key": decrypted.decode("utf-8"), "model": "gpt-4o-mini", "instruction": "You are a helpful grammar assistant."}
        return config
    except Exception:
        return {"api_key": "", "model": "gpt-4o-mini", "instruction": "You are a helpful grammar assistant."}

def remove_config():
    config_file, config_dir = get_config_path()
    if os.path.exists(config_file):
        os.remove(config_file)
    if os.path.exists(config_dir):
        shutil.rmtree(config_dir)

def manage_api_key():
    config = get_config()
    top = tk.Toplevel(root)
    top.title("Manage API Configuration")
    tk.Label(top, text="API Key:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    key_entry = ttk.Entry(top, width=40)
    key_entry.grid(row=0, column=1, padx=5, pady=5)
    key_entry.insert(0, config.get("api_key", ""))
    tk.Label(top, text="Model:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "codex"]
    model_combobox = ttk.Combobox(top, values=models, state="readonly", width=37)
    model_combobox.grid(row=1, column=1, padx=5, pady=5)
    current_model = config.get("model", "gpt-4o-mini")
    model_combobox.set(current_model if current_model in models else "gpt-4o-mini")
    tk.Label(top, text="Instruction:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
    instruction_text = scrolledtext.ScrolledText(top, wrap=tk.WORD, width=30, height=4)
    instruction_text.grid(row=2, column=1, padx=5, pady=5)
    instruction_text.insert(tk.END, config.get("instruction", "You are a helpful grammar assistant."))
    
    def save_key():
        new_key = key_entry.get().strip()
        new_model = model_combobox.get().strip()
        new_instruction = instruction_text.get("1.0", tk.END).strip()
        if not new_key:
            messagebox.showerror("Error", "API Key cannot be empty!")
            return
        new_config = {
            "api_key": new_key,
            "model": new_model,
            "instruction": new_instruction
        }
        try:
            save_config(new_config)
            messagebox.showinfo("Success", "Configuration saved.")
            top.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            logging.error("Failed to save configuration: %s", e)
    
    def remove_key():
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the configuration? This will delete the configuration folder."):
            try:
                remove_config()
                messagebox.showinfo("Success", "Configuration removed.")
                top.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove configuration: {e}")
                logging.error("Failed to remove configuration: %s", e)
    
    save_btn_api = ttk.Button(top, text="Save Configuration", command=save_key)
    save_btn_api.grid(row=3, column=0, padx=5, pady=5)
    remove_btn_api = ttk.Button(top, text="Remove Configuration", command=remove_key)
    remove_btn_api.grid(row=3, column=1, padx=5, pady=5)

def generate_post():
    config = get_config()
    if not config.get("api_key"):
        messagebox.showerror("Error", "No API key set. Please set an API key using Manage API Configuration.")
        return
    gen_window = tk.Toplevel(root)
    gen_window.title("Generate Post")
    gen_window.geometry("400x300")
    tk.Label(gen_window, text="Enter Prompt for Post Generation:").pack(padx=5, pady=5)
    prompt_text = scrolledtext.ScrolledText(gen_window, wrap=tk.WORD, width=40, height=10)
    prompt_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    def do_generate():
        prompt = prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "Prompt cannot be empty!")
            return
        try:
            openai.api_key = config["api_key"]
            full_prompt = (
                "Generate a blog post as a JSON object with the following schema:\n"
                "{\n"
                '  "title": "Your blog post title",\n'
                '  "description": "A short description",\n'
                '  "markdown": "The markdown content of the post"\n'
                "}\n"
                "Ensure that the output is valid JSON with exactly these keys and nothing else.\n"
                "Use the following prompt for context:\n"
                f"{prompt}"
            )
            response = openai.ChatCompletion.create(
                model=config.get("model", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": config.get("instruction", "You are a helpful blog post generator.")},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=1024,
                temperature=0.7,
            )
            generated_content = response.choices[0].message["content"].strip()
            post_data = json.loads(generated_content)
            title = post_data.get("title", "Generated Post")
            description = post_data.get("description", "")
            markdown = post_data.get("markdown", "")

            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")

            number = get_next_post_number()

            # Clean the title for the filename
            clean_title = re.sub(r"[^a-zA-Z0-9]+", "", title) or "generatedpost"
            filename = f"{number}_{clean_title}.md"
            filepath = f"{POSTS_DIR}/{filename}"

            file_content = (
                f"Title: {title}\n"
                f"Description: {description}\n"
                f"Published Date: {current_date}\n"
                f"Published Time: {current_time}\n\n"
                f"{markdown}"
            )
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(file_content)
            posts = load_posts_json()
            new_entry = {
                "title": title,
                "date_published": current_date,
                "time_published": current_time,
                "last_edited": current_date,
                "description": description,
                "link": f"{POSTS_DIR}/{filename}"
            }
            posts.append(new_entry)
            save_posts_json(posts)
            refresh_post_list()
            messagebox.showinfo("Success", f"Generated post saved as {filename}")
            gen_window.destroy()
        except json.JSONDecodeError as je:
            messagebox.showerror("Error", f"Failed to parse JSON from generated content: {je}")
            logging.error("JSON parsing error in generate_post: %s", je)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate post: {e}")
            logging.error("Failed to generate post: %s", e)

    generate_btn = ttk.Button(gen_window, text="Generate", command=do_generate)
    generate_btn.pack(pady=5)
    cancel_btn = ttk.Button(gen_window, text="Cancel", command=gen_window.destroy)
    cancel_btn.pack(pady=5)

# ----------------- UI Setup -----------------
root = tk.Tk()
root.title("Brutal Blog Editor")
root.geometry("1000x600")

style = ttk.Style()
if "clam" in style.theme_names():
    style.theme_use("clam")
root.option_add("*Font", "Helvetica 10")
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

paned_window = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
paned_window.grid(row=0, column=0, sticky="nsew")

left_frame = ttk.Frame(paned_window, padding=10)
left_frame.grid_columnconfigure(0, weight=1)
left_frame.grid_columnconfigure(1, weight=1)
left_frame.grid_rowconfigure(6, weight=1)

status_label = ttk.Label(left_frame, text="Creating a New Post", font=("Helvetica", 10, "italic"))
status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

ttk.Label(left_frame, text="Post Title").grid(row=1, column=0, sticky=tk.W)
title_entry = ttk.Entry(left_frame)
title_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

ttk.Label(left_frame, text="Post Description").grid(row=3, column=0, sticky=tk.W)
desc_entry = ttk.Entry(left_frame)
desc_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))

ttk.Label(left_frame, text="Markdown").grid(row=5, column=0, sticky=tk.W)
markdown_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD)
markdown_text.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

# Improved Button Layout
action_frame = ttk.Frame(left_frame)
action_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=5)
for i in range(4):
    action_frame.columnconfigure(i, weight=1)

save_btn = ttk.Button(action_frame, text="Save Post", command=save_post)
save_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
new_btn = ttk.Button(action_frame, text="New Post", command=new_post)
new_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
edit_btn = ttk.Button(action_frame, text="Edit Selected Post", command=load_post)
edit_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
generate_btn = ttk.Button(action_frame, text="Generate Post", command=generate_post)
generate_btn.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

utility_frame = ttk.Frame(left_frame)
utility_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=5)
for i in range(3):
    utility_frame.columnconfigure(i, weight=1)

toggle_btn = ttk.Button(utility_frame, text="Hide List", command=lambda: toggle_list())
toggle_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
minimal_check_btn = ttk.Button(utility_frame, text="Minimal Grammar Check", command=minimal_grammar_check)
minimal_check_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
manage_api_key_btn = ttk.Button(utility_frame, text="Manage API Configuration", command=manage_api_key)
manage_api_key_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

def toggle_list():
    global list_visible
    if list_visible:
        paned_window.forget(right_frame)
        toggle_btn.config(text="Show List")
        list_visible = False
    else:
        paned_window.add(right_frame, weight=1)
        toggle_btn.config(text="Hide List")
        list_visible = True
    root.update_idletasks()
    root.geometry("")

right_frame = ttk.Frame(paned_window, padding=5)
right_frame.grid_columnconfigure(0, weight=1)
right_frame.grid_rowconfigure(2, weight=1)

sort_frame = ttk.Frame(right_frame)
sort_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
ttk.Label(sort_frame, text="Sort by:").grid(row=0, column=0, sticky="w")
sort_combobox = ttk.Combobox(sort_frame,
                             values=["Name", "Number", "Date Posted", "Date Edited"],
                             state="readonly")
sort_combobox.current(2)  # Set default to "Date Posted"
sort_combobox.grid(row=0, column=1, sticky="ew", padx=5)
sort_combobox.bind("<<ComboboxSelected>>", apply_sort)
toggle_order_btn = ttk.Button(sort_frame, text="Ascending" if sort_order_asc else "Descending", command=toggle_sort_order)
toggle_order_btn.grid(row=0, column=2, sticky="e", padx=5)

ttk.Label(right_frame, text="Posts List").grid(row=1, column=0, sticky=tk.W, padx=5, pady=(5, 0))
post_listbox = tk.Listbox(right_frame)
post_listbox.grid(row=2, column=0, sticky="nsew", padx=(5, 0), pady=5)
list_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=post_listbox.yview)
list_scrollbar.grid(row=2, column=1, sticky="ns", pady=5)
post_listbox.config(yscrollcommand=list_scrollbar.set)

post_listbox.bind("<Button-3>", show_context_menu)
post_listbox.bind("<Double-Button-1>", lambda event: load_post())
post_listbox.bind("<Motion>", on_listbox_motion)
post_listbox.bind("<Leave>", on_listbox_leave)

paned_window.add(left_frame, weight=3)
paned_window.add(right_frame, weight=1)
list_visible = True

refresh_post_list()
root.mainloop()
