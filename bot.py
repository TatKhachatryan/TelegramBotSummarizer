import logging
import fitz  # PyMuPDF for PDF text extraction
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from transformers import pipeline
from docx import Document

# Telegram Bot Token (Replace with your own)
BOT_TOKEN = "7985776943:AAED4vPWy2qd6VJdqjMOfpn6IGiCRHrMpIY"

# Initialize NLP Summarization Model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Logging Configuration
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def start(update: Update, context: CallbackContext) -> None:
    """Start command handler"""
    await update.message.reply_text(
        "Hello! 😊 Send me any text or upload a document (TXT, PDF, DOCX), and I'll summarize it for you! 📄"
    )


async def summarize_text(update: Update, context: CallbackContext) -> None:
    """Handles incoming text messages and summarizes them"""
    user_text = update.message.text.strip()

    if len(user_text) < 20:
        await update.message.reply_text("⚠️ Please provide a longer text (at least 20 characters) for summarization.")
        return

    try:
        summary = generate_summary(user_text)
        await update.message.reply_text(f"📑 **Summary:**\n{summary}")
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        await update.message.reply_text("❌ Oops! Something went wrong while summarizing. Please try again later.")


async def handle_document(update: Update, context: CallbackContext) -> None:
    """Handles uploaded documents (PDF, TXT, DOCX)"""
    document = update.message.document
    file_type = document.mime_type

    # Check supported formats
    if file_type not in ["text/plain", "application/pdf",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        await update.message.reply_text("⚠️ Unsupported file format! Please upload a TXT, PDF, or DOCX file.")
        return

    # Notify user
    await update.message.reply_text("📄 Received your document! Extracting text and summarizing... 🔍")

    # Download the file
    file = await document.get_file()
    file_path = f"./{document.file_name}"
    await file.download_to_drive(file_path)

    # Extract text based on file type
    try:
        if file_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_type == "application/pdf":
            text = extract_text_from_pdf(file_path)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_text_from_docx(file_path)
        else:
            text = ""

        # Validate text
        if not text.strip():
            await update.message.reply_text("⚠️ No readable text found in the document. Please try another file.")
            return

        # Generate summary
        summary = generate_summary(text)
        await update.message.reply_text(f"📑 **Summary:**\n{summary}")

    except Exception as e:
        logging.error(f"Error processing document: {e}")
        await update.message.reply_text("❌ An error occurred while processing your document.")

    finally:
        # Clean up downloaded file
        if os.path.exists(file_path):
            os.remove(file_path)


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file"""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file"""
    doc = Document(docx_path)
    return "\n".join(para.text for para in doc.paragraphs)


def generate_summary(text):
    """Summarizes the given text using the NLP model"""
    max_input_length = 1024
    if len(text) > max_input_length:
        text = text[:max_input_length]  # Truncate if too long

    summary = summarizer(text, max_length=200, min_length=50, do_sample=False)
    return summary[0]['summary_text']


def main():
    """Runs the Telegram bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, summarize_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Start bot
    app.run_polling()


if __name__ == "__main__":
    main()
