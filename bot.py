import logging
import fitz  # PyMuPDF for extracting text from PDFs
import torch
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from transformers import pipeline

# Telegram Bot Token
BOT_TOKEN = "MYTOKEN"

# Force CPU to avoid MPS errors on macOS
device = "cpu"
summarizer = pipeline("summarization", model="google/flan-t5-small", device=0 if torch.cuda.is_available() else -1)

# Logging Configuration
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: CallbackContext) -> None:
    """Start command handler"""
    await update.message.reply_text("Hello! 😊 Send me a long text or a PDF file, and I'll summarize it for you! 📄✨")

async def summarize_text(update: Update, context: CallbackContext) -> None:
    """Handles text summarization"""
    user_text = update.message.text.strip()

    if len(user_text) < 50:
        await update.message.reply_text("⚠️ Please provide a longer text (at least 50 characters) for better summarization.")
        return

    try:
        summary = smart_summarization(user_text)
        await update.message.reply_text(f"📑 **Summary:**\n{summary}")
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        await update.message.reply_text("❌ Oops! Something went wrong while summarizing. Please try again later.")
async def send_long_message(update: Update, text: str, chunk_size=4000):
    """Sends long messages by splitting them into chunks"""
    for i in range(0, len(text), chunk_size):
        await update.message.reply_text(text[i:i + chunk_size])

async def summarize_pdf(update: Update, context: CallbackContext) -> None:
    """Handles PDF file summarization"""
    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Please upload a valid PDF file.")
        return

    file_id = document.file_id
    new_file = await context.bot.get_file(file_id)
    file_path = f"{file_id}.pdf"

    # Download PDF file
    await new_file.download_to_drive(file_path)

    try:
        extracted_text = extract_text_from_pdf(file_path)
        if len(extracted_text) < 50:
            await update.message.reply_text("⚠️ The extracted text is too short for summarization.")
            return

        summary = smart_summarization(extracted_text)

        # ✅ Fix: Send long summaries in multiple messages
        await send_long_message(update, f"📑 **Summary:**\n{summary}")

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        await update.message.reply_text("❌ An error occurred while processing your document.")


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text("text") + "\n"

    return text.strip()

def smart_summarization(text):
    """Splits long text into chunks, summarizes each, and combines the results"""
    MAX_INPUT_LENGTH = 512
    CHUNK_OVERLAP = 50

    chunks = []
    while len(text) > MAX_INPUT_LENGTH:
        split_idx = text.rfind(".", 0, MAX_INPUT_LENGTH)
        if split_idx == -1:
            split_idx = MAX_INPUT_LENGTH
        chunks.append(text[:split_idx + 1])
        text = text[split_idx + 1 - CHUNK_OVERLAP:]

    if text:
        chunks.append(text)

    # Summarize each chunk separately
    summarized_chunks = [summarizer(chunk, max_length=150, min_length=50, do_sample=False)[0]["summary_text"] for chunk in chunks]

    # Combine summarized chunks
    final_summary = " ".join(summarized_chunks)
    return final_summary

def main():
    """Runs the Telegram bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, summarize_text))
    app.add_handler(MessageHandler(filters.Document.PDF, summarize_pdf))  # Handles PDF files

    app.run_polling()

if __name__ == "__main__":
    main()
