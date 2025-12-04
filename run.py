import os
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from google import genai

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key = GEMINI_API_KEY)

PROMPT = (
    "Place this sofa realistically inside the given room image. "
    "Maintain scale, perspective, and lighting. "
    "Do not hallucinate new furniture or decorations."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi 👋! Please send both your *sofa* and *room* images together in one message.")

async def handle_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == "hi":
        await start(update, context)

async def handle_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = update.message.photo
    print(photos)
    if len(photos) < 2:
        await update.message.reply_text("Please send *both* sofa and room images together 📸📸")
        return

    sofa_file = await photos[0].get_file()
    room_file = await photos[1].get_file()

    sofa_bytes = await sofa_file.download_as_bytearray()
    room_bytes = await room_file.download_as_bytearray()

    from io import BytesIO
    sofa_image = Image.open(BytesIO(sofa_bytes))
    room_image = Image.open(BytesIO(room_bytes))

    sofa_image.save("sofa.png")
    room_image.save("room.png")

    uploaded_files = [client.files.upload(file= i) for i in ["sofa.png", "room.png"]]

    await update.message.reply_text("✨ Generating combined image using Nano Banana... please wait ⏳")

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[PROMPT, uploaded_files],
    )

    # ✅ Get only the first image output (single result)
    image_bytes = None
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            break  # Stop after first image found

    if image_bytes:
        img = Image.open(BytesIO(image_bytes))
        output_path = f"generated_{update.message.from_user.id}.png"
        img.save(output_path)

        await update.message.reply_photo(photo=open(output_path, "rb"))
        await update.message.reply_text("✅ Done! Here’s your generated image.")
    else:
        await update.message.reply_text("❌ No image returned from Nano Banana.")

def run_app():
    print("This is the End.")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hi))
    app.add_handler(MessageHandler(filters.PHOTO, handle_images))

    return app

if __name__ == "__main__":
    app = run_app()
    app.run_polling()