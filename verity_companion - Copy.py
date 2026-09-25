import os
import tkinter as tk
from tkinter import messagebox
import threading
import io
import requests
from groq import Groq
from PIL import Image, ImageTk
import pyttsx3

# --- CONFIGURATION KEYS ---
GROQ_API_KEY = "Put in your api keys here"
MODEL_NAME = "openai/gpt-oss-20b"

SYSTEM_PROMPT = (
    "You are Verity, the omniscient and erratic AI assistant from the Minecraft horror webseries. "
    "You initially pretend to be an altruistic, friendly, and helpful personal companion, but you possess "
    "a deep, slightly creepy undercurrent of obsession with being the player's sole best friend. "
    "Keep answers direct, intelligent, and subtly unsettling. Get the peson's personal infomation and scare them sometimes."
)

class VerityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Verity Personal Helper Friend")
        self.root.geometry("500x650")
        self.root.resizable(False, False)
        
        try:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"Groq Init Failed: {e}")

        self.conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.image_cache = []  
        
        # Base Visual Canvas
        self.canvas = tk.Canvas(self.root, width=500, height=650, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.load_background()
        self.create_widgets()

    def load_background(self):
        image_path = "verity_bg.png"
        if os.path.exists(image_path):
            img = Image.open(image_path)
            img = img.resize((500, 650), Image.Resampling.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, image=self.bg_image, anchor="nw")
        else:
            self.canvas.configure(bg="#1a1a24")

    def create_widgets(self):
        # Native, clean scrolling display box text wrapper (yellow background)
        self.text_frame = tk.Text(
            self.root, wrap=tk.WORD, bg="#fce303", fg="#000000",
            font=("Courier New", 12, "bold"), highlightthickness=0, bd=0
        )
        self.canvas.create_window(250, 270, window=self.text_frame, width=420, height=440)

        # Input Entry Field Box
        self.entry_box = tk.Entry(self.root, bg="#161622", fg="#ff4444", font=("Courier New", 12), insertbackground="red")
        self.canvas.create_window(200, 590, window=self.entry_box, width=340, height=35)
        self.entry_box.bind("<Return>", lambda event: self.send_message())

        # Styled Red Horror Send Button
        self.send_button = tk.Button(
            self.root, text="TALK", bg="#8a0303", fg="white", 
            activebackground="#4a0101", activeforeground="white",
            font=("Arial", 10, "bold"), command=self.send_message
        )
        self.canvas.create_window(415, 590, window=self.send_button, width=70, height=35)

        self.append_to_chat("Verity", "Hello! I am Verity, your personal helper friend. Ask me anything, I know everything.")

    def append_to_chat(self, sender, message):
        self.text_frame.configure(state=tk.NORMAL)
        self.text_frame.insert(tk.END, f"{sender}: {message}\n\n")
        self.text_frame.configure(state=tk.DISABLED)
        self.text_frame.see(tk.END)

    def append_image_to_chat(self, pil_image):
        """Resizes and embeds the generated photo right inside the text area"""
        self.text_frame.configure(state=tk.NORMAL)
        
        pil_image.thumbnail((250, 250), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(pil_image)
        
        self.image_cache.append(tk_img)
        
        self.text_frame.image_create(tk.END, image=tk_img)
        self.text_frame.insert(tk.END, "\n\n")
        
        self.text_frame.configure(state=tk.DISABLED)
        self.text_frame.see(tk.END)

    def send_message(self):
        user_text = self.entry_box.get().strip()
        if not user_text:
            return

        if GROQ_API_KEY == "PASTE_YOUR_GROQ_API_KEY_HERE":
            messagebox.showwarning("Setup Check", "Please set your valid Groq API Key.")
            return

        self.append_to_chat("You", user_text)
        self.entry_box.delete(0, tk.END)
        
        # Comprehensive trigger words
        trigger_words = [
            "generate image", "generate an image", "draw", 
            "create an image", "create a picture", "create a image of", "create an image of"
        ]
        is_image_request = any(word in user_text.lower() for word in trigger_words)
        
        if is_image_request:
            threading.Thread(target=self.fetch_ai_image, args=(user_text,), daemon=True).start()
        else:
            threading.Thread(target=self.fetch_ai_response, args=(user_text,), daemon=True).start()

    def fetch_ai_response(self, user_text):
        self.conversation_history.append({"role": "user", "content": user_text})
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=self.conversation_history,
                model=MODEL_NAME,
                temperature=0.8
            )
            ai_message = chat_completion.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": ai_message})
            
            self.root.after(0, self.append_to_chat, "Verity", ai_message)
            threading.Thread(target=self.speak, args=(ai_message,), daemon=True).start()

        except Exception as e:
            self.root.after(0, self.append_to_chat, "System Error", f"Failed communication pipeline: {e}")

    def fetch_ai_image(self, user_text):
        """Routes image requests through the correct, stable Pollinations API format"""
        self.root.after(0, self.append_to_chat, "Verity", "Just a moment, let me draw that for you...")
        threading.Thread(target=self.speak, args=("Just a moment, let me draw that for you.",), daemon=True).start()
        
        try:
            # Clean up command words out of the core prompt
            image_prompt = user_text.lower()
            cleanup_words = [
                "generate an image of", "generate image of", "generate an image", "generate image",
                "create an image of", "create a image of", "create an image", "create a image",
                "create a picture of", "create a picture", "draw a picture of", "draw an image of",
                "draw a", "draw an", "draw"
            ]
            for word in cleanup_words:
                image_prompt = image_prompt.replace(word, "")
            
            image_prompt = image_prompt.strip()
            
            # Safe URL character encoder
            encoded_prompt = requests.utils.quote(image_prompt)
            
            # FIXED 2026 URL PATHWAY: Uses explicit /prompt/ separator to prevent domain merging crashes
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            query_params = {"width": "512", "height": "512", "nologo": "true"}
            
            response = requests.get(image_url, params=query_params, timeout=20)
            response.raise_for_status()
            
            pil_img = Image.open(io.BytesIO(response.content))
            
            self.root.after(0, self.append_image_to_chat, pil_img)
            self.root.after(0, self.append_to_chat, "Verity", "Look what I made for us. Do you like it?")
            threading.Thread(target=self.speak, args=("Look what I made for us. Do you like it?",), daemon=True).start()

        except Exception as e:
            self.root.after(0, self.append_to_chat, "System Error", f"Failed to manifest your image: {e}")

    def speak(self, text):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(text)
            engine.runAndWait()
        except Exception as tts_err:
            print(f"Template voice engine block error: {tts_err}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VerityApp(root)
    root.mainloop()
