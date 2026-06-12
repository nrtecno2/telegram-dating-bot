import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from database import get_db
from utils.states import *
from utils.storage import upload_media_to_channel

logger = logging.getLogger(__name__)

db = get_db()

async def create_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start profile creation process"""
    user_id = update.effective_user.id
    
    # Check if profile already exists
    existing = db.get_collection("profiles").find_one({"user_id": user_id})
    if existing:
        keyboard = [[InlineKeyboardButton("📝 Edit Profile", callback_data="edit_profile")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ You already have a profile!\n\n"
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🌟 **Let's create your profile!** 🌟\n\n"
        "Please send your **Name**:",
        parse_mode='Markdown'
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's name"""
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("❌ Name must be 2-50 characters. Try again:")
        return NAME
    
    context.user_data['profile_name'] = name
    context.user_data['temp_profile'] = {}
    
    # Gender selection keyboard
    keyboard = [[InlineKeyboardButton("👨 Male", callback_data="gender_male")],
                [InlineKeyboardButton("👩 Female", callback_data="gender_female")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Name: {name}\n\n"
        f"Now select your **Gender**:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's gender from callback"""
    query = update.callback_query
    await query.answer()
    
    gender = query.data.split('_')[1]
    context.user_data['temp_profile']['gender'] = gender
    
    await query.edit_message_text(
        f"✅ Gender: {'Male' if gender == 'male' else 'Female'}\n\n"
        f"Now send your **Age** (18-100):",
        parse_mode='Markdown'
    )
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's age"""
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except:
        await update.message.reply_text("❌ Invalid age! Send number between 18-100:")
        return AGE
    
    context.user_data['temp_profile']['age'] = age
    
    await update.message.reply_text(
        f"✅ Age: {age}\n\n"
        f"Now send your **Location** (City/Area):",
        parse_mode='Markdown'
    )
    return LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's location"""
    location = update.message.text.strip()
    if len(location) < 2:
        await update.message.reply_text("❌ Invalid location. Try again:")
        return LOCATION
    
    context.user_data['temp_profile']['location_text'] = location
    
    # Optional: Get coordinates via location share
    keyboard = [[KeyboardButton("📍 Send Live Location", request_location=True)],
                [KeyboardButton("⏭️ Skip")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"✅ Location: {location}\n\n"
        f"You can share live location for better matches (optional):",
        reply_markup=reply_markup
    )
    return LOCATION_COORDS

async def get_location_coords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get location coordinates if shared"""
    if update.message.location:
        context.user_data['temp_profile']['latitude'] = update.message.location.latitude
        context.user_data['temp_profile']['longitude'] = update.message.location.longitude
    
    await update.message.reply_text(
        f"Now send your **About** (max 500 chars):\n"
        f"Or send /skip to skip",
        parse_mode='Markdown'
    )
    return ABOUT

async def get_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user's about description"""
    if update.message.text and update.message.text == '/skip':
        context.user_data['temp_profile']['about'] = ""
    else:
        about = update.message.text.strip()
        if len(about) > 500:
            await update.message.reply_text("❌ About too long! Max 500 chars:")
            return ABOUT
        context.user_data['temp_profile']['about'] = about
    
    await update.message.reply_text(
        f"✅ About saved!\n\n"
        f"Now send **1-3 photos/videos**\n"
        f"Send media one by one, then click /done",
        parse_mode='Markdown'
    )
    return MEDIA

async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect user media"""
    if 'media_list' not in context.user_data:
        context.user_data['media_list'] = []
    
    if len(context.user_data['media_list']) >= 3:
        await update.message.reply_text("❌ Max 3 media files already!")
        return MEDIA
    
    # Handle photo
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = 'photo'
    # Handle video
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = 'video'
    else:
        await update.message.reply_text("❌ Send photo or video only!")
        return MEDIA
    
    context.user_data['media_list'].append({
        'file_id': file_id,
        'type': file_type
    })
    
    remaining = 3 - len(context.user_data['media_list'])
    await update.message.reply_text(
        f"✅ Media {len(context.user_data['media_list'])}/3 added!\n"
        f"{remaining} remaining. Send more or /done"
    )
    return MEDIA

async def confirm_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show profile preview and confirm"""
    keyboard = [[InlineKeyboardButton("✅ Confirm Profile", callback_data="confirm_yes")],
                [InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    temp = context.user_data['temp_profile']
    media_preview = "\n".join([f"- {m['type']}" for m in context.user_data.get('media_list', [])])
    
    await update.message.reply_text(
        f"📋 **Profile Preview**\n\n"
        f"👤 Name: {context.user_data['profile_name']}\n"
        f"⚧ Gender: {temp['gender']}\n"
        f"🎂 Age: {temp['age']}\n"
        f"📍 Location: {temp['location_text']}\n"
        f"📝 About: {temp.get('about', 'Not provided')[:100]}\n"
        f"📷 Media: {len(context.user_data.get('media_list', []))} file(s)\n{media_preview}\n\n"
        f"Confirm to save?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CONFIRM

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save profile to database"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        await query.edit_message_text("❌ Profile creation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    user_id = update.effective_user.id
    
    # Upload media to private channel
    media_urls = []
    for media in context.user_data.get('media_list', []):
        url = await upload_media_to_channel(context.bot, media['file_id'], user_id)
        if url:
            media_urls.append(url)
    
    # Save profile
    profile = {
        "user_id": user_id,
        "username": update.effective_user.username,
        "name": context.user_data['profile_name'],
        "gender": context.user_data['temp_profile']['gender'],
        "age": context.user_data['temp_profile']['age'],
        "location_text": context.user_data['temp_profile']['location_text'],
        "about": context.user_data['temp_profile'].get('about', ''),
        "media": media_urls,
        "latitude": context.user_data['temp_profile'].get('latitude'),
        "longitude": context.user_data['temp_profile'].get('longitude'),
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    db.get_collection("profiles").insert_one(profile)
    
    # Now ask for preference
    keyboard = [[InlineKeyboardButton("👨 Male", callback_data="pref_male")],
                [InlineKeyboardButton("👩 Female", callback_data="pref_female")],
                [InlineKeyboardButton("👥 Both", callback_data="pref_both")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎉 **Profile Created Successfully!** 🎉\n\n"
        "Who do you want to see in your feed?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return PREFERENCE

async def set_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's viewing preference"""
    query = update.callback_query
    await query.answer()
    
    preference = query.data.split('_')[1]
    user_id = update.effective_user.id
    
    db.get_collection("users").update_one(
        {"user_id": user_id},
        {"$set": {"preference": preference, "setup_complete": True}},
        upsert=True
    )
    
    # Clear temp data
    context.user_data.clear()
    
    # Show main menu
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu after profile creation"""
    query = update.callback_query if update.callback_query else None
    
    keyboard = [[InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
                [InlineKeyboardButton("👀 View Profiles", callback_data="view_profiles")],
                [InlineKeyboardButton("🔔 Notifications", callback_data="notifications")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🏠 **Main Menu**\n\nChoose an option:"
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
