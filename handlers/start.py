import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import get_db
from utils.force_join import check_channel_membership, ForceJoinError
from utils.states import START

logger = logging.getLogger(__name__)

db = get_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Main entry point"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"User {user_id} ({user_name}) started the bot")
    
    # Check if user has completed profile
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    existing_user = db.get_collection("users").find_one({"user_id": user_id})
    
    # First check channel membership
    try:
        is_member = await check_channel_membership(update, context)
        
        if not is_member:
            # User not in channel - show force join screen
            keyboard = [
                [InlineKeyboardButton("📢 JOIN CHANNEL 📢", url="https://t.me/nrtecno2")],
                [InlineKeyboardButton("✅ VERIFY MEMBERSHIP", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔐 **ACCESS RESTRICTED** 🔐\n\n"
                "⚠️ You must join our official channel to use this bot!\n\n"
                "📌 **Steps to verify:**\n"
                "1️⃣ Tap the JOIN CHANNEL button below\n"
                "2️⃣ Join @nrtecno2\n"
                "3️⃣ Come back and tap VERIFY MEMBERSHIP\n\n"
                "⚡ Verification is instant and automatic.\n"
                "🔓 No verification = No access\n\n"
                "*This is to prevent spam and ensure quality users.*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
    except ForceJoinError as e:
        logger.error(f"Channel check error: {e}")
        await update.message.reply_text(
            "❌ **System Error**\n\n"
            "Unable to verify channel membership. Please try again later.\n\n"
            f"Error: {str(e)}",
            parse_mode='Markdown'
        )
        return
    
    # User is verified, now check profile status
    if existing_profile and existing_user and existing_user.get('setup_complete', False):
        # Profile exists - show main menu
        await show_verified_main_menu(update, context, user_name)
    else:
        # New user - start profile creation
        await start_profile_creation(update, context, user_name)

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verify button callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Re-check channel membership
    try:
        is_member = await check_channel_membership(update, context)
        
        if is_member:
            # Verification successful
            keyboard = [[InlineKeyboardButton("🚀 CONTINUE TO BOT", callback_data="continue_bot")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ **VERIFICATION SUCCESSFUL!** ✅\n\n"
                f"Welcome {user_name}!\n\n"
                "You have been verified as a channel member.\n"
                "Now you can access all bot features.\n\n"
                "🔓 Full access granted.\n"
                "🔥 Let's get started!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Still not a member
            keyboard = [
                [InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/nrtecno2")],
                [InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ **VERIFICATION FAILED** ❌\n\n"
                "You are still not a member of @nrtecno2.\n\n"
                "📌 Please follow these steps:\n"
                "1️⃣ Click JOIN CHANNEL below\n"
                "2️⃣ Join the channel\n"
                "3️⃣ Click VERIFY AGAIN\n\n"
                "⚡ After joining, verification is instant.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except ForceJoinError as e:
        logger.error(f"Verification error: {e}")
        await query.edit_message_text(
            "❌ **System Error**\n\n"
            "Unable to verify membership. Please try again.\n\n"
            f"Error: {str(e)}",
            parse_mode='Markdown'
        )

async def continue_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle continue button after verification"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Check if profile exists
    existing_profile = db.get_collection("profiles").find_one({"user_id": user_id})
    
    if existing_profile:
        await show_verified_main_menu(update, context, user_name)
    else:
        await start_profile_creation(update, context, user_name)

async def new_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start profile creation for new user (called from /start when no profile)"""
    user_id = update.effective_user.id
    
    # Verify channel membership first
    try:
        is_member = await check_channel_membership(update, context)
        if not is_member:
            # Redirect to verification
            keyboard = [
                [InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/nrtecno2")],
                [InlineKeyboardButton("✅ VERIFY", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔐 **CHANNEL VERIFICATION REQUIRED**\n\n"
                "Please join @nrtecno2 first!",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
    except ForceJoinError:
        await update.message.reply_text("❌ Verification system error. Try again.")
        return ConversationHandler.END
    
    # Start profile creation
    from handlers.profile import create_profile_start
    return await create_profile_start(update, context)

async def show_verified_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_name: str):
    """Show main menu for verified users with complete profile"""
    query = update.callback_query if update.callback_query else None
    
    # Get user stats
    user_id = update.effective_user.id
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    unread_notifications = db.get_collection("notifications").count_documents({"user_id": user_id, "is_read": False})
    
    keyboard = [
        [InlineKeyboardButton("👤 MY PROFILE", callback_data="my_profile")],
        [InlineKeyboardButton("👀 VIEW PROFILES 🔥", callback_data="view_profiles")],
        [InlineKeyboardButton(f"🔔 NOTIFICATIONS ({unread_notifications})", callback_data="notifications")],
        [InlineKeyboardButton("📊 STATS", callback_data="show_stats")],
        [InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"⚡ **DEMON DATING SYSTEM** ⚡\n\n"
        f"Welcome back, {user_name}!\n\n"
        f"📊 Your Stats:\n"
        f"├ ❤️ Likes Received: {likes_received}\n"
        f"├ 🔔 Unread: {unread_notifications}\n"
        f"└ 🎯 Status: Active\n\n"
        f"🔥 Select an option below to continue:"
    )
    
    if query:
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def start_profile_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_name: str):
    """Initiate profile creation process for new user"""
    keyboard = [[InlineKeyboardButton("🚀 START NOW", callback_data="create_profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"🌟 **WELCOME {user_name.upper()}!** 🌟\n\n"
        f"🎯 You've successfully verified channel membership.\n\n"
        f"📝 **Let's create your dating profile!**\n\n"
        f"Here's what we need:\n"
        f"├ ✅ Your Name\n"
        f"├ ✅ Gender (Male/Female)\n"
        f"├ ✅ Age (18-100)\n"
        f"├ ✅ Location\n"
        f"├ ✅ About You (max 500 chars)\n"
        f"└ ✅ 1-3 Photos/Videos\n\n"
        f"⚡ This will take less than 2 minutes!\n"
        f"🔒 All data is private and secure.\n\n"
        f"Ready to find your match? 🔥"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def create_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle create profile button click"""
    query = update.callback_query
    await query.answer()
    
    from handlers.profile import create_profile_start
    await create_profile_start(update, context)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Get stats from database
    profile = db.get_collection("profiles").find_one({"user_id": user_id})
    likes_given = db.get_collection("likes").count_documents({"from_user": user_id})
    likes_received = db.get_collection("likes").count_documents({"to_user": user_id})
    messages_sent = db.get_collection("messages").count_documents({"from_user": user_id})
    messages_received = db.get_collection("messages").count_documents({"to_user": user_id})
    
    # Find mutual likes
    mutual_likes = db.get_collection("likes").aggregate([
        {"$match": {"from_user": user_id}},
        {"$lookup": {
            "from": "likes",
            "localField": "to_user",
            "foreignField": "from_user",
            "as": "mutual"
        }},
        {"$match": {"mutual.to_user": user_id}}
    ])
    mutual_count = len(list(mutual_likes))
    
    stats_text = (
        f"📊 **YOUR STATS** 📊\n\n"
        f"👤 Profile:\n"
        f"├ Name: {profile.get('name', 'N/A')}\n"
        f"├ Age: {profile.get('age', 'N/A')}\n"
        f"└ Gender: {profile.get('gender', 'N/A')}\n\n"
        f"❤️ Interactions:\n"
        f"├ Likes Given: {likes_given}\n"
        f"├ Likes Received: {likes_received}\n"
        f"├ Mutual Matches: {mutual_count}\n"
        f"└ Active Status: Active\n\n"
        f"💬 Messages:\n"
        f"├ Sent: {messages_sent}\n"
        f"└ Received: {messages_received}\n\n"
        f"🎯 Keep interacting to find better matches!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 BACK TO MENU", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

# Add handlers for remaining callbacks
async def my_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View own profile"""
    query = update.callback_query
    await query.answer()
    # This will be implemented in profile.py
    from handlers.profile import show_my_profile
    await show_my_profile(update, context)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
        [InlineKeyboardButton("🎯 Change Preference", callback_data="set_preference")],
        [InlineKeyboardButton("🗑 Delete Account", callback_data="delete_account")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ **SETTINGS** ⚙️\n\nChoose an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
